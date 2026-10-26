"""Pull archived event/calendar pages from the last 12 months for each venue site from the Wayback Machine.

Usage: python3 tools/wayback.py <city> [outdir]
  Reads cache/sweep_<city>.json (written by build.py, nearest venue first) and saves pages under
  outdir (default cache/wayback/<venue-slug>/). Finished venues are skipped on re-runs, so it can be
  stopped and restarted; venues it couldn't reach are retried next time.
Writes outdir/<venue-slug>/<timestamp>_<n>.txt (page text) and outdir/index.json.
"""
import gzip, html, json, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UA = {"User-Agent": "local-bands-research/1.0 (personal project)", "Accept-Encoding": "identity"}
EVENTISH = re.compile(r"event|calendar|music|show|live|entertain|concert|lineup|schedule|whats-?on|tickets|gig|band|perform", re.I)
SKIP = re.compile(r"\.(js|css|png|jpe?g|gif|svg|webp|ico|woff2?|pdf|xml|json|txt)(\?|$)|/_api/|/_partials/|wp-json|wp-content|utm_|/cart|/account|/login", re.I)
AGGREGATORS = re.compile(r"web\.archive\.org|planetprinceton|patch\.com|princetoninfo|inquirer|levittownnow|morningcall|songkick|bandsintown|facebook|instagram|eventbrite|allevents|jambase|patch\.com|tapinto|nj\.com|google\.|visit|county|\.gov|mercerme|lehighvalleylive|eastonpost|newjerseystage|jerseyindie|setlist|showpass|dice\.fm|ticket", re.I)
MAX_DETAIL = 250      # per-show pages per venue
MAX_LISTING = 24      # monthly captures of listing pages per venue
FROM = "202510"       # the last 12 months: Oct 2025 onward


def get(url, timeout=40):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                raw = r.read()
                if raw[:2] == b"\x1f\x8b":  # some captures come back gzip-compressed
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
        except Exception:
            time.sleep(2 + attempt * 3)
    return None


def cdx(params):
    q = urllib.parse.urlencode({**params, "output": "json", "from": FROM, "filter": "statuscode:200"})
    txt = get("https://web.archive.org/cdx/search/cdx?" + q, timeout=90)
    if txt is None:
        raise ConnectionError("Wayback CDX unreachable")
    try:
        rows = json.loads(txt or "[]")
    except json.JSONDecodeError:
        return []
    return rows[1:] if rows else []


def to_text(page):
    # Structured event data (schema.org JSON-LD) carries dates that the visible text often drops
    events = []
    for blob in re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page):
        for name, start in re.findall(r'"name"\s*:\s*"([^"]{2,200})".{0,400}?"startDate"\s*:\s*"([^"]+)"', blob, re.S):
            events.append(f"{start[:16]}  {html.unescape(name)}")
    # Dates in <time datetime> and data-date attributes survive as inline text
    page = re.sub(r'(?is)<time[^>]*datetime="([^"]+)"[^>]*>', r" [\1] ", page)
    page = re.sub(r'(?i)data-(?:date|start|event-date)="([^"]+)"', r'> [\1] <x', page)
    page = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|tr|td|section|article)>", "\n", page)
    page = html.unescape(re.sub(r"<[^>]+>", " ", page))
    lines = [re.sub(r"\s+", " ", l).strip() for l in page.splitlines()]
    body = "\n".join(l for l in lines if l)
    if events:
        body = "EVENTS (from structured data):\n" + "\n".join(dict.fromkeys(events)) + "\n\n" + body
    return body[:40000]


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
    root = Path(__file__).resolve().parent.parent
    venues = json.load(open(root / "cache" / f"sweep_{sys.argv[1]}.json"))
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "cache" / "wayback"
    out.mkdir(parents=True, exist_ok=True)
    index = json.load(open(out / "index.json")) if (out / "index.json").exists() else {}
    for v in venues:
        site = v.get("website")
        src = v.get("source_url") or ""
        if not site and src and not AGGREGATORS.search(src):
            site = src  # the venue's own page was the source
        if not site:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", (v["name"] + "-" + v.get("town", "")).lower()).strip("-")[:60]
        vdir = out / slug
        if (vdir / ".done").exists():
            continue
        caps = None
        for wait in (0, 60, 180, 600):  # ride out Archive outages rather than skipping the venue
            time.sleep(wait)
            try:
                caps = captures_for(site)
                break
            except ConnectionError:
                print(f"{slug}: Wayback unreachable, retrying in a bit", flush=True)
        if caps is None:
            print(f"{slug}: gave up for this run", flush=True)
            continue
        vdir.mkdir(exist_ok=True)
        seen_text = set()

        def fetch(i_cap):
            i, (ts, orig) = i_cap
            page = get(f"https://web.archive.org/web/{ts}id_/{orig}")
            return i, ts, orig, (to_text(page) if page else None)

        files = []
        with ThreadPoolExecutor(2) as pool:
            for i, ts, orig, text in pool.map(fetch, enumerate(caps)):
                if not text or hash(text) in seen_text:
                    continue
                seen_text.add(hash(text))
                f = vdir / f"{ts}_{i}.txt"
                f.write_text(f"SOURCE: https://web.archive.org/web/{ts}/{orig}\nCAPTURED: {ts[:4]}-{ts[4:6]}-{ts[6:8]}\n\n{text}")
                files.append(f.name)
        if files or not caps:
            (vdir / ".done").write_text(str(len(files)))
        index[slug] = {"venue": v["name"], "town": v.get("town"), "state": v.get("state"), "website": site,
                       "captures_found": len(caps), "files": len(files)}
        print(f"{slug}: {len(caps)} captures, {len(files)} unique pages", flush=True)
        (out / "index.json").write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main()
