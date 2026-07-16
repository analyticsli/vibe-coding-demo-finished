# CLAUDE.md

Companion repo for **"Vibe Coding: Rapid Research Prototyping with AI"**
(UVA Faculty Upskilling, July 2026 — Jingjing Li, McIntire School of Commerce).
This file is the project briefing an agent reads at the start of every session —
keep it short, factual, and current.

## What's in this repo

```
site/       my faculty homepage lives here. Demo 1 starts by fetching the live
            site (sites.google.com/view/jingjingli) and saving its content as
            plain HTML, then redesigns it (text content only — images on the
            live site are script-loaded and are not part of the exercise)
tools/      openalex_server.py — an MCP server (~120 lines) wrapping the public
            OpenAlex scholarly database; no API key needed
data/       genai_papers.csv — 1,000 real papers on generative AI, fetched
            and cleaned by tools/fetch_genai_papers.py (which prints a report
            of what it did)
feeds/      generated literature dashboards land here, one HTML file per topic
.claude/skills/   reusable task recipes (see the literature-feed skill)
```

## Connecting the literature socket

```
claude mcp add openalex python3 tools/openalex_server.py
```

then restart and check with `/mcp`. Tools: `search_works`, `get_work`,
`count_works_by_year`, `top_venues`.

## Conventions

- Generated pages use the palette: navy `#0C255B`, teal `#007681`,
  orange `#F47321`; Georgia for headings, system sans for body.
- Generated dashboards are self-contained single HTML files in `feeds/`.
- Public data only. Never put student records, unpublished results, or
  credentials anywhere in this repo — it is public.
- Commit early and often; the history is part of what this repo teaches.
