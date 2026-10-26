# Brief: fill in band details (genre, description, links, photo)

Input: one batch file from `python3 tools/band_info_input.py`, at `bands/cache/band_info_input_<n>.json`. Each entry gives a band's `name`, `home_base` (may be null), `mapped_town`, up to 8 recent local `shows` (date, venue, town), `show_count` and any `known_links`. Every band played in the PA/NJ/DE area around Philadelphia and Lambertville.

## Task
For each band, find its own online presence and record:
- **genre:** a short genre phrase, like "indie rock", "bluegrass", "80s covers", "jazz trio" or "Grateful Dead tribute". Use 1–3 genres separated by " / ". For tribute or cover bands, say whose music or what era.
- **description:** 1–2 sentences in your own words: what they sound like or play, and where they're from if known. Don't paste their bio, and don't describe the research ("found on Bandcamp…").
- **home_base:** the town and state they say they're from, if stated.
- **links:** website, bandcamp, spotify, instagram, facebook, youtube. Only include URLs you actually saw.
- **solo:** `true` if it turns out to be one person performing under their own or a stage name (a solo singer, rapper or DJ) rather than a band. Duos count as bands.
- **image:** a stable direct image URL, either a Bandcamp `f4.bcbits.com` image or the og:image from the band's own site. Never use fbcdn or cdninstagram URLs. null if none.

## Make sure it's the same band
Many band names are shared. Only record a match when something ties it to these shows: a home town in or near PA/NJ/DE/NY, one of the listed venues on the band's own pages, or a listing at one of those venues that describes the band. If you can't confirm it, leave the fields null. A blank genre is better than the wrong band's.

## How to look
1. **Venue listings:** the listed venues' own event pages often describe the act. WebFetch the venue's events page or an event page.
2. **Bandcamp:** Bandcamp's search page doesn't load through WebFetch, so try likely artist addresses directly, e.g. `https://<bandnamewithoutspaces>.bandcamp.com/`, which shows location, tags, bio and image. Bandcamp rate-limits (429): pause and retry rather than hammering it.
3. **WebSearch:** only when 1 and 2 fail, e.g. `"<band name>" band <town>`. Budget: at most ~30 WebSearch calls per batch. Prefer WebFetch.
4. **Social media:** search snippets from public Facebook or Instagram pages can confirm genre and home town. Their image URLs expire, so don't use them.

## Output
Write a JSON array to `bands/data/bandinfo_<n>.json`, one object per input band in the same order. Bands you couldn't confirm still get an entry, with null fields and `"confirmed": false`:
```json
{"name": "...", "confirmed": true, "solo": false, "genre": "...", "description": "...", "home_base": "... or null",
 "links": {"website": null, "bandcamp": null, "spotify": null, "instagram": null, "facebook": null, "youtube": null},
 "image": null, "source": "the URL that confirmed it"}
```
Check that the JSON is valid. Reply with: how many were confirmed, how many have a genre, and any doubtful matches.
