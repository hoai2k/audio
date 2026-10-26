# Local bands and venues

Static pages that map the bands and live-music venues within about an hour of a town:

- `lambertville/index.html`: Lambertville, NJ (82 km radius)
- `philadelphia/index.html`: Philadelphia, PA (70 km radius)

Each page is one self-contained HTML file. It needs an internet connection for the map tiles, fonts and the Leaflet library. Open it straight from disk, or put it on any static host.

## How it fits together

```
bands/
  data/                 shared research, used by every city
    bands_*.json          bands found by home-base searches
    census_*.json         venue censuses: venues + every dated booking
    venues_*.json         the first venue crawls (older format, kept for their dates)
    towns.json            town and neighbourhood coordinates
    geocache.json         cached OpenStreetMap address lookups
    overrides.json        hand corrections (dropped bands, renamed towns, fixed descriptions)
    venue_summaries.json  one- or two-sentence venue blurbs, keyed "venuename|town"
    bandinfo_*.json       band details looked up later: genre, description, links, photo
  <city>/
    config.json           centre, radius, date window, last-updated date, regions, title, theme
    theme.css             the city's colours, fonts and header styles
    masthead.html         the header illustration (inline SVG)
    index.html            built page (don't edit by hand)
    shows.json, shows.csv every show on that page: date, band, venue, bill-mates, source
  tools/
    build.py              builds a city page from data/ + <city>/config.json
    template.html         page layout and behaviour, shared by all cities
    wayback.py            downloads archived venue calendar pages from the Wayback Machine
    list_venues.py        lists venues or bands already on file for an area
    summary_input.py      lists venues still needing a written summary
    band_info_input.py    lists bands still missing a genre, busiest first
    briefs/               instructions for research agents (see below)
  cache/                  scratch space (git-ignored): Wayback pages, sweep lists
```

**Who's on a page.** A band is listed when either of these holds:

- **Based here:** its home town (from `bands_*.json`) is inside the radius.
- **Plays here often:** within the date window, it has at least two separate bookings (a different venue or month, so a multi-day festival counts once) at venues inside the radius. A band whose listed home base is out of state also has to come back to the same town more than a month apart.

**Solo performers** are listed by the same rules, but only if at least one of their local shows was on a band's bill (opening for one, or sharing the night) or at a festival or concert series (porchfests don't count for solo acts). They get a "Solo artist" badge. Solo acts who only play alone (open mics, solo bar gigs), DJs and school or community groups are left out. Mark solo acts with `"solo": true` on census rows or in band-info files, or list them under `solo_acts` in `data/overrides.json`.

Each band card lists its local shows, so it's clear why the band is there.

## Updating a page

1. **Pick the dates.** In `<city>/config.json`, set `date_from` and `date_to` to the window to show, and `updated` to today. Moving `date_from` forward drops older shows; no data is deleted, they're just filtered out. The page header ("Based on shows from … · last updated …") follows these settings.
2. **Gather new data.** Hand a research agent one of the briefs in `tools/briefs/`, with the area, window and output file filled in. Give each new pass its own file name, e.g. `census_river_2027.json`. The build merges every file and drops duplicates (same band, venue and date), so old and new passes can sit side by side.
   - `venue_census.md`: venues and every dated booking in an area. Pass `ALREADY` from `python3 tools/list_venues.py --town <Town>`.
   - `home_base.md`: bands based in an area. Pass `ALREADY` from `python3 tools/list_venues.py --bands --town <Town>`.
3. **Fill in history from the Wayback Machine** (optional):
   ```bash
   python3 tools/build.py <city>          # refreshes cache/sweep_<city>.json, nearest venue first
   python3 tools/wayback.py <city>        # slow: the Archive rate-limits; safe to stop and re-run
   ```
   Then hand `tools/briefs/wayback_extract.md` to an agent to turn the saved pages into `data/census_wayback_<batch>.json`. To re-sweep a venue later, delete its folder under `cache/wayback/`.
4. **Fill in band details.** Bands found through venue calendars often arrive with only a name and dates. Run `python3 tools/band_info_input.py`, which writes batches of bands missing a genre to `cache/band_info_input_<n>.json`, busiest first. Then hand each batch and `tools/briefs/band_info.md` to an agent; the results go in `data/bandinfo_<n>.json`. Only confirmed matches are used, and they replace crawl placeholders. Bands already covered are skipped on the next run.
5. **Write summaries for new venues.** Run `python3 tools/summary_input.py <city>`, then hand `tools/briefs/venue_summaries.md` to an agent. You can edit `data/venue_summaries.json` by hand at any time.
6. **Build:**
   ```bash
   python3 tools/build.py <city> --geocode   # --geocode looks up any new addresses (1 per second)
   ```
   Check the `MISSING COORDS` lines, if any, and add those towns to `data/towns.json`.
7. **Check it.** Open `<city>/index.html` in a browser. Search a few bands you know, click a few venues, and look for pins in the wrong place. Wrong pins usually mean an address without a town: fix the venue's `address` in its census file, or add a `towns.json` entry.
8. **Fix by hand** with `data/overrides.json`:
   - `drop_bands`: e.g. national touring acts, or a studio project
   - `plays_here_not_based`: home-base entries that are really visiting bands
   - `descriptions`: rewrite a band blurb
   - `town_names`: e.g. "Upper Bucks County" → "Quakertown"
   - `drop_venues`

## Adding a city

1. Copy `philadelphia/` or `lambertville/` to `bands/<newcity>/`.
2. Edit `config.json`:
   - `center` and `radius_km`
   - `home`: the name used in "12 mi from …"
   - `regions`: names and centres. Optional `states` limits a region to one state. `"split": true` marks neighbourhood regions inside `split_town`, for big cities.
   - the title text, and the `fonts` link
3. Restyle `theme.css`. It must define the same CSS variables: `--paper --panel --ink --muted --line --river --river-deep --river-soft --brick --brick-soft --towpath --chip --serif --sans --shadow`. Redraw `masthead.html` too.
4. Run the research briefs for any part of the new radius that `data/` doesn't cover yet, then build.

## Publishing

Pushing to `main` on GitHub runs `.github/workflows/pages.yml`, which publishes the repository to GitHub Pages. The pages are at http://games.hoai.net/audio/bands/. The whole repository is published, so `data/` is public too: never commit private details (see below).

## Notes

- **Privacy:** don't record home addresses, host names, emails or phone numbers. Porch and house shows are filed under the festival or neighbourhood, not the house. DIY venues get no street address and are pinned at their neighbourhood or town, unless they're listed in `public_diy_venues` in `data/overrides.json` (DIY spaces that are public businesses).

- The map uses Esri World Topo tiles (no key needed) and Leaflet 1.9.4 from cdnjs.
- Addresses are geocoded with OpenStreetMap Nominatim. Lookups are cached in `data/geocache.json`, so later builds don't repeat them.
- Images come from Bandcamp or bands' own sites. Facebook and Instagram image links expire, so they're dropped.
