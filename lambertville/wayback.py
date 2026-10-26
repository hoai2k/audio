"""Pull archived event/calendar pages from the last 12 months for each venue site from the Wayback Machine.

Usage: python3 wayback.py venues_all.json outdir
Writes outdir/<venue-slug>/<timestamp>_<n>.txt (page text) and outdir/index.json.
"""
import html, json, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UA = {"User-Agent": "lambertville-local-bands-research/1.0 (personal project)"}
EVENTISH = re.compile(r"event|calendar|music|show|live|entertain|concert|lineup|schedule|whats-?on|tickets|gig|band|perform", re.I)
SKIP = re.compile(r"\.(js|css|png|jpe?g|gif|svg|webp|ico|woff2?|pdf|xml|json|txt)(\?|$)|/_api/|/_partials/|wp-json|wp-content|utm_|/cart|/account|/login", re.I)
MAX_DETAIL = 250      # per-show pages per venue
MAX_LISTING = 24      # monthly captures of listing pages per venue
FROM = "202510"       # the last 12 months: Oct 2025 onward


def get(url, timeout=40):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2 + attempt * 3)
    return None


def cdx(params):
    q = urllib.parse.urlencode({**params, "output": "json", "from": FROM, "filter": "statuscode:200"})
    txt = get("https://web.archive.org/cdx/search/cdx?" + q, timeout=90)
    try:
        rows = json.loads(txt or "[]")
    except json.JSONDecodeError:
        return []
    return rows[1:] if rows else []


def to_text(page):
    page = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|tr|td|section|article)>", "\n", page)
    page = html.unescape(re.sub(r"<[^>]+>", " ", page))
    lines = [re.sub(r"\s+", " ", l).strip() for l in page.splitlines()]
    return "\n".join(l for l in lines if l)[:30000]


def captures_for(site):
    host = urllib.parse.urlparse(site if "://" in site else "https://" + site).netloc.removeprefix("www.")
    if not host:
        return []
    rows = cdx({"url": host + "/*", "fl": "timestamp,original,mimetype", "collapse": "urlkey", "limit": "5000"})
    detail, listing = [], set()
    for ts, orig, mime in rows:
        if "html" not in mime or SKIP.search(orig) or not EVENTISH.search(urllib.parse.urlparse(orig).path):
            continue
        path = urllib.parse.urlparse(orig).path.rstrip("/")
        # A path with a slug after the events segment is one show; otherwise it's a listing page
        if re.search(r"(event|show|concert|calendar)[^/]*/[^/]{6,}", path, re.I):
            detail.append((ts, orig))
        else:
            listing.add(orig.split("?")[0])
    picks = detail[:MAX_DETAIL]
    # Listing pages and the homepage: one capture per month
    for u in list(listing)[:6] + [host + "/"]:
        for ts, orig in cdx({"url": u, "fl": "timestamp,original", "collapse": "timestamp:6"})[:MAX_LISTING]:
            picks.append((ts, orig))
    return picks


def main():
    venues = json.load(open(sys.argv[1]))
    out = Path(sys.argv[2])
    out.mkdir(exist_ok=True)
    index = {}
    for v in venues:
        site = v.get("website")
        if not site:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", (v["name"] + "-" + v.get("town", "")).lower()).strip("-")[:60]
        caps = captures_for(site)
        vdir = out / slug
        vdir.mkdir(exist_ok=True)
        seen_text = set()

        def fetch(i_cap):
            i, (ts, orig) = i_cap
            page = get(f"https://web.archive.org/web/{ts}id_/{orig}")
            return i, ts, orig, (to_text(page) if page else None)

        files = []
        with ThreadPoolExecutor(4) as pool:
            for i, ts, orig, text in pool.map(fetch, enumerate(caps)):
                if not text or hash(text) in seen_text:
                    continue
                seen_text.add(hash(text))
                f = vdir / f"{ts}_{i}.txt"
                f.write_text(f"SOURCE: https://web.archive.org/web/{ts}/{orig}\nCAPTURED: {ts[:4]}-{ts[4:6]}-{ts[6:8]}\n\n{text}")
                files.append(f.name)
        index[slug] = {"venue": v["name"], "town": v.get("town"), "state": v.get("state"), "website": site,
                       "captures_found": len(caps), "files": len(files)}
        print(f"{slug}: {len(caps)} captures, {len(files)} unique pages", flush=True)
        (out / "index.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
