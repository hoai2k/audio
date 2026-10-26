"""List a city's venues that have no written summary yet, as input for briefs/venue_summaries.md.

Usage: python3 tools/summary_input.py lambertville [--all]
Writes bands/cache/venue_summary_input.json. Build the city first, so its page data is current.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    sys.exit(__doc__)
city = ROOT / args[0]
page = (city / "index.html").read_text()
venues = json.loads(re.search(r"const VENUES = (.*?);\nconst STATUS", page, re.S).group(1).replace("<\\/", "</"))
bands = json.loads(re.search(r"const BANDS = (.*?);\nconst TOWNS", page, re.S).group(1).replace("<\\/", "</"))
done = json.load(open(ROOT / "data" / "venue_summaries.json"))
genre = {b["name"]: b.get("genre") or "" for b in bands}
acts = {}
for r in json.load(open(city / "shows.json")):
    acts.setdefault(r["venue_key"], {}).setdefault(r["band"], 0)
    acts[r["venue_key"]][r["band"]] += 1

out = []
for v in venues:
    if v["key"] in done and "--all" not in sys.argv:
        continue
    a = acts.get(v["key"], {})
    top = sorted(a, key=lambda n: -a[n])[:25]
    out.append({"key": v["key"], "name": v["name"], "town": v["town"], "state": v["state"], "kind": v.get("kind"),
                "music_frequency": v.get("frequency"), "crawl_notes": v.get("notes"), "coverage": v.get("coverage"),
                "acts_sample": [f"{n} ({genre[n]})" if genre.get(n) else n for n in top], "distinct_acts": len(a)})
(ROOT / "cache").mkdir(exist_ok=True)
(ROOT / "cache" / "venue_summary_input.json").write_text(json.dumps(out, ensure_ascii=False, indent=0))
print(f"{len(out)} venues need summaries -> cache/venue_summary_input.json")
