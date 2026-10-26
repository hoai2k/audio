# Brief: bands based in an area

Hand this to a research agent together with:
- `AREA`: the towns or neighbourhoods
- `WINDOW`: the activity window, e.g. 2025–2026
- `OUTPUT`: normally `bands/data/bands_<area>.json`
- `ALREADY`: band names already on file (`python3 tools/list_bands.py --near "<town>"`), so they aren't repeated

## Goal
Find bands that are **based** in `AREA` and active during `WINDOW`: shows played or scheduled, or new releases. This catches home-grown bands that venue calendars miss. Bands only (duos OK), no solo acts. Aim for 15–30, quality over quantity, and never invent anything.

## Sources that worked well
- **Bandcamp location data:** `https://bandcamp.com/discover?location=<geoname id>` and the "from <town>" text on artist pages. Keep only bands with a release in `WINDOW`.
- **Lineups that list hometowns:** festival and porchfest pages often name each act's town.
- **Local press and radio:** TAPinto, Patch, local papers, WXPN / The Key, WDVR, WDIY.
- **Venue calendars:** look for "local night" and "showcase" bills.

## Fields per band
- `name`, `town`, `state`, `neighborhood` (optional, for big cities), `genre`
- `description`: 1–2 sentences, your own words
- `links`: any of website, bandcamp, spotify, instagram, facebook, youtube, tiktok, linktree, reverbnation (only URLs you saw)
- `image`: a stable direct image URL (Bandcamp f4.bcbits.com, or the band's own site og:image), never fbcdn/cdninstagram, otherwise null
- `activity`: a short evidence note with a date
- `evidence_url`

Write a JSON array to `OUTPUT`. Reply with the count, plus caveats on weak entries.
