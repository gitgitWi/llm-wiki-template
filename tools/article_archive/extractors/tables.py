"""Turn tables into something Discord can actually show.

Discord renders neither HTML tables nor markdown pipe tables. defuddle passes
`<table>` through as raw HTML, so a benchmark table arrives as a wall of
`<td><strong>0.700</strong></td>` — the most information-dense part of an
article, delivered as its least readable part.

Two output shapes, chosen by width:

* **narrow** — a fixed-width grid inside a fence, which Discord shows in a
  monospace font so the columns line up.
* **wide** — one block per row, because a 7-column grid wraps into confetti on
  a phone. Header labels become the field names.

Multi-row headers (``colspan`` group headers above per-column headers, the
common shape for benchmark tables) are flattened by joining each column's
labels with ``/``, so ``Opus 5 (high)`` over ``Claude Code`` reads
``Opus 5 (high) / Claude Code``.

stdlib only — this runs inside the gateway and is not worth a dependency.
"""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import List, Optional, Tuple

# Beyond this, a fixed-width grid stops being readable on a phone.
MAX_GRID_WIDTH = 72
# Discord hard-caps a message at 2000; a table bigger than this can never be
# formatted usefully, so it is left for the caller to chunk as prose.
MAX_CELLS = 400

_TABLE_RE = re.compile(r"<table\b.*?</table>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")


class _TableParser(HTMLParser):
    """Collect ``(rows, header_row_count)`` from one HTML table.

    ``colspan``/``rowspan`` are expanded into real cells so every row ends up
    the same length and column indexes line up.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: List[List[str]] = []
        self.header_rows = 0
        self._row: Optional[List[str]] = None
        self._cell: Optional[List[str]] = None
        # Cells owed to later rows by a rowspan: (column, text, rows_left).
        self._carry: List[Tuple[int, str, int]] = []
        self._new_carry: List[Tuple[int, str, int]] = []
        self._in_thead = False
        self._row_is_header = False
        self._depth = 0
        self._colspan = 1
        self._rowspan = 1

    # -- helpers ---------------------------------------------------------
    def _splice_carried(self, row: List[str]) -> None:
        """Insert cells a previous row's ``rowspan`` owes to this one.

        Done at row end rather than row start: the row's own cells fill their
        natural positions first, then a carried cell is spliced in at its
        column, which shifts the rest right exactly as the browser would.
        """
        for col, text, _ in sorted(self._carry, key=lambda item: item[0]):
            row.insert(min(col, len(row)), text)

    def _advance_rowspans(self) -> None:
        self._carry = [
            (col, text, left - 1)
            for col, text, left in self._carry
            if left - 1 > 0
        ] + self._new_carry
        self._new_carry = []

    # -- HTMLParser ------------------------------------------------------
    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "table":
            self._depth += 1
            return
        if self._depth != 1:
            return
        attr = {k.lower(): (v or "") for k, v in attrs}
        if tag == "thead":
            self._in_thead = True
        elif tag == "tr":
            self._row = []
            self._row_is_header = self._in_thead
        elif tag in ("td", "th"):
            self._cell = []
            if tag == "th":
                self._row_is_header = self._row_is_header or not self.rows
            self._colspan = max(1, _int(attr.get("colspan"), 1))
            self._rowspan = max(1, _int(attr.get("rowspan"), 1))
        elif tag == "br" and self._cell is not None:
            self._cell.append(" — ")
        elif tag in ("strong", "b") and self._cell is not None:
            # HTMLParser hands handle_data the text only, so emphasis has to be
            # re-emitted here or it is lost before _clean ever sees it.
            self._cell.append("**")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "table":
            self._depth -= 1
            return
        if self._depth != 1:
            return
        if tag == "thead":
            self._in_thead = False
        elif tag in ("strong", "b") and self._cell is not None:
            self._cell.append("**")
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            text = _clean("".join(self._cell))
            col = len(self._row)
            # A colspan cell repeats its label across the columns it covers,
            # which is what lets _flatten_headers pair a group header with the
            # per-column header underneath it.
            self._row.extend([text] * self._colspan)
            if self._rowspan > 1:
                self._new_carry.append((col, text, self._rowspan - 1))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._splice_carried(self._row)
            if any(c.strip() for c in self._row):
                self.rows.append(self._row)
                if self._row_is_header and self.header_rows == len(self.rows) - 1:
                    self.header_rows += 1
            self._row = None
            self._advance_rowspans()

    def handle_data(self, data: str) -> None:
        if self._depth == 1 and self._cell is not None:
            self._cell.append(data)


def _int(value, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


_STRONG_RE = re.compile(r"</?(?:strong|b)\s*>", re.IGNORECASE)


def _clean(text: str) -> str:
    # Benchmark tables bold the winning number — that emphasis is data, so it
    # survives as markdown. The grid renderer strips it again, since a code
    # block would show the asterisks literally.
    text = _STRONG_RE.sub("**", unescape(text))
    text = _TAG_RE.sub("", text)
    text = _WS_RE.sub(" ", text.replace("\n", " ").replace("\r", " "))
    text = re.sub(r"\*\*\s*\*\*", "", text)  # emptied by a stripped inner tag
    return text.strip(" —").strip()


def _unbold(text: str) -> str:
    return text.replace("**", "")


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _normalize(rows: List[List[str]]) -> List[List[str]]:
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


def _flatten_headers(header_rows: List[List[str]]) -> List[str]:
    if not header_rows:
        return []
    width = len(header_rows[0])
    labels = []
    for col in range(width):
        seen: List[str] = []
        for row in header_rows:
            value = row[col].strip()
            if value and value not in seen:
                seen.append(value)
        labels.append(" / ".join(seen))
    return labels


def _grid(headers: List[str], body: List[List[str]]) -> str:
    # A fenced block shows markdown verbatim, so emphasis has to come off.
    headers = [_unbold(h) for h in headers]
    body = [[_unbold(c) for c in row] for row in body]
    table = ([headers] if headers else []) + body
    widths = [max(len(r[c]) for r in table) for c in range(len(table[0]))]
    def line(cells):
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()
    out = []
    if headers:
        out.append(line(headers))
        out.append("  ".join("-" * w for w in widths).rstrip())
    out.extend(line(r) for r in body)
    return "```\n" + "\n".join(out) + "\n```"


def _records(headers: List[str], body: List[List[str]]) -> str:
    """One block per row — the only shape that survives a narrow screen."""
    blocks = []
    for row in body:
        title = row[0].strip() or "—"
        lines = [f"**{title}**"]
        for col in range(1, len(row)):
            value = row[col].strip()
            if not value:
                continue
            label = headers[col].strip() if col < len(headers) else f"열 {col + 1}"
            lines.append(f"- {label}: {value}" if label else f"- {value}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def render_rows(rows: List[List[str]], header_rows: int) -> Optional[str]:
    rows = _normalize([r for r in rows if any(c.strip() for c in r)])
    if not rows or not rows[0]:
        return None
    if sum(len(r) for r in rows) > MAX_CELLS:
        return None

    header_rows = min(header_rows, len(rows))
    headers = _flatten_headers(rows[:header_rows])
    body = rows[header_rows:]
    if not body:
        body, headers = rows, []

    # Measure what the grid would actually print — emphasis is stripped there.
    table = [[_unbold(c) for c in r] for r in ([headers] if headers else []) + body]
    widths = [max(len(r[c]) for r in table) for c in range(len(table[0]))]
    grid_width = sum(widths) + 2 * (len(widths) - 1)

    if grid_width <= MAX_GRID_WIDTH:
        return _grid(headers, body)
    return _records(headers, body)


def html_table_to_text(html: str) -> Optional[str]:
    parser = _TableParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return None
    return render_rows(parser.rows, parser.header_rows)


def replace_html_tables(text: str) -> Tuple[str, int]:
    count = 0

    def _sub(match: re.Match) -> str:
        nonlocal count
        rendered = html_table_to_text(match.group(0))
        if rendered is None:
            return match.group(0)
        count += 1
        return f"\n{rendered}\n"

    return _TABLE_RE.sub(_sub, text), count


# --------------------------------------------------------------------------
# markdown pipe tables — Discord does not render these either
# --------------------------------------------------------------------------

_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


def _split_pipe_row(line: str) -> List[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [_clean(cell) for cell in line.split("|")]


def replace_pipe_tables(text: str) -> Tuple[str, int]:
    lines = text.splitlines()
    out: List[str] = []
    count = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        is_row = line.strip().startswith("|") and line.count("|") >= 2
        separator_next = (
            is_row
            and i + 1 < len(lines)
            and _SEPARATOR_RE.match(lines[i + 1])
            and "-" in lines[i + 1]
        )
        if not separator_next:
            out.append(line)
            i += 1
            continue

        rows = [_split_pipe_row(line)]
        j = i + 2
        while j < len(lines) and lines[j].strip().startswith("|"):
            rows.append(_split_pipe_row(lines[j]))
            j += 1

        rendered = render_rows(rows, 1)
        if rendered is None:
            out.extend(lines[i:j])
        else:
            out.append(rendered)
            count += 1
        i = j

    return "\n".join(out), count
