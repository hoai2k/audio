# Brief: plain-language venue summaries

Input: `python3 tools/summary_input.py` writes `bands/cache/venue_summary_input.json`. It lists venues that don't have a summary yet: key, name, town, kind, music_frequency, crawl_notes, coverage, acts_sample (up to 25 acts that played there, most frequent first, some with genre in parentheses) and distinct_acts.

For each venue, write one or two short sentences, about 15–35 words in total:
1. **What plays there:** the kinds of acts, taken from acts_sample, kind and crawl_notes. Examples: "Mostly jazz trios and duos." "Local rock and punk bills, plus touring club bands."
2. **What's left out:** what the list includes or excludes, where crawl_notes say so, in plain words. Examples: "Solo singers and DJ nights aren't included." "Only local and regional bands are listed, not the national headliners."

Don't mention how the data was gathered or how complete it is. That means no calendars, feeds, APIs, archives, crawls, coverage dates, blocked sites, row counts, booking counts or numbers of bands. Don't invent facts.
- **Little to go on:** if a venue has no acts and no useful notes, write a neutral one-liner from its kind.
- **Closed venues:** start with "Closed.".

Merge the results into `bands/data/venue_summaries.json`, a JSON object mapping key to summary. Keep the existing keys and add the new ones. Check it parses.
