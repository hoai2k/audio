# Brief: venue census for one area

Hand this to a research agent together with an **area brief** that gives:
- `AREA`: the towns or neighbourhoods to cover, plus any venue leads
- `WINDOW`: the date range to record (e.g. `2025-01-01` to `2026-12-31`)
- `OUTPUT`: where to write the JSON (normally `bands/data/census_<area>.json`)
- `ALREADY`: venues already crawled in this area (run `python3 tools/list_venues.py --near "<town>"` to get them); re-record those only to fill gaps or to add single dates.

## Goal
Make a thorough list of the **live-music venues** in the area, and record who played them during `WINDOW`. The page shows venues as well as bands, so list every venue you find, including ones whose lineups you couldn't get, and say why.

## What counts as a venue
Anywhere that hosts live bands with some regularity:
- bars, pubs, and restaurants with music nights
- breweries, wineries and distilleries
- coffee houses and clubs
- theaters and arts centers that book regional acts
- DIY or house-show spaces with public listings
- VFW and legion halls, and firehouses with band nights
- parks with recurring concert series
- recurring festivals (porchfests, town days, summer series)

Skip venues that only book national arena tours. Note karaoke, DJ and open-mic-only spots as kind `"open mic"`, but don't crawl them. A promoter or collective with no room of its own is kind `"promoter"`: file its shows under the venue where each one happened, and tag the rows with `"presenter"`.

## How to find venues and lineups
- **WebSearch:**
  - "live music" + town
  - "[town] brewery live music"
  - local event guides: TAPinto, Patch, newspapers, tourism and county calendars, Jersey Indie, NJ Stage, The Key (WXPN), Lehigh Valley Live, etc.
- **Venue calendars:**
  - the venue's own site (events pages, iCal/JSON feeds, Squarespace `?format=json`, Wix event pages, Tockify/Timely/Google Calendar embeds)
  - ticketing pages (Eventbrite, DICE, Etix, TicketWeb, See Tickets, Showpass)
- **Archived calendars:** the Wayback Machine.
  - The CDX API lists captures: `https://web.archive.org/cdx/search/cdx?url=example.com/*&from=2025&output=json&collapse=urlkey`. Fetch one with `https://web.archive.org/web/<timestamp>id_/<url>`.
  - It rate-limits and sometimes drops out, so go gently and retry after a pause.
  - `tools/wayback.py` does this in bulk for every venue with a website, so focus on what it can't reach.
- **Social media and aggregators:** you can't log in, but search engines index public pages. Use WebSearch with site filters, e.g. `site:facebook.com/events "[venue]"` and `site:instagram.com "[venue]" live music`, plus aggregators (allevents.in, eventbrite.com, songkick.com, jambase.com, bandsintown.com). WebFetch on Facebook and Instagram usually fails, so take dates and acts from the search snippets, and mark those rows `"source_type": "social_snippet"`.
- **Budget:** keep WebSearch to the number the area brief gives (default ~35). Prefer WebFetch on calendars and feeds.

## Rules for appearances
- **Bands, plus solo performers on bills:** record bands (duos count as bands). Also record solo performers, marked `"solo": true` on their rows, when they share a bill with a band (opening for one, or on the same night) or play a festival or concert series. Record solo porchfest sets too (with the flag); the build decides. Skip solo acts who only play alone (open mics, solo bar gigs), and skip DJs, open-mic nights, and school or community ensembles.
- **Every booking counts:** record each dated band booking you find, one row per band per date, singles included. The build decides who's "local" from the totals across all venues. Treat every band the same.
- **Bill-mates:** record the other bands on the bill too, so each band gets its own row.
- **Only real data:** never invent dates, venues or acts.
- **No private details:** don't record home addresses (porch and house shows, DIY spaces in someone's home), host names, emails or phone numbers. For a porchfest, record the festival as the venue and leave out the porches.

## Output
Write ONE JSON object to `OUTPUT`, with a Python script if it's large:
```json
{
  "venues": [{
    "name": "...", "town": "...", "state": "NJ|PA|DE",
    "address": "street address WITH town and state if known, else null",
    "kind": "bar | restaurant | brewery | winery | coffeehouse | club | theater | arts center | DIY | park series | festival | promoter | other | open mic",
    "website": "url or null", "facebook": "url or null", "instagram": "url or null",
    "music_frequency": "nightly | weekly | several per month | monthly | occasional | annual | unknown",
    "calendar_status": "crawled | partial | social_only | no_online_calendar | blocked | closed",
    "coverage": "what date range you actually saw",
    "source_url": "where you confirmed the venue", "notes": "short: what kinds of acts, and what you left out"
  }],
  "appearances": [{"band": "...", "venue": "exact venue name as above", "town": "...", "state": "..", "date": "YYYY-MM-DD",
                   "source_url": "...", "source_type": "venue_calendar | aggregator | social_snippet | press | archive",
                   "time": "optional", "price": "optional", "billing": "optional raw bill text", "presenter": "optional",
                   "solo": "true for a solo performer, else omit"}],
  "band_info": [{
    "name": "...", "home_base": "stated home town or null", "genre": "...",
    "description": "1–2 sentences in your own words (no research notes)",
    "links": {"website": null, "bandcamp": null, "instagram": null, "facebook": null, "spotify": null, "youtube": null},
    "image": "stable direct image URL (Bandcamp f4.bcbits.com or the band's own site og:image; never fbcdn/cdninstagram) or null"
  }],
  "notes": "caveats, and what you couldn't reach"
}
```
`band_info` is only needed for bands with 2+ appearances in your data. Keep it light: don't do extra searching just for images.

Make sure the JSON is valid, and don't touch other files. Reply with:
- the number of venues by calendar_status
- the number of appearances
- the top repeat bands
- caveats
