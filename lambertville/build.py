"""Merge band and venue research into index.html.

Usage: python3 build.py [out.html]   (default: index.html next to this script)
Research JSON lives in data/: bands_*.json (home-base searches), venues_*.json and census_*.json (venue crawls).
"""
import glob, json, re, sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = Path(ARGS[0]) if ARGS else HERE / "index.html"

TOWNS = {
    "Lambertville, NJ": [40.3654, -74.9429], "New Hope, PA": [40.3643, -74.9513], "Stockton, NJ": [40.4087, -74.9785],
    "Frenchtown, NJ": [40.5262, -75.0616], "Flemington, NJ": [40.5123, -74.8593], "Hopewell, NJ": [40.3890, -74.7621],
    "Pennington, NJ": [40.3284, -74.7907], "Doylestown, PA": [40.3101, -75.1299], "Newtown, PA": [40.2293, -74.9368],
    "Yardley, PA": [40.2457, -74.8460], "Quakertown, PA": [40.4418, -75.3416], "Lahaska, PA": [40.3462, -75.0313],
    "Washington Crossing, PA": [40.2937, -74.8735], "Bristol, PA": [40.1007, -74.8518], "Sellersville, PA": [40.3537, -75.3049],
    "Perkasie, PA": [40.3720, -75.2927], "Levittown, PA": [40.1551, -74.8288], "Langhorne, PA": [40.1745, -74.9227],
    "Trenton, NJ": [40.2171, -74.7429], "Princeton, NJ": [40.3573, -74.6672], "Ewing, NJ": [40.2698, -74.7996],
    "Hamilton, NJ": [40.2115, -74.6796], "Lawrenceville, NJ": [40.2968, -74.7296], "Bordentown, NJ": [40.1462, -74.7118],
    "New Brunswick, NJ": [40.4862, -74.4518], "Highland Park, NJ": [40.4959, -74.4243], "Metuchen, NJ": [40.5432, -74.3632],
    "Edison, NJ": [40.5187, -74.4121], "Somerville, NJ": [40.5743, -74.6099], "Bound Brook, NJ": [40.5684, -74.5385],
    "Raritan, NJ": [40.5695, -74.6329], "Bridgewater, NJ": [40.6009, -74.6482], "Easton, PA": [40.6884, -75.2207],
    "Bethlehem, PA": [40.6259, -75.3705], "Allentown, PA": [40.6084, -75.4902], "Nazareth, PA": [40.7404, -75.3096],
    "Emmaus, PA": [40.5395, -75.4968], "Phillipsburg, NJ": [40.6937, -75.1902], "Milford, NJ": [40.5687, -75.0946],
    "Clinton, NJ": [40.6368, -74.9099], "Washington, NJ": [40.7584, -74.9793], "Philadelphia, PA": [39.9526, -75.1652],
    "Lansdale, PA": [40.2415, -75.2838], "Ambler, PA": [40.1543, -75.2216], "Jenkintown, PA": [40.0957, -75.1252],
    "Glenside, PA": [40.1023, -75.1521], "Norristown, PA": [40.1215, -75.3399], "Conshohocken, PA": [40.0793, -75.3016],
    "Phoenixville, PA": [40.1304, -75.5149], "Asbury Park, NJ": [40.2204, -74.0121], "Red Bank, NJ": [40.3471, -74.0643],
    "Freehold, NJ": [40.2601, -74.2738], "Long Branch, NJ": [40.3043, -73.9924], "Morristown, NJ": [40.7968, -74.4815],
    "Dover, NJ": [40.8840, -74.5621], "Rockaway, NJ": [40.9012, -74.5143], "Mount Holly, NJ": [39.9929, -74.7871],
    "Moorestown, NJ": [39.9690, -74.9488], "Cherry Hill, NJ": [39.9348, -75.0307], "Collingswood, NJ": [39.9182, -75.0713],
}

TOWN_FIX = {"Upper Bucks County": "Quakertown"}

def clean_town(t):
    t = re.sub(r"\s*\(.*?\)", "", t).split(" / ")[0].strip()
    t = re.sub(r"\s+area$", "", t)
    return TOWN_FIX.get(t, t)

REGIONS = {
    "bucks_hunterdon": "River Towns, Bucks & Hunterdon", "hunterdon2": "River Towns, Bucks & Hunterdon",
    "mercer_middlesex": "Central Jersey", "somerset": "Central Jersey", "montco": "Philadelphia & Montco",
    "lehigh": "Lehigh Valley", "philly": "Philadelphia & Montco", "shore_morris": "Shore, Morris & Camden",
}
DROP = {"bouncingsouls", "thursday", "relapsed", "wonderyears", "bryanhansenband", "sonicfoundry"}
# Entries found by the home-base searches that are really "plays here often"
PLAYS_HERE = {"lastbigband": "Berks County, Lehigh Valley and West Chester players"}

bands, seen = [], {}
for f in sorted(glob.glob(str(DATA / "bands_*.json"))):
    region = REGIONS[Path(f).stem.removeprefix("bands_")]
    for b in json.load(open(f)):
        b["region"] = region
        b["town"] = clean_town(b["town"])
        b["state"] = (b.get("state") or "").strip().upper()[:2]
        key = re.sub(r"[^a-z0-9]", "", b["name"].lower().removeprefix("the "))
        if key in seen or key in DROP:
            continue
        b["links"] = {k: v for k, v in (b.get("links") or {}).items() if v}
        if b.get("image") and re.search(r"fbcdn|cdninstagram", b["image"]):
            b["image"] = None
        b["basis"] = "based"
        if key in PLAYS_HERE:
            b["basis"], b["home_base"], b["plays_here"] = "plays_here", PLAYS_HERE[key], True
        seen[key] = b
        bands.append(b)

# ---- Venue data: every dated booking from every crawl, pooled ----
band_key = lambda name: re.sub(r"[^a-z0-9]", "", name.lower().replace("&", "and").removeprefix("the "))
venue_key = lambda name, town: re.sub(r"[^a-z0-9]", "", re.sub(r"\s*\(.*?\)", "", name).lower().replace("&", "and").removeprefix("the ")) + "|" + (town or "").lower()
OUT_OF_STATE = re.compile(r"\b(NY|CA|GA|MA|MD|DE|CT|VA|TN|TX|IL|OH|FL)\b|New York|Brooklyn|Nashville|Boston|Atlanta|Los Angeles")
IN_STATE = re.compile(r"\b(PA|NJ)\b|Pennsylvania|New Jersey")

def norm_app(a, band_name):
    return {"band": band_name, "venue": a["venue"].strip(), "town": clean_town(a.get("town") or ""),
            "state": (a.get("state") or "").strip().upper()[:2], "date": a.get("date"),
            "source_url": a.get("source_url"), "source_type": a.get("source_type")}

apps, info, venues = {}, {}, {}

def add_app(a):
    k = (band_key(a["band"]), venue_key(a["venue"], a["town"]), a["date"])
    if a["date"] and k not in apps:
        apps[k] = a

def add_info(i):
    k = band_key(i["name"])
    cur = info.setdefault(k, {})
    for f, v in i.items():
        if v and not cur.get(f):
            cur[f] = v

def add_venue(v):
    k = venue_key(v["name"], v.get("town"))
    cur = venues.setdefault(k, {"name": v["name"], "town": clean_town(v.get("town") or ""), "state": (v.get("state") or "").upper()[:2]})
    for f, val in v.items():
        if val and not cur.get(f):
            cur[f] = val

# Earlier crawls (kept only 2+ date bands, so they add to totals but miss singles)
for f in sorted(glob.glob(str(DATA / "venues_*.json"))):
    rep = json.load(open(f))
    for v in rep.get("venues_crawled", []):
        add_venue({"name": v["venue"], "town": v.get("town"), "state": v.get("state"), "source_url": v.get("source_url"),
                   "coverage": v.get("coverage"), "calendar_status": "crawled"})
    for group in ("bands", "existing_matches"):
        for b in rep.get(group, []):
            for a in b.get("appearances", []):
                add_app(norm_app(a, b["name"]))
            if group == "bands":
                add_info({k: b.get(k) for k in ("name", "home_base", "genre", "description", "links", "image")})

# Venue census (every booking, singles included)
for f in sorted(glob.glob(str(DATA / "census_*.json"))):
    rep = json.load(open(f))
    for v in rep.get("venues", []):
        add_venue(v)
    for a in rep.get("appearances", []):
        add_app(norm_app(a, a["band"]))
    for i in rep.get("band_info", []):
        add_info(i)

# Venues seen only in appearance rows
for a in apps.values():
    add_venue({"name": a["venue"], "town": a["town"], "state": a["state"], "calendar_status": "seen_in_listings"})

by_band = {}
for a in apps.values():
    by_band.setdefault(band_key(a["band"]), []).append(a)

def separate_bookings(rows):
    # Different venue or month, so one multi-day festival counts once
    return len({(venue_key(a["venue"], a["town"]), a["date"][:7]) for a in rows})

def returns_to_town(rows):
    by_town = {}
    for a in rows:
        try:
            by_town.setdefault(a["town"], []).append(date.fromisoformat(a["date"]))
        except (TypeError, ValueError):
            pass
    return any(max(ds) - min(ds) > timedelta(days=31) for ds in by_town.values() if len(ds) > 1)

for key, rows in by_band.items():
    if key in DROP:
        continue
    rows.sort(key=lambda a: a["date"], reverse=True)
    if key in seen:
        seen[key]["appearances"] = rows
        seen[key]["plays_here"] = True
        continue
    if separate_bookings(rows) < 2:
        continue
    i = info.get(key, {})
    hb = i.get("home_base") or ""
    touring = bool(OUT_OF_STATE.search(hb) and not IN_STATE.search(hb))
    if touring and not returns_to_town(rows):
        continue
    towns_played = {}
    for a in rows:
        towns_played[(a["town"], a["state"])] = towns_played.get((a["town"], a["state"]), 0) + 1
    town, state = max(towns_played, key=towns_played.get)
    names = {}
    for a in rows:
        names[a["band"]] = names.get(a["band"], 0) + 1
    b = {"name": i.get("name") or max(names, key=names.get), "town": town, "state": state,
         "genre": i.get("genre") or "", "home_base": i.get("home_base"),
         "description": i.get("description") or "",
         "links": {k: v for k, v in (i.get("links") or {}).items() if v},
         "image": None if re.search(r"fbcdn|cdninstagram", i.get("image") or "") else i.get("image"),
         "basis": "plays_here", "plays_here": True, "appearances": rows}
    if touring:
        b["touring"] = True
    seen[key] = b
    bands.append(b)

# Descriptions that read as research notes rather than band blurbs
DESC_FIX = {"frostduo": "Scranton-based jazz duo."}
for b in bands:
    if band_key(b["name"]) in DESC_FIX:
        b["description"] = DESC_FIX[band_key(b["name"])]

for b in bands:
    if b.get("appearances"):
        n = len(b["appearances"])
        vc = {}
        for a in b["appearances"]:
            vc[a["venue"]] = vc.get(a["venue"], 0) + 1
        b["venue_summary"] = ", ".join(f"{v} ×{c}" if c > 1 else v for v, c in sorted(vc.items(), key=lambda x: -x[1]))
        if b["basis"] == "plays_here":
            b["activity"] = f"{n} area show{'s' if n > 1 else ''} in 2025–26"
            b["evidence_url"] = b["appearances"][0].get("source_url")
            if not b["description"]:
                top = max(vc, key=vc.get)
                b["description"] = f"Regular on the local circuit, most often at {top}."

print(f"appearances={len(apps)} bands_with_dates={len(by_band)} venues={len(venues)}")
extra = json.load(open(DATA / "extra_towns.json")) if (DATA / "extra_towns.json").exists() else {}
TOWNS.update(extra)
used = {f"{b['town']}, {b['state']}" for b in bands}
missing = sorted(used - TOWNS.keys())
if missing:
    print("MISSING COORDS:", missing)
towns = {k: TOWNS[k] for k in used if k in TOWNS}

# ---- Venues: location, region, who's played there ----
GEOCACHE = DATA / "geocache.json"
geocache = json.load(open(GEOCACHE)) if GEOCACHE.exists() else {}

def geocode(q):
    if q in geocache:
        return geocache[q]
    import urllib.parse, urllib.request, time
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "json", "limit": 1, "countrycodes": "us"})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "lambertville-local-bands/1.0 (personal project)"})
        res = json.load(urllib.request.urlopen(req, timeout=20))
        geocache[q] = [float(res[0]["lat"]), float(res[0]["lon"])] if res else None
    except Exception:
        return None
    time.sleep(1.1)  # Nominatim usage policy: 1 request per second
    return geocache[q]

def nearest_region(pt):
    best = min((b for b in bands if b["basis"] == "based" and TOWNS.get(f"{b['town']}, {b['state']}")),
               key=lambda b: (TOWNS[f"{b['town']}, {b['state']}"][0] - pt[0]) ** 2 + (TOWNS[f"{b['town']}, {b['state']}"][1] - pt[1]) ** 2)
    return best["region"]

for b in bands:
    if not b.get("region") and TOWNS.get(f"{b['town']}, {b['state']}"):
        b["region"] = nearest_region(TOWNS[f"{b['town']}, {b['state']}"])

listed = {}
for b in bands:
    for a in b.get("appearances", []):
        listed.setdefault(venue_key(a["venue"], a["town"]), {}).setdefault(b["name"], 0)
        listed[venue_key(a["venue"], a["town"])][b["name"]] += 1
counts_all = {}
for a in apps.values():
    k = venue_key(a["venue"], a["town"])
    counts_all[k] = counts_all.get(k, 0) + 1

venue_out = []
for k, v in venues.items():
    if v.get("kind") == "open mic":
        continue
    town_pt = TOWNS.get(f"{v['town']}, {v['state']}") or \
        (geocode(f"{v['town']}, {v['state']}") if "--geocode" in sys.argv else geocache.get(f"{v['town']}, {v['state']}"))
    pt = None
    if "--geocode" in sys.argv:
        pt = (v.get("address") and geocode(f"{v['address']}")) or geocode(f"{v['name']}, {v['town']}, {v['state']}")
    else:
        pt = (v.get("address") and geocache.get(v["address"])) or geocache.get(f"{v['name']}, {v['town']}, {v['state']}")
    if pt and town_pt and abs(pt[0] - town_pt[0]) + abs(pt[1] - town_pt[1]) > 0.5:
        pt = None  # geocoder matched a same-named place elsewhere
    if not pt and town_pt:
        h = int.from_bytes(k.encode()[:4].ljust(4, b"_"), "big")
        pt = [town_pt[0] + ((h % 97) - 48) / 9000, town_pt[1] + ((h // 97 % 97) - 48) / 7000]  # spread venues around the town centre
        v["approx"] = True
    if not pt:
        print("VENUE WITHOUT LOCATION:", v["name"], v["town"], v["state"])
        continue
    bl = listed.get(k, {})
    venue_out.append({
        "name": v["name"], "town": v["town"], "state": v["state"], "pt": [round(pt[0], 5), round(pt[1], 5)],
        "approx": v.get("approx", False), "kind": v.get("kind"), "address": v.get("address"),
        "website": v.get("website"), "facebook": v.get("facebook"), "instagram": v.get("instagram"),
        "frequency": v.get("music_frequency"), "status": v.get("calendar_status") or "seen_in_listings",
        "coverage": v.get("coverage"), "source_url": v.get("source_url"), "notes": v.get("notes"),
        "bookings": counts_all.get(k, 0), "region": nearest_region(pt),
        "bands": sorted(bl, key=lambda n: -bl[n]),
    })
GEOCACHE.write_text(json.dumps(geocache, indent=0))
print(f"{len(venue_out)} venues ({sum(v['approx'] for v in venue_out)} placed approximately)")

html = (HERE / "template.html").read_text()
html = html.replace("__BANDS__", json.dumps(bands, ensure_ascii=False, indent=0).replace("</", "<\\/"))
html = html.replace("__REGIONS__", json.dumps(list(dict.fromkeys(REGIONS.values())), ensure_ascii=False))
html = html.replace("__VENUES__", json.dumps(venue_out, ensure_ascii=False).replace("</", "<\\/"))
html = html.replace("__TOWNS__", json.dumps(towns)).replace("__DATE__", "October 2026")
OUT.write_text(html)
print(f"{len(bands)} bands, {len(towns)} towns -> {OUT}")
