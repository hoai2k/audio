# Brief: add back solo performers a crawl skipped

Older venue crawls skipped solo acts. The build now lists a solo performer if one of their local shows was on a band's bill (opening for one, or sharing the night) or at a festival or concert series. Porchfests don't count. This brief re-reads a crawl's saved raw data and adds those solo acts back.

The agent gets:
- `RAW`: the raw-data folders and files from the crawl: venue feeds, iCal files, saved pages, schedule PDFs or text.
- `CENSUS`: the census file(s) that crawl produced, in `bands/data/`.
- `OUTPUT`: `bands/data/census_solo_<area>.json`.

## Task
1. For each venue in the census, find its listings in the raw data. Every act on every date is a candidate.
2. Skip acts the census already has for that venue and date, since those are the bands.
3. From the rest, keep **solo performers** only: one person under their own name or a stage name, such as singer-songwriters, solo instrumentalists, or a rapper or producer performing live. Skip DJs, open mics, jams, karaoke, comedy, trivia, drag, kids' and school acts, tribute nights with no performer named, and cancelled shows. If you can't tell whether an act is one person or a band, skip it.
4. Keep a solo act's row when, in the raw data, the same date at the same venue also lists a band (from the census or the raw data), or when the venue is a festival or concert series. Skip porchfests entirely.
5. Use the **exact venue name and town spelling from the census file**, so the rows join up with the band bills. Reuse the census's source URL for that listing, or the raw file's URL.

## Output
The census JSON shape (see `venue_census.md`), with an empty `venues` list unless a venue is new:
```json
{"venues": [],
 "appearances": [{"band": "Performer Name", "venue": "exact census venue name", "town": "...", "state": "..",
                  "date": "YYYY-MM-DD", "solo": true, "source_url": "...", "source_type": "venue_calendar | archive | aggregator",
                  "billing": "optional raw bill text"}],
 "band_info": [{"name": "...", "genre": "...", "description": "...", "home_base": null, "links": {}, "image": null, "solo": true}],
 "notes": "which raw sources you read, which you couldn't use, and judgement calls"}
```
`band_info` is optional: include it only where the listing itself describes the act. Read local files only; no web access is needed. Make sure the JSON is valid. Reply with rows per venue, the number of distinct solo performers, and caveats.
