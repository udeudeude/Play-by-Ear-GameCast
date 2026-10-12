#!/usr/bin/env python3
"""Build a public Apple Podcasts iOS 18 test feed and original audio in site/.

Requirements on GitHub Actions: Python, numpy, Pillow, mutagen, qrcode,
ffmpeg, espeak-ng (or espeak). All content generated locally and originally.
"""
from pathlib import Path
from email.utils import format_datetime
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET
from html import escape, unescape
import json, os, subprocess, wave, tempfile, math, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TCON, TDRC, TRCK, TPOS, COMM, TXXX, APIC, CHAP, CTOC, TLEN

ROOT=Path(__file__).resolve().parent.parent
SITE=ROOT/'site'
BASE=os.environ.get('PLAY_BY_EAR_BASE','https://play-by-ear-gamecast-lab.onrender.com/').rstrip('/')+'/'
SR=22050
for folder in ['media','art','chapters','transcripts']:
    (SITE/folder).mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
VOICE='espeak-ng' if subprocess.run(['which','espeak-ng'],capture_output=True).returncode==0 else 'espeak'

def img(name, title, caption, secret='', frame=None, qr=False):
    n=1400
    im=Image.new('RGB',(n,n),(14,27,46))
    d=ImageDraw.Draw(im)
    f=lambda s,b=False: ImageFont.truetype(BOLD if b else FONT,s)
    for i in range(9):
        m=i*62
        d.ellipse((120-m,190-m,1280+m,1350+m),outline=(20+i*9,85+i*9,124+i*8),width=5)
    d.rounded_rectangle((54,55,1346,1345),radius=25,outline=(239,213,146),width=7)
    d.text((105,104),'PLAY BY EAR  //  iOS 18 LAB',font=f(39,True),fill=(245,219,153))
    def center(txt,y,size=67,color=(243,239,220)):
        font=f(size,True)
        box=d.textbbox((0,0),txt,font=font)
        d.text(((n-box[2])/2,y),txt,font=font,fill=color)
    center(title[:28],395,66)
    center(caption[:37],530,36)
    if secret:center(secret[:18],710,110,(255,163,96))
    if frame is not None:center('FRAME '+str(frame),940,49)
    if qr:
        import qrcode
        q=qrcode.make(BASE+'index.html').convert('RGB').resize((235,235))
        im.paste(q,(583,960))
    out=SITE/'art'/f'{name}.jpg'
    im.save(out,'JPEG',quality=78,optimize=True)
    return out

def spoken(text,voice='en-us+m3',speed=156):
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        subprocess.run([VOICE,'-v',voice,'-s',str(speed),'-a','170','-w',f.name,text],check=True,stdout=subprocess.DEVNULL)
        with wave.open(f.name,'rb') as w:
            rate=w.getframerate()
            raw=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768
    if rate!=SR:
        from scipy.signal import resample_poly
        from math import gcd
        g=gcd(rate,SR);raw=resample_poly(raw,SR//g,rate//g).astype(np.float32)
    return raw

def audio(slug,duration,speech):
    track=np.zeros((int(duration*SR),2),dtype=np.float32)
    for at,ch,text in speech:
        v='en-us+m3' if ch=='B' else ('en-us+m2' if ch=='L' else 'en-us+f3')
        a=spoken(text,v)
        pos=round(at*SR)
        a=a[:max(0,len(track)-pos)]
        if ch in ('B','L'):track[pos:pos+len(a),0]+=.58*a
        if ch in ('B','R'):track[pos:pos+len(a),1]+=.58*a
    peak=np.max(np.abs(track))
    if peak>.93:track*=.93/peak
    fd,raw=tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        with wave.open(raw,'wb') as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
            w.writeframes(np.int16(np.clip(track,-1,1)*32767).tobytes())
        out=SITE/'media'/f'{slug}.mp3'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',raw,'-codec:a','libmp3lame','-b:a','128k','-joint_stereo','0',str(out)],check=True)
    finally: os.remove(raw)
    return out

episodes=[
  dict(slug='lab-three-channels',title='Three Channel Laboratory',duration=277,
       desc='Three-player experiment: different information in LEFT, RIGHT and SCREEN. Includes links, QR code, chapter titles, stereo speech, transcript, and an intentionally exact four-minute thirty-seven-second running time.',
       chapters=[(0,'Welcome','WELCOME','Three separate information channels',''),
         (28,'Stereo Calibration','LEFT / RIGHT','Do not swap earbuds',''),
         (60,'Screen Channel','SCREEN','Only the screen player may read this','7'),
         (93,'Compare Clues','COMBINE','Exchange information, not earbuds',''),
         (127,'QR Image Test','QR CODE','Scan with another device', ''),
         (162,'Tone Experiments','TONES','Pitch and auditory attention',''),
         (198,'Transcript Test','WORDS','Searchable transcript trial',''),
         (229,'Duration Metadata','04:37','The total running time is a clue','437'),
         (260,'Trailing Silence','SILENCE','The last portion is intentional','')],
       speech=[(1,'B','Welcome to Play by Ear. This is an experiment in three independent information channels.'),
         (29,'B','Left and right listeners should each wear one earbud from the same pair. The screen observer does not listen.'),
         (37,'L','Left listener: remember the word MAPLE. You alone should know this.'),
         (37,'R','Right listener: remember the word QUARTZ. You alone should know this.'),
         (61,'B','Screen observer, watch for the secret shown in the chapter image. Do not tell the listeners yet.'),
         (72,'L','My secret codeword is LUNAR. Do not show this to the right listener.'),
         (72,'R','My secret codeword is COPPER. Do not show this to the left listener.'),
         (95,'B','Now compare your information. Say the left secret, followed by the right secret, followed by the screen digit.'),
         (128,'B','This chapter includes a QR code within its artwork. Test whether you can see or scan it.'),
         (163,'B','Listen for pitch and any unusual difference between the channels.'),
         (198,'B','This is the transcript test. Search for the unusual phrase violet cucumber semaphore.'),
         (230,'B','The total duration was chosen deliberately. It should appear as four minutes thirty seven seconds.'),
         (260,'B','The last seconds are deliberately silent. End of test.')]),
  dict(slug='lab-image-cadence',title='How Fast Can Art Change?',duration=147,
       desc='Embedded chapter image intervals include 20, 12, 8, 5, 2, 1, 0.5 and 0.1 seconds. The file encodes these, but Apple Podcasts display timing is unknown.',
       chapters=[(0,'Twenty Seconds','20 SEC','Start', ''),(20,'Twenty Seconds B','20 SEC','Second image',''),
         (40,'Twenty Seconds C','20 SEC','Third image',''),(60,'Twelve Seconds','12 SEC','Shorter',''),
         (72,'Eight Seconds','8 SEC','Shorter',''),(80,'Five Seconds','5 SEC','Shorter',''),
         (85,'Two Seconds','2 SEC','Shorter',''),(87,'One Second','1 SEC','Shorter',''),
         (88,'Half Second','0.5 SEC','Can you see it?',''),(88.5,'Tenth Second A','0.1 SEC','First',''),
         (88.6,'Tenth Second B','0.1 SEC','Second',''),(88.7,'Tenth Second C','0.1 SEC','Third',''),
         (88.8,'Tenth Second D','0.1 SEC','Fourth',''),(88.9,'Recovery','10 SEC','Return to normal',''),
         (98.9,'One Second B','1 SEC','Again',''),(99.9,'One Second C','1 SEC','Again',''),
         (100.9,'Half Second B','0.5 SEC','Again',''),(101.4,'Half Second C','0.5 SEC','Again',''),
         (101.9,'Recovery Two','18 SEC','Observe changes',''),(120,'End Observation','20 SEC','Pause and review',''),
         (140,'Last Seconds','END','Final image','')],
       speech=[(1,'B','This episode tests extremely short chapter images on Apple Podcasts for iOS eighteen.'),
         (42,'B','Watch the illustration and note whether its label changes by itself.'),
         (65,'B','Images will now accelerate. Please do not touch the screen.'),
         (108,'B','The very short image tests are over. Which images did you actually see?'),
         (124,'B','Now repeat while scrubbing manually. Compare your results.'),
         (141,'B','End of the art cadence experiment.')]),
  dict(slug='forked-transmission',title='The Forked Transmission',duration=199,
       desc='Choose-your-own-adventure test: at the Decision Room, use the player chapter list to choose Left Chamber or Right Chamber. See also the separate Left Branch and Right Branch episodes.',
       chapters=[(0,'Starting Point','START','Branch experiment',''),
         (28,'Two Choices','CHOICES','A fork in the recording',''),
         (55,'Decision Room','DECIDE','Choose LEFT or RIGHT',''),
         (80,'Left Chamber','LEFT','You chose a left branch',''),
         (110,'Left Evidence','LEFT CLUE','Compare routes',''),
         (140,'Right Chamber','RIGHT','You chose a right branch',''),
         (170,'Exit','EXIT','Find the next episode',''),
         (190,'Silence / Length','END','Count the seconds','')],
       speech=[(1,'B','This is a branching adventure test. Audio is fixed, but you choose what to hear next.'),
         (29,'B','You are confronted with two doors. A silver door on the left and a copper door on the right.'),
         (56,'B','Choose now. For left, jump to one minute twenty seconds. For right, jump to two minutes twenty seconds.'),
         (81,'B','You entered the left chamber. The walls contain a code marked seven.'),
         (112,'B','Your left evidence is the word VIOLET.'),
         (141,'B','You entered the right chamber. The floor contains a code marked nine.'),
         (171,'B','For a more ambitious test, follow the description link to an entirely different branch episode.'),
         (190,'B','End of transmission.')]),
  dict(slug='branch-left',title='The Left Branch',duration=73,
       desc='Alternate destination from The Forked Transmission. Left-side branch episode.',
       chapters=[(0,'The Left Entrance','LEFT DOOR','Cross episode branch',''),(28,'A Clue','SECRET','The left password','LANTERN'),(60,'End','END','Return to the fork','')],
       speech=[(1,'B','You chose the left branch. The recording remembers nothing, so keep track of your own choices.'),
         (30,'B','Your hidden left-branch word is LANTERN.'),
         (61,'B','The left branch ends here.')]),
  dict(slug='branch-right',title='The Right Branch',duration=79,
       desc='Alternate destination from The Forked Transmission. Right-side branch episode.',
       chapters=[(0,'The Right Entrance','RIGHT DOOR','Cross episode branch',''),(28,'A Clue','SECRET','The right password','COMPASS'),(64,'End','END','Return to the fork','')],
       speech=[(1,'B','You chose the right branch. You can switch to this episode through a description link.'),
         (30,'B','Your hidden right-branch word is COMPASS.'),
         (65,'B','The right branch ends here.')]),
  dict(slug='link-diagnostics',title='Link and Timestamp Diagnostics',duration=101,
       desc='Extra iOS 18 diagnostic episode: test several timestamp spellings in the notes below. Use the native chapter menu as the known-good control. An opening raw RSS page is a failure, not a successful seek.',
       chapters=[(0,'Control','CONTROL','Native chapters already work',''),
         (16,'Test A','A','Full HH MM SS format',''),
         (32,'Test B','B','Short MM SS format',''),
         (48,'Test C','C','Single digit minute',''),
         (64,'Test D','D','Another timestamp',''),
         (80,'Test E','E','Last format',''),
         (96,'Result','RESULT','What happened?','')],
       speech=[(1,'B','Welcome to a diagnostic episode for the iOS eighteen Apple Podcasts app. The native chapter menu works. We are testing whether show notes can seek to the same positions.'),
         (17,'B','This is target A. Its timestamp has hours, minutes, and seconds.'),
         (33,'B','This is target B. Its timestamp has two digits for minutes and seconds.'),
         (49,'B','This is target C. Its timestamp has a single digit minute.'),
         (65,'B','This is target D. Try the linked timestamp in the episode description.'),
         (81,'B','This is target E. Compare all formats, and report whether tapping seeks inside Podcasts or opens a website.'),
         (97,'B','End of the test.')])
]

def fmt(t):
    m=int(t//60);sec=t-m*60
    return f'{m:02d}:{sec:06.3f}' if sec%1 else f'{m:02d}:{int(sec):02d}'

def stamp(t):return f'{int(t//3600):02d}:{int(t//60)%60:02d}:{t%60:06.3f}'

def add_tag(parent,name,value):
    e=ET.SubElement(parent,name);e.text=str(value);return e

def main():
    ns={'itunes':'http://www.itunes.com/dtds/podcast-1.0.dtd',
        'atom':'http://www.w3.org/2005/Atom',
        'podcast':'https://podcastindex.org/namespace/1.0'}
    for k,v in ns.items():ET.register_namespace(k,v)
    it=lambda x:'{'+ns['itunes']+'}'+x
    pod=lambda x:'{'+ns['podcast']+'}'+x
    rss=ET.Element('rss',{'version':'2.0'})
    chan=ET.SubElement(rss,'channel')
    add_tag(chan,'title','Play by Ear - iOS 18 Test Laboratory')
    add_tag(chan,'description','Original games and audio mechanics testing in Apple Podcasts on iOS 18. Includes stereo, chapter images, metadata and branching experiments.')
    add_tag(chan,'link',BASE)
    add_tag(chan,'language','en-us')
    add_tag(chan,'copyright','2026 Play by Ear: original test recordings')
    add_tag(chan,'generator','Play by Ear GitHub Actions audio lab')
    add_tag(chan,it('author'),'Play by Ear')
    add_tag(chan,it('type'),'serial')
    add_tag(chan,it('explicit'),'false')
    ET.SubElement(chan,it('image'),{'href':BASE+'art/lab-three-channels-cover.jpg'})
    ET.SubElement(chan,it('category'),{'text':'Games & Hobbies'})
    ET.SubElement(chan,'{'+ns['atom']+'}link',{'href':BASE+'feed.xml','rel':'self','type':'application/rss+xml'})
    epoch=datetime(2026,10,11,12,0,tzinfo=timezone.utc)
    for ix,ep in enumerate(episodes,1):
        slug=ep['slug']; title=ep['title']; duration=ep['duration']
        cover=img(slug+'-cover',title,'PLAY BY EAR  /  TEST '+str(ix),frame=ix)
        mp3=audio(slug,duration,ep['speech'])
        chapter_list=[]
        id3=ID3(mp3)
        id3.add(TIT2(encoding=3,text=title))
        id3.add(TALB(encoding=3,text='Play by Ear - iOS 18 Test Laboratory'))
        id3.add(TPE1(encoding=3,text='Play by Ear'))
        id3.add(TCON(encoding=3,text='Games & Hobbies'))
        id3.add(TDRC(encoding=3,text='2026'))
        id3.add(TRCK(encoding=3,text=str(ix)))
        id3.add(TPOS(encoding=3,text='1'))
        id3.add(TLEN(encoding=3,text=str(duration*1000)))
        id3.add(COMM(encoding=3,lang='eng',desc='Hidden Message',text='MERIDIAN'))
        id3.add(TXXX(encoding=3,desc='PLAY_BY_EAR_SECRET',text='ID3_CUSTOM_FIELD_913'))
        id3.add(APIC(encoding=3,mime='image/jpeg',type=3,desc='Episode Cover',data=cover.read_bytes()))
        elemids=[]
        for j,(start,chapter_title,headline,subtitle,secret) in enumerate(ep['chapters']):
            end=ep['chapters'][j+1][0] if j+1<len(ep['chapters']) else duration
            cid='ch'+str(j).zfill(3)
            art=img(slug+'-'+str(j).zfill(2),headline,subtitle,secret,frame=j,qr=slug=='lab-three-channels' and j==4)
            item={'startTime':start,'title':chapter_title,'img':BASE+'art/'+art.name,'url':BASE+slug+'.html'}
            chapter_list.append(item)
            frames=[TIT2(encoding=3,text=chapter_title),APIC(encoding=3,mime='image/jpeg',type=3,desc='Chapter Artwork',data=art.read_bytes())]
            id3.add(CHAP(element_id=cid,start_time=round(start*1000),end_time=round(end*1000),start_offset=0xFFFFFFFF,end_offset=0xFFFFFFFF,sub_frames=frames))
            elemids.append(cid)
        id3.add(CTOC(element_id='toc',flags=3,child_element_ids=elemids,sub_frames=[TIT2(encoding=3,text='Play by Ear Chapters')]))
        id3.save(mp3,v2_version=3)
        (SITE/'chapters'/f'{slug}.json').write_text(json.dumps({'version':'1.2.0','chapters':chapter_list},indent=2)+'\n')
        transcript=['WEBVTT','']
        for ti,(at,ch,s) in enumerate(ep['speech']):
            end=min(duration, at+max(3,min(12,len(s)/12)))
            transcript.extend([stamp(at)+' --> '+stamp(end),f'<v { {"L":"Left","R":"Right","B":"Narrator"}[ch] }>'+s+'</v>',''])
        (SITE/'transcripts'/f'{slug}.vtt').write_text('\n'.join(transcript))
        item=ET.SubElement(chan,'item')
        add_tag(item,'title',title)
        add_tag(item,'guid','play-by-ear-ios18-'+slug+'-2026-v2')
        add_tag(item,'pubDate',format_datetime(epoch+timedelta(minutes=ix)))
        add_tag(item,it('author'),'Play by Ear')
        add_tag(item,it('explicit'),'false')
        add_tag(item,it('season'),'1')
        add_tag(item,it('episode'),str(ix))
        add_tag(item,it('episodeType'),'bonus' if ix>=4 else 'full')
        add_tag(item,it('duration'),str(duration))
        ET.SubElement(item,it('image'),{'href':BASE+'art/'+cover.name})
        add_tag(item,'link',BASE+slug+'.html')
        links=f'<p><a href="{BASE+slug+".html"}">Open this episode page</a></p>'
        if slug=='forked-transmission':
            # Directly subscribed RSS episodes do not have catalog episode IDs,
            # so these cannot be reliable in-app deep links on iOS 18.
            links+='<p>To stay in Apple Podcasts: tap the show name, then open the episode named The Left Branch or The Right Branch.</p>'
            links+=f'<p>Optional WEB previews (leave Podcasts): <a href="{BASE}branch-left.html">Left branch webpage</a> or <a href="{BASE}branch-right.html">Right branch webpage</a></p>'
        # On iOS 18.7.10, auto-linked MM:SS show-note timestamps in this directly
        # subscribed RSS feed opened the raw feed XML rather than seeking audio.
        # The real MP3 CHAP chapters work, including their art, so do not publish
        # misleading pseudo-navigation links beside them. List titles only.
        timing='<p>To jump to a chapter: open Now Playing, tap the chapter/list button, and select a chapter. The chapter menu is the working navigation method on iOS 18.</p><ul>'+''.join(f'<li>Chapter {j+1}: {escape(ch[1])}</li>' for j,ch in enumerate(ep['chapters']))+'</ul>'
        if slug=='link-diagnostics':
            # Controlled A/B test for iOS 18 automatic seek parsing. Five
            # variants link to real targets in the same MP3; the native chapter
            # metadata remains the reliable control. This deliberately restores
            # timestamps in ONE episode rather than breaking every show note.
            timing='<p>Tap each candidate below. SUCCESS = Apple Podcasts seeks in this episode. FAILURE = the raw RSS feed or a browser opens.</p>'+(
                '<ul><li>A at 00:00:16 (HH:MM:SS)</li>'
                '<li>B at 00:32 (MM:SS)</li>'
                '<li>C at 0:48 (M:SS)</li>'
                '<li>D at 01:04 (MM:SS)</li>'
                '<li>E at 00:01:20 (HH:MM:SS)</li></ul>'
                '<p>Control: use the player chapter menu to open Test A through Test E. Those are embedded ID3 chapters.</p>')

        add_tag(item,'description',ep['desc']+'\n'+links+timing)
        ET.SubElement(item,'enclosure',{'url':BASE+'media/'+mp3.name,'length':str(mp3.stat().st_size),'type':'audio/mpeg'})
        ET.SubElement(item,pod('chapters'),{'url':BASE+'chapters/'+slug+'.json','type':'application/json+chapters'})
        ET.SubElement(item,pod('transcript'),{'url':BASE+'transcripts/'+slug+'.vtt','type':'text/vtt','language':'en'})
        (SITE/f'{slug}.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+escape(title)+'</title><h1>'+escape(title)+'</h1><p>'+escape(ep['desc'])+'</p><p><a href="feed.xml">Follow RSS feed</a> | <a href="index.html">All episodes</a></p><audio controls preload="metadata" src="media/'+mp3.name+'"></audio><h2>Chapter art</h2>'+''.join('<figure><img loading="lazy" width="250" src="art/'+slug+'-'+str(j).zfill(2)+'.jpg"><figcaption>'+fmt(ch[0])+' '+escape(ch[1])+'</figcaption></figure>' for j,ch in enumerate(ep['chapters']))+ ('<p><a href="branch-left.html">LEFT branch</a> / <a href="branch-right.html">RIGHT branch</a></p>' if slug=='forked-transmission' else '')+'</html>')
        print(title,'size',mp3.stat().st_size,'chapters',len(chapter_list))
    ET.indent(rss,space='  ')
    # Apple recommends CDATA for descriptions containing HTML/links. The
    # previous ElementTree serialization escaped literal <a> tags to &lt;a>.
    # Some clients tolerated it, but use actual CDATA to avoid ambiguities.
    raw_xml=ET.tostring(rss,encoding='unicode')
    def as_cdata(match):
        body=unescape(match.group(1)).replace(']]>',']]]]><![CDATA[>')
        return '<description><![CDATA['+body+']]></description>'
    raw_xml=re.sub(r'<description>(.*?)</description>',as_cdata,raw_xml,flags=re.DOTALL)
    (SITE/'feed.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'+raw_xml,encoding='utf-8')
    (SITE/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Play by Ear: iOS 18 Lab</title><h1>Play by Ear: iOS 18 Test Laboratory</h1><p><a href="feed.xml">RSS feed for Apple Podcasts</a></p><ol>'+''.join('<li><a href="'+ep['slug']+'.html">'+escape(ep['title'])+'</a></li>' for ep in episodes)+'</ol><p>Play the feed in Apple Podcasts on iOS 18 to test native chapter artwork and navigation.</p></html>')
    (SITE/'.nojekyll').write_text('')
    print('DONE',SITE/'feed.xml')

if __name__=='__main__':main()
