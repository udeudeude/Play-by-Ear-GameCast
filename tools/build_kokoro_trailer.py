#!/usr/bin/env python3
"""Build the Kokoro-voiced Play by Ear trailer and append it to site/feed.xml.

The existing six eSpeak technical episodes remain deliberately unchanged.
Kokoro is the default for NEW natural-voice material; robotic speech remains
an intentional special effect. Requires model and voices from kokoro-onnx.
"""
from pathlib import Path
from email.utils import format_datetime
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from html import escape
import json
import os
import tempfile
import subprocess
import wave
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.signal import resample_poly
from mutagen.id3 import ID3, APIC, TIT2, TALB, TPE1, TCON, TDRC, TRCK, CTOC, CHAP
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = os.environ.get(
    "PLAY_BY_EAR_BASE", "https://play-by-ear-gamecast-lab.onrender.com/"
).rstrip("/") + "/"
MODEL_DIR = Path(os.environ.get("KOKORO_MODEL_DIR", "/tmp/play-by-ear-kokoro"))
MODEL = MODEL_DIR / "kokoro-v1.0.onnx"
VOICES = MODEL_DIR / "voices-v1.0.bin"
SR = 44100
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SLUG = "play-by-ear-trailer"
VERSION = "v1"
GUID = "play-by-ear-trailer-2026-stable-guid"

# A stand-alone project introduction, not a game or a fictional transmission.
SEGMENTS = [
    ("What is Play by Ear?", "bm_lewis",
     "What if a board game were made of listening? Not a soundtrack behind a "
     "game, and not simply an audio adventure. Imagine a recording that is "
     "the game board, the clock, a witness, or even your opponent. "
     "Welcome to Play by Ear, an experiment in original tabletop games "
     "designed for ordinary podcast players."),
    ("A new playing surface", "bm_george",
     "Two players might share a pair of earbuds, each hearing different "
     "secrets, while a third player watches pictures change on the screen. "
     "A QR code might send another player to a different recording. "
     "You might explore a place by jumping between chapters, or try to "
     "reconstruct a mystery from echoes, interruptions, and silence."),
    ("A public laboratory", "bm_lewis",
     "For now, this feed is a laboratory, not a finished collection of games. "
     "The episodes test what podcast players actually permit. Some experiments "
     "involve stereo separation, rapid changes of chapter artwork, or branching "
     "between recordings. Others expose real limitations. The failures are "
     "part of the research."),
    ("Get involved", "bm_george",
     "The longer vision includes cooperative games, listening puzzles, "
     "strange new uses of radio drama, and experiments inspired by sound art "
     "and Fluxus. If you are interested in designing, composing, programming, "
     "playtesting, or challenging an idea, find the Play by Ear GitHub "
     "repository linked in the episode description. "
     "For now, bring headphones, curiosity, and maybe a piece of paper. "
     "This is Play by Ear.")
]


def art(name, title, subtitle, qr=False):
    n = 1400
    im = Image.new("RGB", (n, n), (14, 25, 39))
    d = ImageDraw.Draw(im)
    if qr:
        import qrcode
        obj = qrcode.QRCode(
            border=4, box_size=16,
            error_correction=qrcode.constants.ERROR_CORRECT_M)
        obj.add_data("https://github.com/udeudeude/Play-by-Ear-GameCast")
        obj.make(fit=True)
        q = obj.make_image(
            fill_color="black", back_color="white").convert("RGB")
        q = q.resize((1260, 1260), Image.Resampling.NEAREST)
        im.paste(q, (70, 70))
    else:
        for i in range(11):
            inset = i * 45
            d.ellipse((120-inset, 240-inset, 1280+inset, 1400+inset),
                      outline=(17+i*7, 80+i*8, 94+i*8), width=3)
        d.rounded_rectangle((65, 72, 1335, 1328), radius=44,
                            outline=(229, 207, 154), width=6)
        f1 = ImageFont.truetype(BOLD, 96)
        f2 = ImageFont.truetype(BOLD, 53)
        f3 = ImageFont.truetype(FONT, 37)
        def centered(text, y, font, color):
            bb = d.textbbox((0, 0), text, font=font)
            d.text(((n-(bb[2]-bb[0]))/2, y), text,
                   font=font, fill=color)
        centered("PLAY BY EAR", 300, f1, (245, 222, 170))
        centered(title, 560, f2, (229, 241, 238))
        centered(subtitle, 670, f3, (130, 222, 211))
        centered("GAMES MADE OF SOUND", 1130, f3, (245, 222, 170))
    p = SITE / "art" / (name + ".jpg")
    im.save(p, "JPEG", quality=83, optimize=True)
    return p


def timecode(t):
    ms = round(t * 1000)
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, rem = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02}.{rem:03}"


def create():
    if not MODEL.is_file() or not VOICES.is_file():
        raise RuntimeError(
            "Missing Kokoro model files in " + str(MODEL_DIR)
            + ". Do not silently use eSpeak for natural narration.")
    voice = Kokoro(str(MODEL), str(VOICES))
    parts = []
    chaps = []
    vtt = ["WEBVTT", ""]
    cursor = 0
    for idx, (heading, speaker, words) in enumerate(SEGMENTS):
        start_sec = cursor / SR
        print("Synthesizing Kokoro", idx + 1, speaker, heading, flush=True)
        samples, source_sr = voice.create(
            words, voice=speaker, speed=1.0, lang="en-gb")
        sound = np.asarray(samples, dtype=np.float32)
        if sound.ndim > 1:
            sound = np.mean(sound, axis=1)
        if source_sr != SR:
            sound = resample_poly(sound, SR, source_sr).astype(np.float32)
        # Add a very short fade to avoid clicks at segment transitions.
        fade = min(int(0.025 * SR), len(sound) // 2)
        if fade:
            sound[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
            sound[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        padding = np.zeros(int((1.35 if idx < 3 else 1.7) * SR),
                           dtype=np.float32)
        parts.extend([sound * 0.75, padding])
        cursor += len(sound) + len(padding)
        chaps.append({"start": start_sec, "title": heading,
                      "text": words, "speaker": speaker})
        vtt += [timecode(start_sec) + " --> " +
                timecode((cursor - len(padding)) / SR),
                "<v " + speaker + ">" + words + "</v>", ""]
    mono = np.concatenate(parts)
    stereo = np.repeat(mono[:, None], 2, axis=1)
    peak = float(np.max(np.abs(stereo)))
    if peak > .93:
        stereo *= .93 / peak
    duration = len(stereo) / SR

    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with wave.open(wav_path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(np.int16(
                np.clip(stereo, -1, 1) * 32767).tobytes())
        media = SITE / "media" / (SLUG + "-" + VERSION + ".mp3")
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", wav_path, "-codec:a", "libmp3lame",
            "-b:a", "128k", "-ar", str(SR), "-joint_stereo", "0",
            str(media)], check=True)
    finally:
        os.remove(wav_path)

    cover = art(SLUG + "-cover-" + VERSION,
                "AN INVITATION", "EXPERIMENTAL PODCAST GAMES")
    tags = ID3(media)
    tags.add(TIT2(encoding=3, text="Play by Ear: An Invitation"))
    tags.add(TALB(encoding=3, text="Play by Ear"))
    tags.add(TPE1(encoding=3, text="Play by Ear"))
    tags.add(TCON(encoding=3, text="Games & Hobbies"))
    tags.add(TDRC(encoding=3, text="2026"))
    tags.add(APIC(encoding=3, mime="image/jpeg", type=3,
                  desc="Trailer cover", data=cover.read_bytes()))
    chapter_json = []
    ids = []
    for idx, c in enumerate(chaps):
        is_last = idx == len(chaps) - 1
        image = art(
            SLUG + "-scene-" + str(idx) + "-" + VERSION,
            c["title"] if not is_last else "OPEN SOURCE",
            "A PUBLIC EXPERIMENT" if not is_last else "FIND US ON GITHUB",
            qr=is_last)
        end = chaps[idx+1]["start"] if not is_last else duration
        eid = "trailer-ch" + str(idx)
        ids.append(eid)
        tags.add(CHAP(
            element_id=eid,
            start_time=round(c["start"] * 1000),
            end_time=round(end * 1000),
            start_offset=0xffffffff, end_offset=0xffffffff,
            sub_frames=[
                TIT2(encoding=3, text=c["title"]),
                APIC(encoding=3, mime="image/jpeg", type=3,
                     desc="Trailer chapter image", data=image.read_bytes())
            ]))
        chapter_json.append({
            "startTime": round(c["start"], 3),
            "title": c["title"],
            "img": BASE + "art/" + image.name,
            "url": "https://github.com/udeudeude/Play-by-Ear-GameCast"
                if is_last else BASE + SLUG + ".html"})
    tags.add(CTOC(
        element_id="trailer-toc", flags=3,
        child_element_ids=ids,
        sub_frames=[TIT2(encoding=3, text="Trailer chapters")]))
    tags.save(media, v2_version=3)
    (SITE / "transcripts" / (SLUG + ".vtt")).write_text(
        "\n".join(vtt), encoding="utf-8")
    (SITE / "chapters" / (SLUG + ".json")).write_text(
        json.dumps({"version": "1.2.0", "chapters": chapter_json}, indent=2),
        encoding="utf-8")
    body = (
        "<p>Welcome to Play by Ear: a research podcast about original "
        "tabletop games whose mechanics depend on recorded audio.</p>"
        "<p>This feed is currently an experimental laboratory, not "
        "a finished game collection. Some tests may fail. Later episodes "
        "may change or be removed as the project develops.</p>"
        "<p>Interested in contributing ideas, testing, composing or "
        "developing games? Visit "
        '<a href="https://github.com/udeudeude/Play-by-Ear-GameCast">'
        "the Play by Ear GitHub project</a>.</p>"
    )
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Play by Ear: An Invitation</title></head><body>"
        "<h1>Play by Ear: An Invitation</h1>"
        "<p>Original podcast-first tabletop games. This is an experiment.</p>"
        '<audio controls preload="metadata" src="media/' + media.name +
        '"></audio>' + body + "</body></html>")
    (SITE / (SLUG + ".html")).write_text(html, encoding="utf-8")
    # Append an RSS item without rewriting the feed or changing its existing
    # GUIDs, URLs, chapter metadata, or XML CDATA.
    ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    PODCAST = "https://podcastindex.org/namespace/1.0"
    ET.register_namespace("itunes", ITUNES)
    ET.register_namespace("podcast", PODCAST)
    item = ET.Element("item")
    def el(tag, value):
        ET.SubElement(item, tag).text = str(value)
    el("title", "Play by Ear: An Invitation")
    # Preserve the episode identifier but declare it is not an HTTP permalink.
    ET.SubElement(item, 'guid', {'isPermaLink': 'false'}).text = GUID
    el("pubDate", format_datetime(
        datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)))
    el("description", "Play by Ear: games made of listening. "
       "Currently an experimental laboratory. " +
       "Learn more: https://github.com/udeudeude/Play-by-Ear-GameCast")
    el("link", BASE + SLUG + ".html")
    el("{" + ITUNES + "}author", "Play by Ear")
    el("{" + ITUNES + "}explicit", "false")
    el("{" + ITUNES + "}episodeType", "trailer")
    el("{" + ITUNES + "}duration", str(round(duration)))
    ET.SubElement(item, "{" + ITUNES + "}image",
                  {"href": BASE + "art/" + cover.name})
    ET.SubElement(item, "enclosure", {
        "url": BASE + "media/" + media.name,
        "length": str(media.stat().st_size),
        "type": "audio/mpeg"})
    ET.SubElement(item, "{" + PODCAST + "}chapters", {
        "url": BASE + "chapters/" + SLUG + ".json",
        "type": "application/json+chapters"})
    ET.SubElement(item, "{" + PODCAST + "}transcript", {
        "url": BASE + "transcripts/" + SLUG + ".vtt",
        "type": "text/vtt", "language": "en"})
    feed_path = SITE / "feed.xml"
    feed = feed_path.read_text(encoding="utf-8")
    if GUID in feed:
        raise RuntimeError("Trailer already in RSS: will not duplicate GUID")
    if "</channel>" not in feed:
        raise RuntimeError("RSS missing closing channel element")
    feed = feed.replace(
        "</channel>", "  " + ET.tostring(
            item, encoding="unicode") + "\n  </channel>", 1)
    feed_path.write_text(feed, encoding="utf-8")
    print("TRAILER_READY", round(duration, 2), media.name,
          media.stat().st_size, flush=True)


if __name__ == "__main__":
    create()
