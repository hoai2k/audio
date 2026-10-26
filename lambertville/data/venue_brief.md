# Venue census brief (shared by all area agents)

Goal: build a thorough census of LIVE-MUSIC VENUES in your area and who played them in Jan 2025 – Dec 2026. It feeds a map page of local bands near Lambertville, NJ (today is 2026-10-26). The user wants to see how thoroughly we capture venues, so record every venue you find, including ones whose lineups you couldn't get, and say why.

## What counts as a venue
Anywhere that hosts live bands with some regularity: bars, pubs, restaurants with music nights, breweries, wineries and distilleries, coffee houses, clubs, theaters and arts centers that book regional acts, DIY/house-show spaces with public listings, VFWs/legion halls/firehouses with band nights, parks with recurring concert series, and recurring festivals (porchfests, town days, summer series). Skip venues that only book national arena tours, and karaoke/DJ/open-mic-only spots (note open-mic-only places as kind "open mic" if you find them but don't crawl them).

## How to find venues and lineups
- WebSearch for "live music" + town; "[town] brewery live music"; local event guides (TAPinto, Patch, town Facebook groups surfaced in search, newspapers, tourism sites, Jersey Indie, NJ Stage, Lehigh Valley Live, The Key, etc.).
- Calendars: the venue's own site (events page, iCal/JSON feeds, Squarespace `?format=json`, Wix event pages, Tockify/Timely/Google Calendar embeds), Wayback Machine snapshots (web.archive.org) for past months.
- Social media and event aggregators: you can't log in, but search engines index public pages. Use WebSearch with site: filters, e.g. `site:facebook.com/events "[venue]"`, `site:instagram.com "[venue]" live music`, and aggregators (allevents.in, eventbrite.com, songkick.com, jambase.com, bandsintown.com, do317-style city guides). WebFetch on Facebook/Instagram usually fails; take dates/acts from search-result snippets when that's all there is, and mark those appearances `"source_type": "social_snippet"`.
- Budget: the web-search limit is shared with 5 other agents running now. Use at most ~35 WebSearch calls; prefer WebFetch on calendars and feeds.

## Already crawled earlier (re-use is fine; focus on NEW venues, and only revisit these to fill obvious gaps)
Archer Music Hall (Allentown); Artie's Bar & Grill (Frenchtown); ArtsQuest/SteelStacks & Musikfest (Bethlehem); Bethlehem Brew Works; Birdhouse Center for the Arts (Lambertville); Broken Goblet Brewing (Bensalem); Doylestown Arts Festival; Flemington DIY; Free Will Brewing (Perkasie); Godfrey Daniels (Bethlehem); Havana (New Hope); Hopewell Porchfest; Hopewell Valley Vineyards (Pennington); John & Peter's (New Hope); Live at the Falls (Easton); Mercer County Park concerts; New Hope Winery; Peddler's Village (Lahaska); Princeton Porchfest; Princeton Public Library; Princeton Shopping Center concerts; Puck Live (Doylestown); Randy Now's Man Cave (Hightstown); Sellersville Theater 1894; Small World Coffee (Princeton); Triumph Brewing New Hope (closed Mar 2026) and Princeton; Vault Brewing (Yardley); Weyerbacher / Porters' Pub / Rivals / The Coop / Easton Public Market (Easton); Woolsey Park concerts (Hopewell Twp).

## Rules for appearances
- Bands only (duos OK); skip solo artists, DJs, open-mic nights, school/community ensembles.
- Record every dated band booking you find (one row per band per date), even single appearances: the page decides who's "local" from the totals across all venues.
- Only real data. Never invent dates, venues or acts.

## Output
Write ONE JSON object with the Write tool (or a Python script) to the path given in your area brief:
```json
{
  "venues": [{
    "name": "...", "town": "...", "state": "NJ|PA",
    "address": "street address if known, else null",
    "kind": "bar | restaurant | brewery | winery | coffeehouse | club | theater | arts center | DIY | park series | festival | other | open mic",
    "website": "url or null", "facebook": "url or null", "instagram": "url or null",
    "music_frequency": "nightly | weekly | several per month | monthly | occasional | annual | unknown",
    "calendar_status": "crawled | partial | social_only | no_online_calendar | blocked | closed",
    "coverage": "what date range you actually saw, e.g. 'Jan 2025–Nov 2026 site calendar' or 'none'",
    "source_url": "where you confirmed the venue", "notes": "short"
  }],
  "appearances": [{"band": "...", "venue": "exact venue name as above", "town": "...", "state": "..", "date": "YYYY-MM-DD", "source_url": "...", "source_type": "venue_calendar | aggregator | social_snippet | press | archive"}],
  "band_info": [{
    "name": "...", "home_base": "stated home town or null", "genre": "...",
    "description": "1–2 sentences, your own words (no research notes)",
    "links": {"website": null, "bandcamp": null, "instagram": null, "facebook": null, "spotify": null, "youtube": null},
    "image": "stable direct image URL (Bandcamp f4.bcbits.com or the band's own site og:image; never fbcdn/cdninstagram) or null"
  }],
  "notes": "caveats, what you couldn't reach"
}
```
`band_info` is only needed for bands with 2+ appearances in your data; keep it light (no extra searching just for images).

Make sure the JSON is valid. Don't touch other files. Reply with: number of venues by calendar_status, number of appearances, top repeat bands, and caveats.
