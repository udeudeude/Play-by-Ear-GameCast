# Play by Ear · GameCast

Experimental original tabletop games whose mechanics depend on recorded podcast audio. Separate from Th'die's Cast, which provides utilities for existing games.

## Follow the iOS 18 test feed

**Apple Podcasts subscription URL:**

https://play-by-ear-gamecast-lab.onrender.com/feed.xml

In Apple Podcasts on iOS 18: Library → menu (•••) → Follow a Show by URL. Paste the RSS address.

**Seven episodes after the Kokoro trailer build succeeds:** One introductory trailer plus Three Channel Laboratory; How Fast Can Art Change?; The Forked Transmission; The Left Branch; The Right Branch; Link and Timestamp Diagnostics.

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

## Voice production policy (2026-10-12)

Use **Kokoro TTS by default** for NEW natural spoken narration, including the project's public trailer. Preferred English voices: `bm_lewis` and `bm_george`. Use eSpeak/other explicitly synthetic or processed voices only when a robotic, mechanical, or intentionally distorted effect is needed. **Do not silently fall back to robotic speech** if Kokoro inference fails. Existing eSpeak laboratory recordings are preserved as historical tests.

Implementation: `tools/build_kokoro_trailer.py`, `kokoro-onnx` (MIT), Kokoro model weights (Apache 2.0). The GitHub Actions build downloads and caches the model only for generation; no model weights are distributed to podcast listeners. Trailer uses 44.1-kHz stereo MP3 encoding, includes embedded chapters, one prominent QR leading to this repository, and a stable episode GUID. In future audio revisions, KEEP the GUID and change the media URL (for example, `-v2.mp3`) to bypass player caching. The experimental eSpeak stereo MP3s use 22.05 kHz at 128 kbps. Apple's **RSS-feed audio** guidance expressly includes 22.05/24 kHz stereo at 80–160 kbps, so these recordings need not be re-encoded solely to submit an RSS feed. Apple's separate 44.1-kHz minimum applies to subscriber audio uploaded directly through Podcasts Connect. Kokoro trailer is produced at 44.1 kHz. See https://podcasters.apple.com/support/893-audio-requirements.

## Editing after Apple Podcasts catalog submission

The RSS feed remains authoritative. Metadata/episode art/audio may be replaced and test episodes may be removed by altering the published RSS feed. Existing downloaded recordings may persist on listeners' phones. **Never recycle or change an existing episode GUID**, even after removal. Use new filenames/URLs for replacement artwork and audio; avoid forcing the feed to generate new identities every build. Archive changed versions for reproducible research and prevent old QR and cross-episode links from breaking unexpectedly.

## Experimental trailer

The trailer is an explicit introduction and an invitation to potential designers, composers, programmers, playtesters and critics. Current contact link: this GitHub repository. Do not add a personal email until the separate project-contact discussion establishes one. Publishing the trailer on our own RSS does NOT itself submit the show to Apple Podcasts Connect.

## Apple Podcasts Connect submission diagnostics (2026-10-12)

Apple Podcasts Connect displayed a generic `An error has occurred. Try again later.` when adding the directly subscribed RSS feed. This does not disclose the underlying validator error. The old Apple category `Games & Hobbies` was replaced with `Leisure` > `Games`; the content XML namespace was added. Another feed defect was found: non-URL plain-text episode GUIDs lacked `isPermaLink="false"`. RSS 2.0 defaults missing `isPermaLink` to true, incorrectly treating the IDs as HTTP permalinks. The generator now adds `isPermaLink="false"` while keeping **all exact GUID texts unchanged**. Both the base test generator and the Kokoro trailer generator were corrected; the publish workflow asserts this for all seven items.

If the submit screen remains generically red after Render serves the new version, run a public live validator (https://podba.se/validate/ or https://www.castfeedvalidator.com/) and inspect network/HTTP failures. Apple itself recommends those tools. Passing XML validation does not guarantee Render allows Apple ingestion; test HTTP HEAD, byte range, public image/media retrieval, and exact RSS response. We cannot establish a Render problem solely because an isolated sandbox/browser tool cannot fetch the site. If external validators pass, investigate Podcasts Connect account/session or Apple service failure rather than repeatedly changing valid RSS data.

## Research and design

Core areas: audio-based navigation, audio masking and illusions, channel-specific secrets, independent screen information, timed orchestration, and unusual podcast-player mechanics.
