"""Build one city's page from the shared research data.

Usage:
  python3 tools/build.py lambertville              # writes bands/lambertville/index.html (+ shows.json/.csv)
  python3 tools/build.py philadelphia --geocode    # also look up new venue/town locations (OpenStreetMap, 1 req/s)

Inputs (bands/data/):
  bands_*.json      bands found by home-base searches (briefs/home_base.md)
  census_*.json     venue censuses: venues + every dated booking (briefs/venue_census.md, briefs/wayback_extract.md)
  venues_*.json     the first venue crawls (older format, bands with 2+ dates only)
  towns.json        town coordinates;  geocache.json  cached address lookups
  overrides.json    hand corrections;  venue_summaries.json  plain-language venue blurbs
City settings (bands/<city>/config.json): centre, radius, date window, last-updated date, regions, theme.
"""
import csv, glob, json, math, re, sys, time, unicodedata, urllib.parse, urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, CACHE = ROOT / "data", ROOT / "cache"
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
if not ARGS:
    sys.exit(__doc__)
CITY = ROOT / ARGS[0]
CFG = json.load(open(CITY / "config.json"))
GEOCODE = "--geocode" in sys.argv
D_FROM, D_TO = CFG["date_from"], CFG["date_to"]
CENTER, RADIUS = CFG["center"], CFG["radius_km"]
SPLIT = CFG.get("split_town")
CACHE.mkdir(exist_ok=True)

# ---- names and keys ----
fold = lambda t: unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()  # Café -> cafe
band_key = lambda name: re.sub(r"[^a-z0-9]", "", fold(name).replace("&", "and").removeprefix("the "))
venue_key = lambda name, town: re.sub(r"[^a-z0-9]", "", fold(re.sub(r"\s*\(.*?\)", "", name)).replace("&", "and").removeprefix("the ")) + "|" + fold(town)

OV = json.load(open(DATA / "overrides.json"))
DROP = {band_key(n) for n in OV.get("drop_bands", {})}
PLAYS_NOT_BASED = {band_key(n): hb for n, hb in OV.get("plays_here_not_based", {}).items()}
DESC_FIX = {band_key(n): d for n, d in OV.get("descriptions", {}).items()}
DROP_VENUES = {fold(v) for v in OV.get("drop_venues", [])}

def clean_town(t):
    t = re.sub(r"\s*\(.*?\)", "", t or "").split(" / ")[0].strip()
    t = re.sub(r"\s+area$", "", t)
    return OV.get("town_names", {}).get(t, t)

def km(a, b):
    r = math.pi / 180
    h = math.sin((b[0] - a[0]) * r / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin((b[1] - a[1]) * r / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

# ---- places ----
TOWNS = json.load(open(DATA / "towns.json"))
GEOCACHE = DATA / "geocache.json"
geocache = json.load(open(GEOCACHE)) if GEOCACHE.exists() else {}

def geocode(q):
    if q in geocache or not GEOCODE:
        return geocache.get(q)
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "json", "limit": 1, "countrycodes": "us"})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "local-bands-map/1.0 (personal project)"})
        res = json.load(urllib.request.urlopen(req, timeout=20))
        geocache[q] = [float(res[0]["lat"]), float(res[0]["lon"])] if res else None
    except Exception:
        return None
    time.sleep(1.1)  # Nominatim usage policy: 1 request per second
    return geocache[q]

def clean_neighborhood(n):
    # "Spruce Hill / Cedar Park", "Northern Liberties (outside this area)" -> one known name
    for part in re.sub(r"\s*\(.*?\)", "", n or "").split("/"):
        part = OV.get("neighborhood_names", {}).get(part.strip(), part.strip())
        if part:
            return part
    return None

def town_pt(town, state, neighborhood=None):
    neighborhood = clean_neighborhood(neighborhood)
    if neighborhood and TOWNS.get(f"{neighborhood}, {town}, {state}"):
        return TOWNS[f"{neighborhood}, {town}, {state}"]
    return TOWNS.get(f"{town}, {state}") or geocode(f"{town}, {state}")

def region_of(pt, town, state):
    inside = bool(SPLIT) and town == SPLIT
    cands = [r for r in CFG["regions"] if r.get("split", False) == inside and (not r.get("states") or state in r["states"])]
    cands = cands or CFG["regions"]
    return min(cands, key=lambda r: (r["center"][0] - pt[0]) ** 2 + ((r["center"][1] - pt[1]) * 0.76) ** 2)["name"]

# ---- load the shared pool ----
based_all, seen = [], {}
for f in sorted(glob.glob(str(DATA / "bands_*.json"))):
    for b in json.load(open(f)):
        key = band_key(b["name"])
        if key in seen or key in DROP:
            continue
        b["town"], b["state"] = clean_town(b["town"]), (b.get("state") or "").strip().upper()[:2]
        b["links"] = {k: v for k, v in (b.get("links") or {}).items() if v}
        if re.search(r"fbcdn|cdninstagram", b.get("image") or ""):
            b["image"] = None
        b["basis"] = "based"
        if key in PLAYS_NOT_BASED:
            b["basis"], b["home_base"] = "plays_here", PLAYS_NOT_BASED[key]
        seen[key] = b
        based_all.append(b)

SHOW_FIELDS = ("band", "venue", "town", "state", "date", "source_url", "source_type")

def norm_app(a, band_name):
    row = {"band": band_name.strip(), "venue": a["venue"].strip(), "town": clean_town(a.get("town")),
           "state": (a.get("state") or "").strip().upper()[:2], "date": a.get("date"),
           "source_url": a.get("source_url"), "source_type": a.get("source_type")}
    # Keep whatever else the crawl recorded (time, billing text, price, presenter...)
    row["extra"] = {k: v for k, v in a.items() if k not in SHOW_FIELDS and k != "name" and v not in (None, "", [])}
    return row

apps, info, venues = {}, {}, {}

def add_app(a):
    k = (band_key(a["band"]), venue_key(a["venue"], a["town"]), a["date"])
    if a["date"] and k not in apps:
        apps[k] = a

def add_info(i):
    cur = info.setdefault(band_key(i["name"]), {})
    for f, v in i.items():
        if v and not cur.get(f):
            cur[f] = v

def add_venue(v):
    k = venue_key(v["name"], clean_town(v.get("town")))
    cur = venues.setdefault(k, {"name": v["name"], "town": clean_town(v.get("town")), "state": (v.get("state") or "").upper()[:2]})
    for f, val in v.items():
        if val and not cur.get(f):
            cur[f] = val

for f in sorted(glob.glob(str(DATA / "venues_*.json"))):  # first crawls
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
for f in sorted(glob.glob(str(DATA / "census_*.json"))):  # venue censuses
    rep = json.load(open(f))
    for v in rep.get("venues", []):
        add_venue(v)
    for a in rep.get("appearances", []):
        add_app(norm_app(a, a["band"]))
    for i in rep.get("band_info", []):
        add_info(i)
for a in apps.values():  # venues seen only in booking rows
    add_venue({"name": a["venue"], "town": a["town"], "state": a["state"], "calendar_status": "seen_in_listings"})

# ---- venue locations (shared across cities) ----
PUBLIC_DIY = {fold(n) for n in OV.get("public_diy_venues", [])}
for k, v in venues.items():
    tp = town_pt(v["town"], v["state"], v.get("neighborhood"))
    if (v.get("kind") == "DIY" or "house show" in fold(v["name"])) and fold(v["name"]) not in PUBLIC_DIY:
        # DIY spaces are often someone's home: no street address, pin at the neighbourhood or town only
        v["address"] = None
        v["private"] = True
    queries = []
    if v.get("address"):
        addr = v["address"]
        queries.append(addr if fold(v["town"]) in fold(addr) else f"{addr}, {v['town']}, {v['state']}")
    queries.append(f"{v['name']}, {v['town']}, {v['state']}")
    pt = None
    for q in ([] if v.get("private") else queries):
        hit = geocode(q)
        if hit and (not tp or abs(hit[0] - tp[0]) + abs(hit[1] - tp[1]) <= 0.25):  # reject same-named places elsewhere
            pt = hit
            break
    if not pt and tp:
        h = int.from_bytes(k.encode()[:4].ljust(4, b"_"), "big")
        pt = [tp[0] + ((h % 97) - 48) / 30000, tp[1] + ((h // 97 % 97) - 48) / 24000]  # a little around the town centre
        v["approx"] = True
    v["pt"] = pt
GEOCACHE.write_text(json.dumps(geocache, indent=0))

# ---- this city: venues in range, bookings in the date window ----
def in_range(pt):
    return bool(pt) and km(CENTER, pt) <= RADIUS

local_venues = {k for k, v in venues.items() if in_range(v["pt"]) and fold(v["name"]) not in DROP_VENUES}
local = [a for a in apps.values() if D_FROM <= (a["date"] or "") <= D_TO and venue_key(a["venue"], a["town"]) in local_venues]
by_band = {}
for a in local:
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

PLACEHOLDER_DESC = re.compile(r"^(band|act|group) (on|booked at|seen at|that played|listed at|with \w+ \w* ?dates?)\b|\bbills? at\b|\bappearances? (at|in)\b|"
                              r"^plays? (at|these venues)|\bcensus\b|\bdated (shows|dates|appearances)\b|\bcrawl|\blistings?\b|\bcalendar\b|\bHVV\b", re.I)
OUT_OF_STATE = re.compile(r"\b(NY|CA|GA|MA|MD|CT|VA|TN|TX|IL|OH|FL)\b|New York|Brooklyn|Nashville|Boston|Atlanta|Los Angeles")
IN_STATE = re.compile(r"\b(PA|NJ|DE)\b|Pennsylvania|New Jersey|Delaware")

bands, chosen = [], {}
for b in based_all:  # home-base bands whose town is in range
    pt = town_pt(b["town"], b["state"], b.get("neighborhood"))
    if not in_range(pt):
        continue
    b = dict(b, pt=pt, appearances=sorted(by_band.get(band_key(b["name"]), []), key=lambda a: a["date"], reverse=True))
    b["plays_here"] = bool(b["appearances"])
    if SPLIT and b["town"] == SPLIT and not TOWNS.get(f"{clean_neighborhood(b.get('neighborhood'))}, {SPLIT}, {b['state']}"):
        # No neighbourhood on file: place a city band where it plays most in the city
        in_city = [venues[venue_key(a["venue"], a["town"])]["pt"] for a in b["appearances"] if a["town"] == SPLIT]
        if in_city:
            b["pt"] = max(in_city, key=in_city.count)
    chosen[band_key(b["name"])] = b
    bands.append(b)

for key, rows in by_band.items():  # bands that play here often, wherever they're from
    if key in DROP or key in chosen or separate_bookings(rows) < 2:
        continue
    i = info.get(key, {})
    hb = i.get("home_base") or ""
    touring = bool(OUT_OF_STATE.search(hb) and not IN_STATE.search(hb))
    if touring and not returns_to_town(rows):  # touring acts count only if they come back
        continue
    rows.sort(key=lambda a: a["date"], reverse=True)
    vc = {}
    for a in rows:
        k = venue_key(a["venue"], a["town"])
        vc[k] = vc.get(k, 0) + 1
    top = venues[max(vc, key=vc.get)]  # mapped where they play most
    names = {}
    for a in rows:
        names[a["band"]] = names.get(a["band"], 0) + 1
    genre = i.get("genre") or ""
    desc = i.get("description") or ""
    if PLACEHOLDER_DESC.search(desc):  # crawl stubs like "Band on 3 Philadelphia bills at X"
        desc = ""
    b = {"name": i.get("name") or max(names, key=names.get), "town": top["town"], "state": top["state"], "pt": top["pt"],
         "genre": "" if genre.lower() in ("unknown", "n/a") else genre, "home_base": i.get("home_base"),
         "description": desc, "links": {k: v for k, v in (i.get("links") or {}).items() if v},
         "image": None if re.search(r"fbcdn|cdninstagram", i.get("image") or "") else i.get("image"),
         "basis": "plays_here", "plays_here": True, "appearances": rows, **({"touring": True} if touring else {})}
    chosen[key] = b
    bands.append(b)

# ---- specific genres: "Dream pop / indie rock" -> ["Dream Pop", "Indie Rock"] ----
KEEP_BAND = {"big", "jam", "string", "brass", "party", "cover", "wedding", "garage", "tribute", "marching", "show"}
NOT_GENRES = {"horns", "harmonies", "harmony", "vocal", "vocals", "originals", "duo", "trio", "quartet", "local", "regional", "unknown"}
GENRE_ALIASES = {"cover": "covers", "party cover": "party covers", "alt-rock": "alternative rock", "alt rock": "alternative rock",
                 "alternative": "alternative rock", "hip hop": "hip-hop", "psych": "psychedelic", "psych rock": "psychedelic rock",
                 "singer songwriter": "singer-songwriter", "rock n roll": "rock and roll", "rock-n-roll": "rock and roll",
                 "folk rock": "folk-rock", "alt country": "alt-country", "pop-punk": "pop punk", "post punk": "post-punk",
                 "cover band": "covers", "cover bands": "covers", "party band": "party", "tribute band": "tribute"}
SMALL = {"and", "of", "n", "the"}

def split_genres(g):
    g = re.sub(r"\(.*?\)", "", g or "")
    g = re.sub(r"(?i)\brock\s*(&|and|'?n'?)\s*roll\b", "rock-n-roll", g)
    g = re.sub(r"(?i)singer\s*[/-]\s*songwriter", "singer-songwriter", g)
    g = re.sub(r"(?i)\br\s*&\s*b\b", "rnb", g)
    out = []
    for p in re.split(r"\s*(?:/|,|;|\+|\||&|\band\b|\bwith\b|\bplus\b)\s*", g):
        p = re.sub(r"\s+", " ", p.strip(" .-")).lower().replace("rnb", "r&b")
        words = p.split()
        if len(words) > 1 and words[-1] in ("band", "bands") and words[-2] not in KEEP_BAND:
            p = " ".join(words[:-1])
        p = re.sub(r"\b(music|group|act|outfit|project|ensemble)\b", "", p).strip(" -")
        p = GENRE_ALIASES.get(p, p)
        if 2 < len(p) <= 28 and p not in NOT_GENRES and p not in out:
            out.append(p)
    return [" ".join(w if w in SMALL and i else w.upper() if w in ("r&b", "edm", "ska-punk") else w[:1].upper() + w[1:]
                     for i, w in enumerate(t.split())).replace("R&b", "R&B") for t in out]

# ---- labels, regions, places ----
y0, y1 = D_FROM[:4], D_TO[:4]
years = y0 if y0 == y1 else f"{y0}–{y1[2:]}"
places = {}
for b in bands:
    if band_key(b["name"]) in DESC_FIX:
        b["description"] = DESC_FIX[band_key(b["name"])]
    b["genres"] = split_genres(b.get("genre"))
    b["region"] = region_of(b["pt"], b["town"], b["state"])
    if SPLIT and b["town"] == SPLIT:  # a big city is mapped by neighbourhood area
        b["place"] = b["region"]
        places[b["place"]] = next(r["center"] for r in CFG["regions"] if r["name"] == b["region"])
    else:
        b["place"] = f"{b['town']}, {b['state']}"
        places[b["place"]] = town_pt(b["town"], b["state"]) or b["pt"]
    apps_b = b.get("appearances") or []
    if apps_b:
        vc = {}
        for a in apps_b:
            vc[a["venue"]] = vc.get(a["venue"], 0) + 1
        b["venue_summary"] = ", ".join(f"{v} ×{c}" if c > 1 else v for v, c in sorted(vc.items(), key=lambda x: -x[1]))
        if b["basis"] == "plays_here":
            b["activity"] = f"{len(apps_b)} area show{'s' if len(apps_b) > 1 else ''} in {years}"
            b["evidence_url"] = apps_b[0].get("source_url")
            if not b["description"]:
                b["description"] = f"Regular on the local circuit, most often at {max(vc, key=vc.get)}."
    b.pop("pt", None)

listed, counts_all = {}, {}
for b in bands:
    for a in b.get("appearances", []):
        k = venue_key(a["venue"], a["town"])
        listed.setdefault(k, {}).setdefault(b["name"], 0)
        listed[k][b["name"]] += 1
for a in local:
    k = venue_key(a["venue"], a["town"])
    counts_all[k] = counts_all.get(k, 0) + 1

SUMMARIES = json.load(open(DATA / "venue_summaries.json")) if (DATA / "venue_summaries.json").exists() else {}
band_genre = {b["name"]: b.get("genre") or "" for b in bands}
GENRE_WORDS = [("jazz", "jazz"), ("blues", "blues"), ("tribute", "tribute"), ("cover", "cover"), ("punk", "punk"), ("metal", "metal"),
               ("folk", "folk"), ("americana", "Americana"), ("bluegrass", "bluegrass"), ("country", "country"), ("funk", "funk"),
               ("soul", "soul"), ("jam", "jam"), ("indie", "indie"), ("rock", "rock"), ("latin", "Latin"), ("reggae", "reggae")]

def genre_summary(names):
    # Stand-in until venue_summaries.json has a written blurb for this venue
    tally = {}
    for n in names:
        g = band_genre.get(n, "").lower()
        for word, label in GENRE_WORDS:
            if word in g:
                tally[label] = tally.get(label, 0) + 1
                break
    top = [g for g, c in sorted(tally.items(), key=lambda x: -x[1]) if c >= max(2, len(names) // 10)][:3]
    if not top:
        return ""
    return "Mostly " + (top[0] if len(top) == 1 else ", ".join(top[:-1]) + " and " + top[-1]) + " bands."

venue_out = []
for k in local_venues:
    v = venues[k]
    if v.get("kind") in ("open mic", "promoter"):
        continue
    bl = listed.get(k, {})
    venue_out.append({
        "name": v["name"], "town": v["town"], "state": v["state"], "pt": [round(v["pt"][0], 5), round(v["pt"][1], 5)],
        "approx": v.get("approx", False), "kind": v.get("kind"), "address": v.get("address"),
        "website": v.get("website"), "facebook": v.get("facebook"), "instagram": v.get("instagram"),
        "frequency": v.get("music_frequency"), "status": v.get("calendar_status") or "seen_in_listings",
        "coverage": v.get("coverage"), "source_url": v.get("source_url"), "notes": v.get("notes"),
        "bookings": counts_all.get(k, 0), "region": region_of(v["pt"], v["town"], v["state"]),
        "bands": sorted(bl, key=lambda n: -bl[n]), "summary": SUMMARIES.get(k) or genre_summary(list(bl)), "key": k,
    })
venue_out.sort(key=lambda v: km(CENTER, v["pt"]))
# Wayback sweep input for this city, nearest venue first
(CACHE / f"sweep_{CITY.name}.json").write_text(json.dumps(venue_out, indent=0))

# ---- show records for this city (window + range), for later use ----
bill = {}
for a in local:
    bill.setdefault((venue_key(a["venue"], a["town"]), a["date"]), []).append(a["band"])
on_page = {band_key(b["name"]): b["basis"] for b in bands}
shows = []
for a in sorted(local, key=lambda a: (a["date"], a["venue"], a["band"])):
    vk, bk = venue_key(a["venue"], a["town"]), band_key(a["band"])
    shows.append({"date": a["date"], "band": a["band"], "venue": a["venue"], "town": a["town"], "state": a["state"],
                  "same_bill": sorted(set(bill[(vk, a["date"])]) - {a["band"]}),
                  "source_url": a["source_url"], "source_type": a["source_type"],
                  "on_page": on_page.get(bk),  # "based", "plays_here", or None if the band didn't qualify
                  "band_key": bk, "venue_key": vk, **({"extra": a["extra"]} if a.get("extra") else {})})
(CITY / "shows.json").write_text(json.dumps(shows, ensure_ascii=False, indent=1))
with open(CITY / "shows.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["date", "band", "venue", "town", "state", "same_bill", "on_page", "source_type", "source_url"])
    for r in shows:
        w.writerow([r["date"], r["band"], r["venue"], r["town"], r["state"], "; ".join(r["same_bill"]),
                    r["on_page"] or "", r["source_type"] or "", r["source_url"] or ""])

# ---- page ----
updated = date.fromisoformat(CFG["updated"])
dated = [r["date"][:4] for r in shows if re.match(r"\d{4}-", r["date"] or "")]
s0, s1 = (min(dated), max(dated)) if dated else (y0, y1)
period = f"Based on shows from {s0 if s0 == s1 else f'{s0}–{s1}'} · last updated {updated.month}/{updated.day}/{updated.strftime('%y')}"
used_regions = [r["name"] for r in CFG["regions"]]
missing = sorted({b["place"] for b in bands if not places.get(b["place"])})
if missing:
    print("MISSING COORDS:", missing)

def js(x):
    return json.dumps(x, ensure_ascii=False).replace("</", "<\\/")

subs = {
    "__PAGE_TITLE__": f"{CFG['title']} {CFG['title_em']}", "__TITLE__": CFG["title"], "__TITLE_EM__": CFG["title_em"],
    "__PERIOD__": period, "__FONTS__": CFG["fonts"], "__HOME__": CFG["home"],
    "__THEME_CSS__": (CITY / CFG["theme"]).read_text(), "__MASTHEAD__": (CITY / CFG["masthead"]).read_text(),
    "__CENTER__": js(CENTER), "__RADIUS_M__": str(int(RADIUS * 1000)), "__YEARS__": years,
    "__DATE__": updated.strftime("%B %Y"),
    "__BANDS__": js(bands), "__VENUES__": js(venue_out), "__TOWNS__": js({p: c for p, c in places.items() if c}),
    "__REGIONS__": js(used_regions),
}
page = (ROOT / "tools" / "template.html").read_text()
for k, v in subs.items():
    page = page.replace(k, v)
(CITY / "index.html").write_text(page)
print(f"{CITY.name}: {len(bands)} bands ({sum(b['basis'] == 'based' for b in bands)} based here), {len(venue_out)} venues, "
      f"{len(shows)} shows {D_FROM}..{D_TO} -> {CITY / 'index.html'}")
