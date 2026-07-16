#!/usr/bin/env python3
"""Fetch 1,000 papers on generative AI from OpenAlex into data/genai_papers.csv.

The script the agent writes live in the research beat. It cleans on the way
in — tidies stray formatting tags out of titles, removes duplicate
records — and prints a report of what it did.

Usage:
    python3 tools/fetch_genai_papers.py            # -> data/genai_papers.csv
    python3 tools/fetch_genai_papers.py -n 100 --out /tmp/sample.csv
"""
import argparse
import csv
import pathlib
import re

import httpx

BASE = "https://api.openalex.org/works"
QUERY = "generative AI"
PER_PAGE = 200  # OpenAlex maximum
TAG = re.compile(r"<[^>]+>")


def abstract_text(inv: dict | None) -> str:
    """OpenAlex stores abstracts as an inverted index; rebuild the plain text."""
    if not inv:
        return ""
    pos = {p: t for t, ps in inv.items() for p in ps}
    return " ".join(pos[i] for i in sorted(pos))


def fetch(n: int) -> list[dict]:
    rows, page = [], 1
    while len(rows) < n:
        r = httpx.get(BASE, params={
            "search": QUERY,
            "per-page": min(PER_PAGE, n - len(rows)),
            "page": page,
            "select": "display_name,publication_year,primary_location,"
                      "cited_by_count,doi,abstract_inverted_index",
        }, timeout=60)
        r.raise_for_status()
        batch = r.json().get("results", [])
        if not batch:
            break
        for w in batch:
            src = (w.get("primary_location") or {}).get("source") or {}
            rows.append({
                "title": w.get("display_name") or "",
                "year": w.get("publication_year") or "",
                "venue": src.get("display_name") or "",
                "cited_by_count": w.get("cited_by_count") or 0,
                "doi": w.get("doi") or "",
                "abstract": abstract_text(w.get("abstract_inverted_index")),
            })
        print(f"  page {page}: {len(rows)} fetched")
        page += 1
    return rows[:n]


def clean(rows: list[dict]) -> tuple[list[dict], int, int]:
    """Tidy titles, remove duplicates. Returns (rows, fixed, dropped)."""
    fixed = sum(1 for r in rows if TAG.search(r["title"]))
    for r in rows:
        r["title"] = TAG.sub("", r["title"]).strip()
    seen, out, dropped = set(), [], 0
    for r in rows:
        key = r["doi"].lower() if r["doi"] else (r["title"].lower(), r["year"])
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        out.append(r)
    return out, fixed, dropped


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", type=int, default=1000, help="number of papers")
    ap.add_argument("--out", default=None, help="output CSV (default data/genai_papers.csv)")
    args = ap.parse_args()

    out = pathlib.Path(args.out) if args.out else \
        pathlib.Path(__file__).resolve().parent.parent / "data" / "genai_papers.csv"
    raw = fetch(args.n)
    rows, fixed, dropped = clean(raw)
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    missing = sum(1 for r in rows if not r["abstract"])
    print(f"fetched: {len(raw)}")
    print(f"tidied:  {fixed} titles had stray formatting tags — removed")
    print(f"removed: {dropped} duplicates (same DOI, or same title+year)")
    print(f"kept:    {len(rows)} rows -> {out}")
    print(f"noted:   {missing} rows have no abstract")


if __name__ == "__main__":
    main()
