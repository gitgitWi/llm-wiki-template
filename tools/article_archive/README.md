# article-archive

URL in, markdown in the wiki out. Extraction, Korean summary, Korean
translation, and a browser re-read — with no idea what a Discord channel is.

Front ends drive it over the CLI: the Hermes plugin posts a card into a Discord
thread, `/ingest` runs the same commands from Claude Code. Both get the same
files.

## Commands

```bash
python3 tools/article_archive/cli.py scrap <url> --json       # -> raw/articles/<stem>.md
python3 tools/article_archive/cli.py summarize <stem> --json   # -> wiki/digests/<stem>.md
python3 tools/article_archive/cli.py translate <stem> --json   # -> raw/articles/<stem>.ko.md
python3 tools/article_archive/cli.py browser <stem> --json     # re-extract, replace the raw file
python3 tools/article_archive/cli.py xarticle <url> --json     # pull a quoted X Article
python3 tools/article_archive/cli.py show <url>                # extract, print, write nothing
```

`--json` prints one object on stdout and nothing else — that is the contract a
front end parses. Human output goes to stderr, so the two never mix.

`scrap` returns a **stem** (`2026-08-17-things-we-learned-about-llms-in-2024`).
Every later pass takes that stem instead of the URL, so nothing is fetched
twice. Keep it; the tool has no URL→stem index.

**`scrap` makes no model call.** Extraction is deterministic scripting, and
tags arrive later with the summary — archiving a link costs nothing but the
fetch.

## Where things land, and why

| Pass | File | Published? |
|---|---|---|
| `scrap` | `raw/articles/<stem>.md` | no |
| `translate` | `raw/articles/<stem>.ko.md` | no |
| `summarize` | `wiki/digests/<stem>.md` | yes, after `/publish` |

The original and its full translation are someone else's article — a complete
translation is if anything *more* of a derivative work than the extract, so it
sits with the source in `raw/`, which the web build excludes and (in the public
template) git ignores. The summary is ours, so it is the piece that can be
published.

`scrap` writes `raw/` once and only `browser` replaces it — that is a better
capture of the same source, not an edit.

## Committing

Every pass commits and pushes what it wrote — an archive that exists only on
one laptop is half an archive. Order is **commit → fetch → rebase → push**:
pulling into a dirty tree is how you lose a file you just generated, so the
commit happens first and the worst case is a local commit that has not gone out
yet.

A diverged remote that will not rebase cleanly aborts the rebase and skips the
push, leaving the commit local. Nothing here force-pushes, and nothing here can
fail the pass — the document is already on disk, so git trouble is a warning,
not a lost archive.

Two things it refuses to commit, both on purpose:

- **gitignored paths.** In the public template `raw/` is ignored, so `scrap`
  and `translate` write nothing committable. That is the normal case, not an
  error, so those paths are filtered out before `git add` rather than tried and
  apologised for.
- **anything marked `visibility: private`**, while `git_require_public` is on.
  In a public repo committing a file *is* publishing it, more directly than the
  web app would — so the frontmatter field that means "not for publication" is
  honoured at the repo boundary too. Setting a digest to private is the escape
  hatch for a summary that turns out to be too personal to share.

The commit is pathspec-limited to the files the pass wrote, so whatever else
happens to be staged in the repo is not swept into it.

A private fork turns `git_require_public` off and sets `digest_visibility` back
to `private`: there the repo itself is the boundary and everything belongs in
it.

## Extraction tiers

| Tier | When | Typical |
|---|---|---|
| `fxtwitter` | `x.com` / `twitter.com` | ~0.6 s |
| `defuddle:http` | everything else, tried first | ~0.8 s |
| `defuddle:browser` | tier 2 returned fewer than `min_word_count` words | ~5 s |

Tier 3 launches Chromium through `agent-browser`, grabs the rendered DOM, and
pipes it back into defuddle. It only runs when the plain HTTP fetch came up
short, so client-rendered pages are covered without every archive paying for a
browser launch.

Before any of it, one ranged GET checks the status. defuddle fetches the page
itself and reports a 404 body as a successful parse, which is how a dead link
ends up archived as an article titled "404 page not found". 401/403/429 are
bot walls rather than missing pages, so those still fall through to the browser
tier — a real fingerprint often gets where a script does not.

Inline `<svg>` and `data:` URIs are replaced with a caption line rather than
deleted, so the archive still shows a figure was there. On a diagram-heavy
article that is a third of the payload, and the translator would otherwise be
billed for tokens that can only come back as noise.

## The AI passes are agent runs over files

Each pass is **one** `cline` session. The prompt names paths, never content:

```
scratch/
  source.md        <- written by the script
  translation.md   <- written by the agent
```

The script copies the article body into a fresh scratch directory, tells the
agent to read `./source.md` and write `./translation.md`, then reads the answer
back and assembles the final document with proper frontmatter.

This is why there is no chunking, no concurrency, and no token budget in the
settings. Stuffing text into a prompt means fitting an output ceiling, which
means splitting, which means one request per chunk — and every chunk is an
independent session that cannot see the others' word choices, so terminology
drifts across the article. Handing over a file removes the whole class of
problem: the agent works through a long document the way a person would.

**Isolation.** `--auto-approve` has to be on for a non-interactive run, so the
agent gets a directory containing exactly what it needs and nothing it could
damage. It never sees the repo — that is why the source is *copied* rather than
pointed at in place. Do not "simplify" this by setting the agent's cwd to the
wiki.

Frontmatter stays code-owned. The agent writes prose; `documents.py` writes the
schema. A model cannot drift the document format.

### Checks on what comes back

Truncation is the failure mode that matters: it leaves half an article in the
archive with nothing to show anything went wrong. Two checks, structure first
because it is the sharper signal — the translator is told to preserve markdown
exactly, so a complete pass returns the same headings.

| Check | Signal |
|---|---|
| truncated | output has < 60% of the source's headings, or < 25% of its characters |
| untranslated | output equals input, or prose went in and no Hangul came out |

Either one fails the route, which falls through to the next entry in
`agent_fallbacks` and puts the failed one on a 10-minute cooldown.

### Measured

Full-article translation, `cline:deepseek/deepseek-v4-flash`, `--thinking low`:

| Source | Time | Output ratio |
|---|---|---|
| 11,923 chars | 2m15s | 0.56 |
| 40,162 chars | 14m38s | 0.74 |

Roughly **22 seconds per 1,000 characters**, and there is no parallelism to
hide it — one document, one run. That is the price of the trade: a chunked
version of the same article would finish sooner but with terminology drifting
between chunks.

Two settings follow from that number and have to move together:
`translate_max_chars` (80k ≈ 29 min) sits just under `agent_timeout` (30 min),
so an article too long to finish is refused up front instead of failing after
half an hour. The Hermes plugin allows 35 minutes so the tool's limit is the
one that governs.

Summarization is not affected — it is one pass regardless of length (~2 min).

## Per-pass model and effort

| Pass | Default effort | Why |
|---|---|---|
| `translate` | `low` | Mechanical work over a long document; effort buys latency more than quality. |
| `summary` | `high` | One run per article, and the piece that gets published. |

`<pass>_model` overrides the model for that pass; empty means `agent_model`.

## Settings

Defaults are in `settings.py`. Override with `config.json` next to it
(gitignored, so a private fork points at its own repo without conflicting on
template merges), or with `ARTICLE_ARCHIVE_<KEY>` environment variables.

| Key | Default | Meaning |
|---|---|---|
| `wiki_root` | the repo this lives in | Where files are written. |
| `git_autocommit` / `git_push` | `true` / `true` | Commit and push after each pass. `--no-sync` skips both for one run. |
| `git_require_public` | `true` | Refuse to commit `visibility: private` documents. Turn off in a private fork. |
| `git_remote` / `git_branch` | `origin` / current | Where to push. |
| `digest_visibility` | `public` | What new digests are marked. `private` in a private fork. |
| `uri_mode` | `auto` | `auto` reports a GitHub blob URL once the file is pushed, else the path. `path` / `github` force one. |
| `github_repo` / `github_branch` | `""` / `main` | Only for `uri_mode: github`; `auto` reads owner/repo off the git remote. |
| `check_http_status` | `true` | Reject 4xx/5xx before extracting. |
| `min_word_count` | `120` | Below this, retry extraction through the browser. |
| `browser_fallback` | `true` | Allow the browser tier at all. |
| `reformat_tables` | `false` | Flatten tables into fixed-width grids. Only useful for chat clients that cannot render them; a markdown file can. |
| `agent_bin` | `cline` | The agent CLI. Must accept `-s`, `-m`, `-P`, `--thinking`, `--json`. |
| `agent_provider` / `agent_model` | `cline` / `cline:deepseek/deepseek-v4-flash` | Preferred route. |
| `agent_fallbacks` | `[]` | Tried in order. `"<provider>\|<model>"` pins a provider; a bare value is a model on `agent_provider`. The separator is `\|` because model ids contain both `/` and `:`. |
| `agent_timeout` | `1800` | Per-run ceiling. A long article is minutes. |
| `translate_max_chars` | `120000` | Refuse absurdly long sources. |
| `<pass>_model` / `<pass>_thinking` | see above | Per-pass overrides for `translate`, `summary`. |
| `xcom_expand_threads` | `false` | Follow a self-reply chain when archiving an X thread head. Costs one browser visit per X archive. |

## Install

```bash
cd tools/article_archive && npm install    # defuddle
```

Python is stdlib only — no venv, no pip. The AI passes additionally need
`cline` on PATH; `scrap`, `browser`, `xarticle` and `show` do not.

## Known gaps

- HTML `<table>` markup from defuddle is left as-is with `reformat_tables:
  false`. It renders (markdown passes HTML through) but is not converted to a
  pipe table.
- No URL→stem index. Re-scraping the same URL on a different day writes a
  second file; `/lint` is where that gets caught.
- A scraped-but-never-summarized article has no tags, because labels ride
  along with the summary.
