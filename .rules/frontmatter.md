---
updated: 2026-08-19
description: Frontmatter contract for every markdown file in this repo — the wiki tier (wiki/, notes/) and the project-doc tier (.dev/, tools/, apps/, .rules/).
read_when: Before creating or editing any .md file here, or when changing the Astro content schema, the archive tool's writer, or /lint.
agent: claude-opus-5 / claude-code
tags: [frontmatter, schema, convention, docs, agent-readability]
---

# Frontmatter rules

An agent decides whether to keep reading a file from its first ~10 lines.
Frontmatter is that decision surface, so it answers three questions: **how fresh
is this**, **what is inside**, **why would I open it**. Everything else is noise.

Written in English — keys, values, and this document — because every consumer of
these fields is a tool or an agent. Prose in `wiki/` stays Korean.

## Two tiers

| Tier | Where | Block |
|---|---|---|
| **Wiki** | `wiki/`, `notes/`, and what the archive tool writes into `raw/` | full schema below — the web app validates it |
| **Project doc** | `.dev/`, `tools/`, `apps/`, `.rules/`, plans, handoffs, reviews | the 5-field block below |

### Tier A — wiki and notes

```yaml
---
title: LLM Wiki 방법론            # Korean is fine here — only here
type: source | note | concept | entity | synthesis
visibility: public | private     # missing or misspelled ⇒ treated as private
domains: [ai]                    # closed vocabulary, see below
tags: [llm, pkm]                 # open vocabulary, extracted from the content
status: living | draft | archived
created: 2026-08-17
updated: 2026-08-17
description: One line — what this page holds.        # new pages and pages you edit
read_when: Answering how the wiki schema evolved.    # optional
agent: claude-opus-5 / claude-code                   # who wrote it, when known
source:                          # only in raw/ and wiki/digests/
  url: https://...
  author: 저자명
  captured: 2026-08-17
related: ["[[other-page]]"]      # wikilinks to related pages
---
```

`domains` closed vocabulary (drives web-app navigation — ask the user before
adding a value): `ai` · `dev` · `career` · `product` · `infra` · `misc`.
A source that spans fields gets **several `domains`**, not a new folder.

The executable copy of this schema is `apps/web/src/content.config.ts`; the
domain list is duplicated in `tools/article_archive/passes.py`. Change all three
together.

Tool-written digests carry a `summary:` block (provider/model/backend) instead
of `agent:` — that block already records which model produced the text.

### Tier B — project docs

```yaml
---
updated: 2026-08-19
description: One line — what is in this document.
read_when: The situation that makes this file worth opening (and when to skip it).
agent: claude-opus-5 / claude-code
tags: [webapp, astro, handoff]
---
```

`updated` and `description` are required; `read_when` is required whenever the
file is not self-evident from its title; `agent` and `tags` are strongly
preferred. No `visibility` — nothing outside `wiki/` and `notes/` is published
by the web app, and nothing outside them is scanned by the leak guard.

## Shared rules

1. **Keep it short enough to skim.** Tier B is ten lines or fewer; Tier A runs
   longer only because of the schema itself (`source:`, `related:`) and should
   stay under fifteen. If a field does not help an agent decide whether to read
   on, it does not belong in frontmatter.
2. **Dates are ISO `YYYY-MM-DD`**, and `updated` is bumped on every substantive
   edit. (The key is `updated`, not `updatedAt` — the wiki schema, the archive
   tool, and every existing page already use `updated`.)
3. **`description` states content, `read_when` states purpose.** One line each,
   no trailing period needed, no marketing.
4. **`agent` is `<model> / <harness>`** — e.g. `claude-opus-5 / claude-code`,
   `solar-pro4 / hermes`, `gpt-5 / codex`. If you do not know which model or
   harness produced a document, ask the user rather than guessing. Omit the
   field for documents a human wrote.
5. **`tags` are extracted from the content** — 3–6 lowercase kebab-case slugs,
   specific over generic, no `#`.
6. **Never include**: the file name or path (the agent already opened it), line
   counts or file size, a table of contents, or anything re-derivable from the
   body or from git.

## Exemptions

- **`README.md` at the repo root** — GitHub renders frontmatter as a table on
  the landing page. Nested READMEs (`apps/web/`, `tools/`) are agent-facing and
  do carry the Tier B block.
- **`.claude/commands/*.md`** — the frontmatter format belongs to Claude Code
  (`description`, `argument-hint`). Do not add fields to it.
- **`raw/` originals** — written by the archive tool, never hand-edited (see
  `CLAUDE.md` §1).
- **Generated files** (`dist/`, `graphify-out/`).
