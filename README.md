# Play by Ear · GameCast

Experimental original tabletop games whose mechanics depend on recorded podcast audio. Separate from Th'die's Cast, which provides utilities for existing games.

## Follow the iOS 18 test feed

**Apple Podcasts subscription URL:**

https://play-by-ear-gamecast-lab.onrender.com/feed.xml

In Apple Podcasts on iOS 18: Library → menu (•••) → Follow a Show by URL. Paste the RSS address.

**Six episodes:** Three Channel Laboratory; How Fast Can Art Change?; The Forked Transmission; The Left Branch; The Right Branch; Link and Timestamp Diagnostics.

The test focuses on independent left/right stereo information, per-chapter images and chapter navigation, two- and three-player asymmetric information, links, transcripts, deliberately chosen run times, and branching between episodes.

The content is original, including generated eSpeak narration. This is a compatibility experiment, **not** yet a completed game. On iOS 18, chapter-image updates at sub-second durations and transcripts from a private RSS feed are unverified / limited.

## Project and publication

- `tools/build_test_feed.py`: reproducible generator for the test audio, chapter JPEGs, Podcasting 2.0 chapter JSON, VTT transcripts, web pages, and RSS XML.
- `.github/workflows/publish.yml`: automatically builds and validates the media; publishes files to the `gh-pages` branch.
- `gh-pages` branch: generated static assets; do not hand-edit.
- The public feed is hosted as a Render static site from `gh-pages`.
- `.github/workflows/verify-feed.yml`: confirms external RSS 200, audio MIME type, and byte-range support (HTTP 206).

The actual public URLs and player behavior should be tested in Apple Podcasts on iOS 18.7.10, especially changing chapter artwork.


## iOS 18.7.10 results (user-tested, 2026-10-12)

- **PASS:** Apple Podcasts recognizes the MP3-embedded ID3 chapter list. Episode 1 shows all nine chapters, selects the requested chapter, and identifies the current chapter while playing. The Now Playing chapter thumbnail corresponds to the current chapter in the supplied screenshot.
- **FAIL:** Description timestamps such as `00:28` are automatically rendered as tappable links but opened the show's raw `feed.xml` in a browser instead of seeking to that time. This occurred for a directly subscribed RSS feed, even though independent embedded chapter navigation works. Root cause inside Apple Podcasts is not proven.
- **MITIGATION:** The feed generator no longer includes misleading automatically linked `MM:SS` chapter lists in descriptions. Navigate via the built-in Now Playing chapter list; the audio's embedded chapter metadata is unchanged. The episode web pages still provide readable timestamp lists for browser use.
- **USER-REPORTED PASS:** In *How Fast Can Art Change?*, every programmed art-change speed appeared to work, including the 0.1-second interval. This is a positive observational result, not yet a frame-by-frame latency/dropped-frame measurement.
- **NOT YET VERIFIED:** Frame-accurate 0.1-second performance, Lock Screen artwork behavior, offline playback, separate left/right listening, and private-feed transcript handling. The screenshots alone do not establish these.

Do not assume iOS 18 description timestamps provide reliable CYOA branching for direct-RSS subscriptions. The new *Link and Timestamp Diagnostics* episode isolates five timestamp formats against the working embedded chapters. If none seek, the restriction is likely direct-RSS/catolog identity rather than timestamp spelling.

The cross-episode show-note links intentionally point to **webpages**, not to in-app Apple Podcasts episodes. Direct-to-episode Apple URLs require catalog IDs assigned by Apple Podcasts Connect. A direct RSS subscription does not provide a documented way to target arbitrary subscribed episodes via native deep links. Apple catalog submission would need to be initiated separately by the creator; it is not performed by this project.

## QR code production rule (2026-10-12)

The first 235 x 235 QR code in a 1400 x 1400 chapter-art image proved too small to scan within Apple Podcasts. The generator now uses a **1260 x 1260** high-contrast QR code centered in the 1400 x 1400 image, with four modules of white quiet-zone border and no typography or decoration inside the code. This occupies 90% of the full image width. Keep future QR chapter artwork similarly dominant, and test both in-app viewing and second-device scanning. The QR points to the project's hosted index; when Apple assigns catalog episode IDs, consider swapping in official Apple Podcasts episode/time share links. If the podcast app caches embedded MP3 art, delete and re-download the episode to inspect updates.

Official Apple Podcasts episode/time links can be acquired on iOS 18 from Now Playing > More > Share > From Start > From [time]. This should be tested for app-opening behavior before using it as a core branching game mechanic.

## Research and design

Core areas: audio-based navigation, audio masking and illusions, channel-specific secrets, independent screen information, timed orchestration, and unusual podcast-player mechanics.
