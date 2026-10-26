"""Shrink a venue's archived pages to one digest for lineup extraction (briefs/wayback_extract.md).

Captures repeat most of their text. For each venue this drops site chrome (lines that appear in most
captures, like menus and footers) and captures identical to an earlier one, but keeps lines that recur
in only some captures, since an act's name can repeat on different dates. Structured event blocks are always kept.

Usage: python3 tools/wayback_digest.py [wayback_dir] [--only slug1,slug2]
Writes <wayback_dir>/<slug>/DIGEST.md and prints each digest's size.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
wb = Path(args[0]) if args else ROOT / "cache" / "wayback"
only = None
if "--only" in sys.argv:
    only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

DATEISH = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b|\b\d{1,2}/\d{1,2}(/\d{2,4})?\b|\b20(25|26)-\d{2}-\d{2}\b|\b(mon|tue|wed|thu|fri|sat|sun)[a-z]*\b", re.I)
CHROME = re.compile(r"^(home|about|contact|menu|shop|cart|login|sign in|subscribe|privacy|terms|search|more|book now|buy tickets|tickets|get tickets|learn more|read more|view all|©.*|copyright.*|skip to.*|use tab to navigate.*)$", re.I)

for vdir in sorted(p for p in wb.iterdir() if p.is_dir()):
    if only and vdir.name not in only:
        continue
    files = sorted(vdir.glob("*.txt"))
    if not files:
        continue
    pages = []
    for f in files:
        lines = f.read_text(errors="replace").splitlines()
        pages.append((lines[:2], [l.strip() for l in lines[2:]]))
    # Lines on most captures are site chrome
    freq = {}
    for _, body in pages:
        for s in set(body):
            freq[s] = freq.get(s, 0) + 1
    chrome = {s for s, n in freq.items() if len(pages) >= 4 and n > 0.6 * len(pages)}
    out, seen_pages = [], set()
    for head, body in pages:
        keep, in_events = [], False
        for s in body:
            if s.startswith("EVENTS (from structured data)"):
                in_events = True
            elif in_events and not s:
                in_events = False
            if not s or len(s) > 400 or (not in_events and (s in chrome or (len(s) < 40 and CHROME.match(s)))):
                continue
            keep.append(s)
        sig = "\n".join(keep)
        if not keep or sig in seen_pages or not any(DATEISH.search(l) for l in keep):
            continue
        seen_pages.add(sig)
        out.append("\n".join(head) + "\n" + "\n".join(keep[:500]))
    (vdir / "DIGEST.md").write_text(f"# {vdir.name}\n\n" + "\n\n---\n\n".join(out))
    print(f"{vdir.name}: {len(files)} pages -> {len(out)} useful captures, {sum(map(len, out)) // 1000} KB")
