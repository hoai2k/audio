# Brief: extract lineups from archived venue pages

`tools/wayback.py` saves archived copies of venue event and calendar pages as text, at `bands/cache/wayback/<venue-slug>/<timestamp>_<n>.txt`. Each file starts with `SOURCE:` (the archive URL) and `CAPTURED:` (the capture date). Some also start with an `EVENTS (from structured data)` block, which has reliable dates and event names. `bands/cache/wayback/index.json` maps each slug to its venue name, town and state.

Before handing the work over, run `python3 tools/wayback_digest.py`. It writes one `DIGEST.md` per venue folder: the captures in date order, with repeated lines and site chrome removed. Read the digest, and open individual capture files only when a digest entry is unclear.

Hand this to an agent together with:
- `SLUGS`: the venue folders to read
- `WINDOW`: the dates to keep
- `OUTPUT`: normally `bands/data/census_wayback_<batch>.json`

## Task
For each venue folder, read its `DIGEST.md` and pull out every dated band booking in `WINDOW`, one row per band per date. This needs no web access: read the local files only.
- **Dates:** use the structured-data block, `[YYYY-MM-DD]` markers or dates in the text. If a listing shows month and day but no year, infer the year from the capture date: a listing captured in Oct 2025 showing "Feb 22" means 2026 if it's under "upcoming", or 2025 if it's under "past events". If you can't tell, skip it.
- **Duplicates:** the same show often appears in many captures. Record it once, and use the earliest capture that shows it as `source_url`.
- **Bands only:** skip solo acts, DJs, open mics, trivia, comedy, karaoke and cancelled shows. Split multi-band bills into separate rows, and keep the raw bill text in `billing`.
- **Extra details:** if the page gives a time or price, keep it.

## Output
The same JSON shape as `venue_census.md`, with `"source_type": "archive"` on every row. Put a venue entry in `venues` for each slug: name, town and state from `index.json`, `calendar_status` "partial", and `coverage` = the capture dates you saw. `band_info` is optional.

Reply with rows per venue, and anything odd.
