#!/usr/bin/env python3
"""Publish an original Kokoro link-navigation lab without changing existing episode GUIDs.

Outputs a new episode, QR chapter artwork, optional shortlink pages, and its RSS item.
Existing original audio and chapter tests remain unchanged.
"""
from pathlib import Path
import json, os, urllib.request, urllib.parse, subprocess, wave, tempfile, re
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.etree import ElementTree as ET
from html import escape
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TCON, TDRC, APIC, CHAP, CTOC
from mutagen.mp3 import MP3
from scipy.signal import resample_poly
from kokoro_onnx import Kokoro
import qrcode

ROOT=Path(__file__).resolve().parent.parent
SITE=ROOT/'site'
BASE=os.environ.get('PLAY_BY_EAR_BASE','https://play-by-ear-gamecast-lab.onrender.com/').rstrip('/')+'/'
APP_SHOW='https://podcasts.apple.com/us/podcast/play-by-ear-gamecast/id6822012769'
SHOW_ID=6822012769
TITLE='Crossroads: The Link Laboratory'
SLUG='crossroads-link-lab'
GUID='play-by-ear-crossroads-link-lab-2026-v1'
SR=44100
MODEL_DIR=Path(os.environ.get('KOKORO_MODEL_DIR','/tmp/play-by-ear-kokoro'))
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
for part in ['media','art','chapters','transcripts','go']:
    (SITE/part).mkdir(parents=True,exist_ok=True)

def apple_url(episode_id,time=None):
    value=APP_SHOW+'?i='+str(episode_id)
    return value if time is None else value+'&t='+str(int(time))

def resolve_episode_ids():
    """Use Apple's live catalog IDs, never invent the ?i= identifier."""
    cache={}
    query='https://itunes.apple.com/lookup?'+urllib.parse.urlencode({
        'id':SHOW_ID,'entity':'podcastEpisode','limit':200,'country':'us'})
    try:
        req=urllib.request.Request(query,headers={'User-Agent':'PlayByEarGamecast/1.0 (podcast link testing)'})
        with urllib.request.urlopen(req,timeout=20) as reply:
            data=json.load(reply)
        for item in data.get('results',[]):
            if item.get('kind')=='podcast-episode' or item.get('wrapperType')=='podcastEpisode':
                name=item.get('trackName','').strip()
                episode_id=item.get('trackId')
                if name and isinstance(episode_id,int):cache[name]=episode_id
    except Exception as ex:
        print('WARNING: Apple episode lookup unavailable:',str(ex),flush=True)
    output={'show':APP_SHOW,'episodes':cache,'catalogSource':query}
    (SITE/'apple-episode-links.json').write_text(json.dumps(output,indent=2)+'\n')
    for name in ['The Left Branch','The Right Branch',TITLE]:
        print('APPLE ID',name,cache.get(name,'PENDING'),flush=True)
    return cache

def art(name,title,subtitle,qr_url=None):
    n=1400
    im=Image.new('RGB',(n,n),(11,27,44))
    if qr_url:
        qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=16,border=4)
        qr.add_data(qr_url);qr.make(fit=True)
        q=qr.make_image(fill_color='black',back_color='white').convert('RGB')
        # The white quiet zone remains in the 1260x1260 graphic.
        im.paste(q.resize((1260,1260),Image.Resampling.NEAREST),(70,70))
    else:
        d=ImageDraw.Draw(im)
        for k in range(14):
            inset=k*39
            d.ellipse((120-inset,170-inset,1280+inset,1330+inset),outline=(22+5*k,75+7*k,112+6*k),width=3)
        d.rounded_rectangle((68,68,1332,1332),radius=35,outline=(238,205,137),width=7)
        f=ImageFont.truetype(BOLD,65)
        big=ImageFont.truetype(BOLD,95)
        little=ImageFont.truetype(FONT,42)
        def middle(t,y,font,color):
            box=d.textbbox((0,0),t,font=font)
            d.text(((n-(box[2]-box[0]))/2,y),t,font=font,fill=color)
        middle('PLAY BY EAR GAMECAST',218,f,(111,218,203))
        middle(title,590,big if len(title)<22 else f,(241,235,208))
        middle(subtitle,835,little,(111,218,203))
        middle('CROSSROADS  /  LINK EXPERIMENT',1180,little,(238,205,137))
    path=SITE/'art'/(name+'.jpg')
    im.save(path,'JPEG',quality=83,optimize=True)
    return path

# Speech is short enough for its allocated fixed-length chapter; uncovered time is
# genuine quiet, so chapter jumps and QR opportunities are not rushed.
SECTIONS=[
(0,'Start Here','WELCOME','A navigation experiment',
 'Welcome to Crossroads, a Play by Ear Gamecast laboratory. We will test several ways to move between recordings, and between moments in one recording, using an ordinary iPhone podcast player. Some jumps may open a browser first. All experiments are voluntary; the same destinations are available by chapter.'),
(45,'Choose a Chapter','FORK','Use the chapter menu',
 'Begin with a choice. In the episode description, try the internal timestamp links for Left Room and Right Room. If a link fails, use the native chapter menu. Choose one route. You can return to this hub whenever you wish.'),
(90,'Left Room','LEFT ROOM','Internal navigation',
 'You reached the left room inside this same recording. The word for this test is tide. Make a note, then move to the right room, return to the choice hub, or test a QR destination.'),
(135,'Right Room','RIGHT ROOM','Internal navigation',
 'You reached the right room without loading another episode. The word for this test is stone. Record it, then return to the hub, or continue to the QR tests.'),
(180,'Direct QR to Left Branch','QR  /  APPLE','Scan with a second device',
 'This chapter displays a QR code intended to open The Left Branch in Apple Podcasts. Scan the full artwork with another phone. Note whether Apple Podcasts opens directly, or whether Safari intervenes. A missing catalog identifier will route to our companion navigation page.'),
(225,'Direct QR to Right Branch','QR  /  APPLE','Test the opposite destination',
 'The next QR attempts the same direct jump to The Right Branch. The listener who scans should keep their result private until both players have completed the test.'),
(270,'Permanent QR to Left','QR  /  STABLE','A project-owned address',
 'This QR contains a permanent Play by Ear web address, rather than the Apple episode URL. It is intended to stay usable even if Apple changes its link format. Does it cost an additional browser step?'),
(315,'Permanent QR to Right','QR  /  STABLE','Compare the handoff',
 'Repeat that test with the right-hand destination. Compare it with the direct Apple QR. A stable link has advantages, but direct links may feel more natural.'),
(360,'QR Back into This Episode','QR  /  RETURN','Jump to the left room',
 'The image now contains a link designed to bring a second device into this episode at the left room. Because this episode receives its Apple identifier only after publication, our companion can resolve that identifier later.'),
(405,'Exchange a Timestamp','SHARE','Use the Share sheet',
 'Seek to a point of your choosing. From the episode view, share the episode from the current time. Send that link to a second player. Test whether it starts in the right place on their phone, and whether the title or notes disclose anything unexpected.'),
(450,'Observation','RESULTS','Keep the outcomes',
 'That completes the tests. Which path needed the fewest taps? Did you stay inside Apple Podcasts? Did the timestamp survive? Compare chapter navigation, text links, direct QR, project shortlinks, and the share sheet. Your observations will inform a real game.')
]
DURATION=495

def synth_audio():
    kokoro=Kokoro(str(MODEL_DIR/'kokoro-v1.0.onnx'),str(MODEL_DIR/'voices-v1.0.bin'))
    arr=np.zeros((DURATION*SR,2),dtype=np.float32)
    vtt=['WEBVTT','']
    def stamp(sec):
        return f'00:{int(sec//60):02}:{int(sec%60):02}.000'
    for ix,(start,label,headline,subtitle,words) in enumerate(SECTIONS):
        # Never use bm_george: that voice is reserved for Living Patterns.
        sound,sr=kokoro.create(words,voice='bm_lewis',speed=1.08,lang='en-gb')
        sound=np.asarray(sound,dtype=np.float32)
        if sound.ndim>1:sound=sound.mean(axis=1)
        if sr!=SR:sound=resample_poly(sound,SR,sr)
        available=(SECTIONS[ix+1][0] if ix+1<len(SECTIONS) else DURATION)-start-3
        if len(sound)>round(available*SR):
            raise ValueError(f'Kokoro speech too long at {start}s: {len(sound)/SR:.1f}s > {available:.1f}s')
        pos=(start+2)*SR
        arr[pos:pos+len(sound),:]+=sound[:,None]*.7
        vtt.extend([stamp(start+2)+' --> '+stamp(start+2+len(sound)/SR),
                    '<v Narrator>'+words+'</v>',''])
    peak=float(np.max(np.abs(arr)))
    if peak>0.92:arr*=0.92/peak
    fd,wav=tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        with wave.open(wav,'wb') as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
            w.writeframes(np.int16(np.clip(arr,-1,1)*32767).tobytes())
        media=SITE/'media'/(SLUG+'-v1.mp3')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',wav,
                        '-c:a','libmp3lame','-b:a','112k','-ar',str(SR),
                        '-joint_stereo','0',str(media)],check=True)
    finally:
        os.remove(wav)
    (SITE/'transcripts'/(SLUG+'.vtt')).write_text('\n'.join(vtt)+'\n',encoding='utf-8')
    return media

def make_shortlinks(ids):
    """Project-owned landing links provide explicit alternatives when app links fail."""
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Play by Ear · continue</title><link rel="stylesheet" href="../assets/style.css">
<main class="shell"><a class="back" href="../index.html">← Play by Ear Gamecast</a>
<p class="eyebrow">AUDIO DESTINATION</p><h1>Continue listening</h1>
<p>This link is part of an experiment. It may open Apple Podcasts or offer a direct link below.</p>
<p class="action"><a id="go" class="btn primary" href="URL">Open in Apple Podcasts ↗</a></p>
<p class="small">If Apple Podcasts doesn't open, use the show page and choose <strong>EPISODE</strong>.</p>
<a class="btn ghost" href="https://podcasts.apple.com/us/podcast/id6822012769">Open show listing</a>
</main></html>'''
    for slug,name,at in [('left','The Left Branch',0),('right','The Right Branch',0),
                          ('intra-left',TITLE,90),('intra-right',TITLE,135)]:
        eid=ids.get(name)
        url=apple_url(eid,at) if eid else APP_SHOW
        body=page.replace('URL',escape(url,quote=True)).replace('EPISODE',escape(name))
        # The new episode will gain an Apple catalog ID after Apple's next RSS ingest.
        # When it is absent, the page can resolve it dynamically if Apple's JSON API
        # permits fetch; otherwise it provides clear native chapter navigation.
        if eid is None and name==TITLE:
            body=body.replace('</main>',"<p class='small'>The Apple episode identifier is pending. Open the show and choose Crossroads, then the Left Room or Right Room chapter.</p></main>")
        (SITE/'go'/(slug+'.html')).write_text(body,encoding='utf-8')

def create(ids):
    def route(key):
        return BASE+'go/'+key+'.html'
    # Direct Apple QR only when an actual catalog ID was retrieved; never guess it.
    qr={
        4:apple_url(ids['The Left Branch'],28) if 'The Left Branch' in ids else route('left'),
        5:apple_url(ids['The Right Branch'],28) if 'The Right Branch' in ids else route('right'),
        6:route('left'),7:route('right'),8:route('intra-left')}
    cover=art(SLUG+'-cover-v1','CROSSROADS','Ten ways to travel through a podcast')
    media=synth_audio()
    tags=ID3(media)
    for tag in (TIT2(encoding=3,text=TITLE),TALB(encoding=3,text='Play by Ear Gamecast'),
                TPE1(encoding=3,text='Play by Ear'),TCON(encoding=3,text='Leisure'),
                TDRC(encoding=3,text='2026')):
        tags.add(tag)
    tags.add(APIC(encoding=3,mime='image/jpeg',type=3,desc='Episode cover',data=cover.read_bytes()))
    toc=[];chapter_data=[]
    for ix,(start,label,headline,subtitle,words) in enumerate(SECTIONS):
        until=SECTIONS[ix+1][0] if ix+1<len(SECTIONS) else DURATION
        pic=art(SLUG+f'-chapter-{ix:02d}-v1',headline,subtitle,qr.get(ix))
        toc_id=f'cross-{ix:02d}'
        toc.append(toc_id)
        tags.add(CHAP(element_id=toc_id,start_time=start*1000,end_time=until*1000,
                      start_offset=0xffffffff,end_offset=0xffffffff,
                      sub_frames=[TIT2(encoding=3,text=label),
                                  APIC(encoding=3,mime='image/jpeg',type=3,
                                       desc='Chapter image',data=pic.read_bytes())]))
        chapter_data.append({'startTime':start,'title':label,'img':BASE+'art/'+pic.name,
                             'url':BASE+'go/'+('left' if ix in (4,6) else 'right')+'.html'
                             if ix in (4,5,6,7) else BASE+SLUG+'.html'})
    tags.add(CTOC(element_id='crossroads-toc',flags=3,child_element_ids=toc,
                  sub_frames=[TIT2(encoding=3,text='Crossroads chapters')]))
    tags.save(media,v2_version=3)
    (SITE/'chapters'/(SLUG+'.json')).write_text(json.dumps({'version':'1.2.0','chapters':chapter_data},indent=2)+'\n')
    make_shortlinks(ids)
    # Populate native Apple links where catalog IDs are known. Deliberately
    # label any unconfirmed new-episode links as tests, rather than claiming success.
    internal_id=ids.get(TITLE)
    def selftarget(sec):
        return apple_url(internal_id,sec) if internal_id else route('intra-left' if sec==90 else 'intra-right')
    a=lambda href,label: '<a href="'+escape(href,quote=True)+'">'+escape(label)+'</a>'
    htmlnotes=('<p>A navigation experiment for iOS 18. No puzzle solutions appear in these notes.</p>'
        '<p><strong>Within this recording:</strong> '+a(selftarget(90),'Left Room at 01:30')+
        ' · '+a(selftarget(135),'Right Room at 02:15')+
        '. If a link fails, use the native chapter list.</p>'
        '<p><strong>Into another episode:</strong> '+
        a(apple_url(ids['The Left Branch']) if 'The Left Branch' in ids else route('left'),'The Left Branch')+
        ' · '+a(apple_url(ids['The Right Branch']) if 'The Right Branch' in ids else route('right'),'The Right Branch')+'.</p>'
        '<p><strong>Project-owned permanent links:</strong> '+
        a(route('left'),'Left shortlink')+' · '+a(route('right'),'Right shortlink')+'.</p>'
        '<p>'+a(BASE+SLUG+'.html','Spoiler-free episode website')+' · '+
        a(APP_SHOW,'Apple Podcasts show listing')+'</p>')
    tree=ET.parse(SITE/'feed.xml')
    root=tree.getroot();chan=root.find('channel')
    if any(i.findtext('guid')==GUID for i in chan.findall('item')):
        raise RuntimeError('Crossroads GUID already present; refusing duplicate')
    ns='http://www.itunes.com/dtds/podcast-1.0.dtd'
    pod='https://podcastindex.org/namespace/1.0'
    ET.register_namespace('itunes',ns)
    ET.register_namespace('podcast',pod)
    item=ET.Element('item')
    def e(tag,v):ET.SubElement(item,tag).text=str(v)
    e('title',TITLE)
    ET.SubElement(item,'guid',{'isPermaLink':'false'}).text=GUID
    e('pubDate',format_datetime(datetime(2026,10,14,13,0,tzinfo=timezone.utc)))
    e('description',htmlnotes)
    e('link',BASE+SLUG+'.html')
    e('{'+ns+'}author','Play by Ear')
    e('{'+ns+'}explicit','false')
    e('{'+ns+'}season','1')
    e('{'+ns+'}episode','7')
    e('{'+ns+'}episodeType','bonus')
    e('{'+ns+'}duration',DURATION)
    ET.SubElement(item,'{'+ns+'}image',{'href':BASE+'art/'+cover.name})
    ET.SubElement(item,'enclosure',{'url':BASE+'media/'+media.name,'length':str(media.stat().st_size),
                                    'type':'audio/mpeg'})
    ET.SubElement(item,'{'+pod+'}chapters',{'url':BASE+'chapters/'+SLUG+'.json',
                                        'type':'application/json+chapters'})
    ET.SubElement(item,'{'+pod+'}transcript',{'url':BASE+'transcripts/'+SLUG+'.vtt',
                                           'type':'text/vtt','language':'en'})
    raw=ET.tostring(item,encoding='unicode')
    # Clean serialization of HTML episode notes for Apple Podcasts.
    # Force literal HTML in a CDATA description, irrespective of how
    # ElementTree chooses to escape quotes in this RSS string.
    raw=re.sub(r'<description>.*?</description>',
               lambda _: '<description><![CDATA['+htmlnotes+']]></description>',
               raw,count=1,flags=re.DOTALL)
    path=SITE/'feed.xml'
    current=path.read_text(encoding='utf-8')
    path.write_text(current.replace('</channel>','  '+raw+'\n</channel>',1),encoding='utf-8')
    print('CROSSROADS_READY',media.name,'chapterCount',len(toc),'size',media.stat().st_size)

if __name__=='__main__':
    create(resolve_episode_ids())
