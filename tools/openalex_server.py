#!/usr/bin/env python3
"""OpenAlex MCP server (stdio) — scholarly literature search.

OpenAlex (openalex.org) is a fully public scholarly database: ~250M works,
all fields, no API key required. This server wraps its REST API so an agent
can search the literature directly.

No credentials. OPENALEX_MAILTO (optional, ~/.claude/.env) joins the polite
pool for faster responses.

Written for the UVA "Vibe Coding" faculty workshop, July 2026.
"""
import os
import pathlib

import httpx
from mcp.server.fastmcp import FastMCP


def _load_dotenv():
    p = pathlib.Path.home() / ".claude" / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()
BASE = "https://api.openalex.org"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")

mcp = FastMCP("openalex")


def _get(path: str, **params) -> dict:
    if MAILTO:
        params["mailto"] = MAILTO
    r = httpx.get(f"{BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _brief(w: dict) -> dict:
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    return {
        "title": w.get("display_name"),
        "year": w.get("publication_year"),
        "venue": src.get("display_name"),
        "cited_by_count": w.get("cited_by_count"),
        "doi": w.get("doi"),
        "openalex_id": w.get("id"),
        "is_open_access": (w.get("open_access") or {}).get("is_oa"),
        "authors": [a["author"]["display_name"]
                    for a in (w.get("authorships") or [])[:6]],
    }


@mcp.tool()
def search_works(query: str, from_year: int = 0, to_year: int = 0,
                 sort: str = "cited_by_count:desc", limit: int = 10) -> list:
    """Search scholarly works across all fields (medicine, engineering,
    humanities, ...). sort: 'cited_by_count:desc' | 'publication_date:desc'
    | 'relevance_score:desc'. Returns title/year/venue/citations/DOI/authors."""
    filters = []
    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")
    params = {"search": query, "sort": sort, "per-page": min(limit, 50)}
    if filters:
        params["filter"] = ",".join(filters)
    data = _get("works", **params)
    return [_brief(w) for w in data.get("results", [])]


@mcp.tool()
def get_work(doi_or_openalex_id: str) -> dict:
    """Full record for one work (by DOI like 10.1126/science.adh2586, a DOI
    URL, or an OpenAlex id like W4382222099), including the abstract."""
    key = doi_or_openalex_id.strip()
    if key.lower().startswith("10."):
        key = f"https://doi.org/{key}"
    w = _get(f"works/{key}")
    out = _brief(w)
    inv = w.get("abstract_inverted_index")
    if inv:
        pos = {p: t for t, ps in inv.items() for p in ps}
        out["abstract"] = " ".join(pos[i] for i in sorted(pos))
    out["type"] = w.get("type")
    out["topics"] = [t["display_name"] for t in (w.get("topics") or [])[:5]]
    return out


@mcp.tool()
def count_works_by_year(query: str, from_year: int = 2015) -> list:
    """Publication counts per year for a topic — the growth curve of a field.
    Returns [{year, works_count}, ...] sorted by year."""
    data = _get("works", search=query, group_by="publication_year",
                filter=f"from_publication_date:{from_year}-01-01", **{"per-page": 200})
    rows = [{"year": int(g["key"]), "works_count": g["count"]}
            for g in data.get("group_by", []) if g["key"].isdigit()]
    return sorted(rows, key=lambda r: r["year"])


@mcp.tool()
def top_venues(query: str, limit: int = 10) -> list:
    """Where a topic is published: the venues (journals/conferences) with the
    most works matching the query."""
    data = _get("works", search=query, group_by="primary_location.source.id",
                **{"per-page": 200})
    return [{"venue": g["key_display_name"], "works_count": g["count"]}
            for g in data.get("group_by", [])[:limit]]


if __name__ == "__main__":
    mcp.run()
