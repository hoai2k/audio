"""List venues (or bands) already on file, to hand to a research agent as ALREADY.

Usage:
  python3 tools/list_venues.py --town Philadelphia --town Collingswood
  python3 tools/list_venues.py --state DE
  python3 tools/list_venues.py --bands --town Philadelphia
"""
import argparse, glob, json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

ap = argparse.ArgumentParser()
ap.add_argument("--town", action="append", default=[], help="town to match (repeatable, case-insensitive)")
ap.add_argument("--state", action="append", default=[])
ap.add_argument("--bands", action="store_true", help="list bands instead of venues")
args = ap.parse_args()
towns = {t.lower() for t in args.town}
states = {s.upper() for s in args.state}

def match(town, state):
    return (not towns or (town or "").lower() in towns) and (not states or (state or "").upper() in states)

seen = {}
if args.bands:
    for f in glob.glob(str(DATA / "bands_*.json")):
        for b in json.load(open(f)):
            if match(b.get("town"), b.get("state")):
                seen[b["name"]] = f"{b['name']} ({b.get('town')})"
    for f in glob.glob(str(DATA / "census_*.json")):
        for a in json.load(open(f)).get("appearances", []):
            if match(a.get("town"), a.get("state")):
                seen.setdefault(a["band"], a["band"])
else:
    for f in glob.glob(str(DATA / "census_*.json")):
        for v in json.load(open(f)).get("venues", []):
            if match(v.get("town"), v.get("state")):
                seen[(v["name"], v.get("town"))] = f"{v['name']} ({v.get('town')}; {v.get('calendar_status')})"
    for f in glob.glob(str(DATA / "venues_*.json")):
        for v in json.load(open(f)).get("venues_crawled", []):
            if match(v.get("town"), v.get("state")):
                seen.setdefault((v["venue"], v.get("town")), f"{v['venue']} ({v.get('town')}; crawled)")
print("; ".join(sorted(seen.values())))
