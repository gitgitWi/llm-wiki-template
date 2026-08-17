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

Inline `<svg>` and `data:` URIs are replaced with a caption line rather than
deleted, so the archive still shows a figure was there. On a diagram-heavy
article that is a third of the payload, and the translator would otherwise be
billed for tokens that can only come back as noise.

## LLM backend

Detected, not configured:

1. **hermes** — `agent.auxiliary_client`, when this runs on Hermes' interpreter.
2. **openai** — any OpenAI-compatible `/v1/chat/completions`, when
   `ARTICLE_ARCHIVE_OPENAI_BASE_URL` is set. Works with Ollama and OpenRouter.
3. **none** — `scrap` and `show` still work; the AI passes report unavailable.

Above whichever answers, a route ladder (`llm_provider`/`llm_model`, then
`llm_fallbacks`) with a 10-minute cooldown on a refused route, so one long
article does not re-probe a dead provider once per chunk. A route that hands
back the source text instead of Korean is treated as a failure — some
open-weight models silently echo long inputs, which looks like success.

The route that answered is written into the file:

```yaml
summary:
  updated: 2026-08-17T16:39:53+09:00
  provider: copilot
  model: gpt-4.1
  backend: hermes
```

## Settings

Defaults are in `settings.py`. Override with `config.json` next to it
(gitignored, so a private fork points at its own repo without conflicting on
template merges), or with `ARTICLE_ARCHIVE_<KEY>` environment variables.

| Key | Default | Meaning |
|---|---|---|
| `wiki_root` | the repo this lives in | Where files are written. |
| `uri_mode` | `path` | `github` reports blob URLs — set this in a private fork. |
| `github_repo` / `github_branch` | `""` / `main` | Used by `uri_mode: github`. |
| `min_word_count` | `120` | Below this, retry extraction through the browser. |
| `browser_fallback` | `true` | Allow the browser tier at all. |
| `reformat_tables` | `false` | Flatten tables into fixed-width grids. Only useful for chat clients that cannot render them; a markdown file can. |
| `llm_provider` / `llm_model` | `ollama-cloud` / `deepseek-v4-flash:0731` | Preferred route. |
| `llm_fallbacks` | `["copilot/gpt-4.1", …]` | Tried in order. Only the first `/` separates provider from model. |
| `translate_chunk_chars` | `3500` | Source characters per translation request. |
| `translate_max_chars` | `120000` | Skip translation past this size. |
| `summary_source_chars` | `24000` | Front slice sent to the summarizer. |
| `xcom_expand_threads` | `false` | Follow a self-reply chain when archiving an X thread head. Costs one browser visit per X archive. |

## Install

```bash
cd tools/article_archive && npm install    # defuddle
```

Python is stdlib only — no venv, no pip.

## Known gaps

- HTML `<table>` markup from defuddle is left as-is with `reformat_tables:
  false`. It renders (markdown passes HTML through) but is not converted to a
  pipe table.
- No URL→stem index. Re-scraping the same URL on a different day writes a
  second file; `/lint` is where that gets caught.
