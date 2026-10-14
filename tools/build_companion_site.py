#!/usr/bin/env python3
"""Build spoiler-free mobile episode webpages AFTER all audio/feed assets exist.

Static HTML/CSS only for core presentation; optional tiny JS adds local audio seeks.
No chapter image galleries, secret codes, generated transcripts, or answer keys on pages.
"""
from pathlib import Path
import html, json, re
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
SITE=ROOT/'site'
BASE='https://play-by-ear-gamecast-lab.onrender.com/'
SHOW='https://podcasts.apple.com/us/podcast/id6822012769'
(SITE/'assets').mkdir(parents=True,exist_ok=True)

CSS=r'''
:root{color-scheme:dark;--bg:#09141f;--panel:#102638;--panel2:#162e3f;--text:#f3f0e5;--sub:#b6c8cf;--line:#345065;--accent:#91eadb;--gold:#efd3a1}
*{box-sizing:border-box}
html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 80% -20%,#173e50 0,transparent 40%),var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;line-height:1.55;font-size:16px}
a{color:var(--accent)}a:hover{text-decoration-color:var(--gold)}
a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid var(--gold);outline-offset:4px}
.shell{width:min(100% - 32px,880px);margin:auto}
header{border-bottom:1px solid var(--line);padding:13px 0;background:rgba(8,19,30,.78)}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.brand{font-weight:850;letter-spacing:.075em;text-decoration:none;color:var(--text);font-size:15px}
.nav{display:flex;gap:16px;align-items:center;font-size:14px}.nav a{text-decoration:none}
main{padding:35px 0 80px}.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:750;margin:0 0 12px}
h1{font-weight:800;letter-spacing:-.035em;line-height:1.1;font-size:clamp(34px,7vw,64px);margin:0 0 18px}
h2{font-size:clamp(22px,4vw,32px);line-height:1.2;letter-spacing:-.02em}
.lead{font-size:clamp(17px,2.5vw,21px);max-width:640px;color:var(--sub);margin:0 0 20px}
.muted,.small{color:var(--sub)}.small{font-size:13px}
.hero{padding:22px 0 32px;border-bottom:1px solid var(--line)}
.buttons{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:12px 17px;min-height:46px;border-radius:11px;text-decoration:none;font-weight:720;border:1px solid var(--line);font-size:15px;cursor:pointer;color:var(--text);background:var(--panel2)}
.btn.primary{background:var(--accent);color:#071824;border:1px solid transparent}
.btn.ghost{background:transparent}.btn:hover{filter:brightness(1.07)}
.card{background:var(--panel);padding:22px;border:1px solid var(--line);border-radius:17px;min-width:0}
.list{display:grid;gap:14px;padding:25px 0}
.card h2{margin:7px 0;font-size:22px}
.card p{margin:7px 0 15px;color:var(--sub)}
.card-link{color:var(--text);text-decoration:none}.card-link:hover{color:var(--accent)}
.two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.cover{max-width:200px;width:100%;border-radius:14px;border:1px solid var(--line);background:#0b2030;aspect-ratio:1/1;object-fit:cover}
.episode-head{display:flex;gap:22px;align-items:start}
.player{margin:25px 0;padding:20px 22px;background:var(--panel);border-radius:17px;border:1px solid var(--line)}
audio{width:100%;margin-top:6px}
details{border:1px solid var(--line);border-radius:12px;padding:15px 17px;margin:14px 0;background:var(--panel)}
summary{cursor:pointer;font-weight:730;color:var(--text)}
.seek-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:16px}
.seek-grid button{min-height:44px;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:9px;padding:9px;text-align:left;cursor:pointer;font:inherit;font-size:14px}
.timing{font-variant-numeric:tabular-nums;color:var(--accent);font-weight:750}
footer{padding:25px 0 50px;border-top:1px solid var(--line);font-size:13px;color:var(--sub)}
.notice{padding:14px 17px;border-left:3px solid var(--accent);background:var(--panel);border-radius:6px;margin:20px 0}
.pill{border:1px solid var(--line);padding:3px 9px;border-radius:99px;font-size:12px;color:var(--sub);display:inline-block;margin-right:6px}
@media(max-width:560px){.two,.seek-grid{grid-template-columns:1fr}.episode-head{display:block}.cover{max-width:140px;margin-bottom:18px}.nav{gap:10px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
'''
(SITE/'assets'/'style.css').write_text(CSS,encoding='utf-8')
EP_HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>TITLE • Play by Ear Gamecast</title><link rel="stylesheet" href="assets/style.css"></head>
<body><header><div class="shell top"><a class="brand" href="index.html">PLAY BY EAR <span style="color:var(--accent)">GAMECAST</span></a><nav class="nav"><a href="index.html">Episodes</a><a href="https://github.com/udeudeude/Play-by-Ear-GameCast">GitHub ↗</a></nav></div></header>
<main class="shell">
<section class="hero episode-head"><div><img class="cover" src="COVER" alt="Episode cover"></div>
<div><p class="eyebrow">AUDIO EXPERIMENT · DURATION</p><h1>TITLE</h1><p class="lead">DESCRIPTION</p>
<div class="buttons"><a class="btn primary" href="APPLE">Open in Apple Podcasts ↗</a><a class="btn ghost" href="https://podcasts.apple.com/us/podcast/id6822012769">Open show</a></div>
</div></section>
<div class="player"><strong>Web audio preview</strong><p class="small">For full testing, listen in the Apple Podcasts iOS app. This browser player is a fallback.</p><audio id="episode" controls preload="metadata" src="AUDIO"></audio></div>
<div class="notice"><strong>Spoiler-free by design.</strong> This page does not display hidden messages, answers, chapter artwork, or transcript text. Visual surprises remain in the podcast player.</div>
ADDITIONAL
<details><summary>Chapter navigation (titles and times only)</summary><p class="small">Select a chapter to seek within the webpage's audio player. This is a browser test, separate from Apple Podcasts' native chapters.</p>
<div class="seek-grid">CHAPTERS</div></details>
<details><summary>Technical information</summary><p>Each episode may contain embedded ID3 chapter artwork, alternate left/right stereo information, timestamps, or QR artwork. Apple Podcasts can behave differently from Safari or other podcast apps.</p><p>Use a second device to scan on-screen QR codes. If the destination changes, note whether you saw Safari or Apple Podcasts.</p></details>
</main><footer><div class="shell">Play by Ear Gamecast · Experimental tabletop games made of audio · <a href="https://github.com/udeudeude/Play-by-Ear-GameCast">Project repository</a></div></footer>
<script>document.querySelectorAll('[data-seek]').forEach(function(b){b.addEventListener('click',function(){var a=document.getElementById('episode');a.currentTime=Number(b.dataset.seek);a.play().catch(function(){});});});</script></body></html>'''
INDEX_HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark">
<title>Play by Ear Gamecast · Games made of sound</title><meta name="description" content="Experimental tabletop games whose mechanics depend on recorded podcast audio."><link rel="stylesheet" href="assets/style.css">
</head><body><header><div class="shell top"><a class="brand" href="index.html">PLAY BY EAR <span style="color:var(--accent)">GAMECAST</span></a><nav class="nav"><a href="#episodes">Episodes</a><a href="https://github.com/udeudeude/Play-by-Ear-GameCast">GitHub ↗</a></nav></div></header>
<main class="shell"><section class="hero"><p class="eyebrow">Games made of sound</p><h1>Play by Ear<br>Gamecast</h1><p class="lead">What if a tabletop game lived inside a recording? We are testing unusual uses of podcast audio, chapters, timing, stereo separation, and synchronized visuals.</p>
<div class="buttons"><a class="btn primary" href="https://podcasts.apple.com/us/podcast/id6822012769">Listen in Apple Podcasts ↗</a><a class="btn ghost" href="feed.xml">RSS feed</a></div>
<p class="small">Public prototype laboratory. The games are experiments, not polished releases.</p></section>
<section id="episodes"><h2>Experiments</h2><p class="muted">All episode webpages are spoiler-free. A separate iOS player may be required for full functionality.</p>
<div class="list">EPISODES</div></section>
<section class="card"><p class="eyebrow">Participate</p><h2>Help explore the medium</h2>
<p>Designers, composers, game players, software makers, and curious listeners can report unexpected behavior or propose mechanics using our GitHub repository.</p>
<a class="btn ghost" href="https://github.com/udeudeude/Play-by-Ear-GameCast">Open project repository ↗</a>
</section></main><footer><div class="shell">Original experiments · <a href="https://github.com/udeudeude/Play-by-Ear-GameCast">Play by Ear Gamecast</a></div></footer></body></html>'''
def remove_markup(s):
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html.unescape(s or ''))).strip()
def nice_duration(x):
    s=int(float(x or 0));return f'{s//60}:{s%60:02d}'
def get_catalog():
    p=SITE/'apple-episode-links.json'
    try:return json.loads(p.read_text())['episodes']
    except Exception:return {}
def make():
    root=ET.parse(SITE/'feed.xml').getroot()
    catalog=get_catalog()
    it='{http://www.itunes.com/dtds/podcast-1.0.dtd}'
    all_items=list(root.findall('./channel/item'))
    listings=[]
    for item in all_items:
        title=item.findtext('title') or 'Untitled episode'
        slink=item.findtext('link') or ''
        name=slink.rsplit('/',1)[-1].removesuffix('.html')
        if not name:
            continue
        enclosure=item.find('enclosure')
        cover=item.find(it+'image')
        cover_url=cover.attrib['href'] if cover is not None else ''
        cover_rel='art/'+cover_url.rsplit('/',1)[-1] if cover_url else ''
        duration=nice_duration(item.findtext(it+'duration'))
        ep_name=name+'.html'
        description=remove_markup(item.findtext('description'))
        # No spoiler sections, chapter media art, or transcript quoted in listing.
        short=description[:185].rsplit(' ',1)[0]+'…' if len(description)>185 else description
        # In show notes HTML may include operational links; avoid rendering those here.
        if name=='crossroads-link-lab':
            short='A hands-on test of chapter jumps, links between episodes, two-device QR relays, and timestamped sharing.'
        eid=catalog.get(title)
        app_url=(SHOW+'?i='+str(eid)) if eid else SHOW
        media_path='media/'+(enclosure.attrib['url'].rsplit('/',1)[-1] if enclosure is not None else '')
        chapters_file=SITE/'chapters'/(name+'.json')
        chapters=[]
        if chapters_file.exists():
            try:chapters=json.loads(chapters_file.read_text())['chapters']
            except Exception:pass
        chapter_html=''.join(
            '<button type="button" data-seek="'+str(c.get('startTime',0))+'"><span class="timing">'+
            nice_duration(c.get('startTime',0))+'</span> '+html.escape(c.get('title','Chapter'))+'</button>'
            for c in chapters)
        if name=='crossroads-link-lab':
            extra='''<section class="card"><p class="eyebrow">Choose a route</p><h2>Test the handoff</h2>
<p>All buttons lead to experiments, not answers. One method may open a browser before returning to Podcasts.</p>
<div class="two">
<a class="btn" href="go/left.html">Left destination · stable link ↗</a>
<a class="btn" href="go/right.html">Right destination · stable link ↗</a>
<a class="btn" href="go/intra-left.html">Within episode · left ↗</a>
<a class="btn" href="go/intra-right.html">Within episode · right ↗</a>
</div></section>'''
        else:extra=''
        page=EP_HTML.replace('TITLE',html.escape(title))
        page=page.replace('COVER',html.escape(cover_rel,quote=True))
        page=page.replace('DURATION',duration)
        page=page.replace('DESCRIPTION',html.escape(short))
        page=page.replace('APPLE',html.escape(app_url,quote=True))
        page=page.replace('AUDIO',html.escape(media_path,quote=True))
        page=page.replace('CHAPTERS',chapter_html).replace('ADDITIONAL',extra)
        (SITE/ep_name).write_text(page,encoding='utf-8')
        listings.append((title,ep_name,short,duration))
    listings.reverse()
    cards=[]
    for title,link,short,duration in listings:
        cards.append('<article class="card"><span class="pill">'+duration+'</span><h2><a class="card-link" href="'+
        html.escape(link,quote=True)+'">'+html.escape(title)+'</a></h2><p>'+html.escape(short)+
        '</p><a class="btn ghost" href="'+html.escape(link,quote=True)+'">View spoiler-free episode page ↗</a></article>')
    (SITE/'index.html').write_text(INDEX_HTML.replace('EPISODES',''.join(cards)),encoding='utf-8')
    print('COMPANION_READY',len(listings),'spoiler-free episode pages')

if __name__=='__main__':make()
