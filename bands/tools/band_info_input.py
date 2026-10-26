"""List bands on the city pages that are missing a genre, most active first, as input for briefs/band_info.md.

Usage: python3 tools/band_info_input.py [--batch 120] [--min-shows 1]
Reads every built city page; writes bands/cache/band_info_input_<n>.json in batches and prints a summary.
Build the cities first so their page data is current.
"""
import glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
batch = int(sys.argv[sys.argv.index("--batch") + 1]) if "--batch" in sys.argv else 120
min_shows = int(sys.argv[sys.argv.index("--min-shows") + 1]) if "--min-shows" in sys.argv else 1
done = set()
for f in glob.glob(str(ROOT / "data" / "bandinfo_*.json")):
    done |= {re.sub(r"[^a-z0-9]", "", i["name"].lower()) for i in json.load(open(f))}

need = {}
for page in glob.glob(str(ROOT / "*" / "index.html")):
    html = Path(page).read_text()
    m = re.search(r"const BANDS = (.*?);\nconst TOWNS", html, re.S)
    if not m:
        continue
    for b in json.loads(m.group(1).replace("<\\/", "</")):
        key = re.sub(r"[^a-z0-9]", "", b["name"].lower())
        if b.get("genres") or key in done:
            continue
        apps = b.get("appearances") or []
        cur = need.get(key)
        if cur and len(cur["shows"]) >= len(apps):
            continue
        need[key] = {
            "name": b["name"], "home_base": b.get("home_base"), "mapped_town": f"{b['town']}, {b['state']}",
            "shows": [f"{a['date']} {a['venue']}, {a['town']}" for a in apps[:8]],
            "show_count": len(apps), "known_links": b.get("links") or {},
        }

ranked = sorted((n for n in need.values() if n["show_count"] >= min_shows), key=lambda n: (-n["show_count"], n["name"]))
out = ROOT / "cache"
out.mkdir(exist_ok=True)
for old in out.glob("band_info_input_*.json"):
    old.unlink()
for i in range(0, len(ranked), batch):
    (out / f"band_info_input_{i // batch + 1}.json").write_text(json.dumps(ranked[i:i + batch], ensure_ascii=False, indent=1))
counts = {}
for n in ranked:
    counts[n["show_count"]] = counts.get(n["show_count"], 0) + 1
print(f"{len(ranked)} bands need info, in {-(-len(ranked) // batch)} batches of {batch}; by show count: "
      + ", ".join(f"{k}:{v}" for k, v in sorted(counts.items(), reverse=True)[:12]))
