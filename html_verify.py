from __future__ import annotations

import html
import json
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw
from yt_dlp import YoutubeDL

OUT = Path('html_verify_output')
OUT.mkdir(exist_ok=True)
SHEETS = OUT / 'sheets'
SHEETS.mkdir(exist_ok=True)

TARGETS = {
    'UCiiqjbw9FKaVSHyE6kOncKQ': {'label':'Нарезка T2x2','contact':'https://t.me/tashini_999'},
    'UCbBUIeZzS_mOzk-sl2I0Wew': {'label':'Стинт лучшее','contact':'https://t.me/Tiveriy'},
    'UCWFet2M-JDh6XL-8RfPoFDg': {'label':'Stint Fun','contact':'https://t.me/qwastOff'},
    'UCfPJse-3skARpxs5LaSUiWA': {'label':'TWITCH НАРЕЗКИ T2X2','contact':'https://t.me/darkzz'},
    'UCm1ntxZX0XAEydR70UABOUw': {'label':'Нарезки Стинта 2','contact':'https://t.me/ra1ph_d'},
    'UCWAs-6bnfm4lvCphK68m7YQ': {'label':'T2x2 BEST','contact':'https://t.me/t2x2inside'},
    'UC8WrBIrZBZ2gaEBNILijxPQ': {'label':'T2x2 NEWS','contact':''},
    'UC3z13cV53Pk3vrZjY7LHn-w': {'label':'MazelloFFMoments','contact':''},
    'UCb-SQh-EzmM4PViGtD_42bg': {'label':'Твич моменты','contact':''},
    'UCAziG6T1Cj3zuo5mxODXrZQ': {'label':'Нарезочкин','contact':'https://vk.com/podldima'},
}

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.5',
})
SESSION.cookies.set('CONSENT', 'YES+cb.20210328-17-p0.en+FX+667')

VPN_RE = re.compile(r'\b(vpn|впн|proxy|прокси|vless|xray|outline|amnezia|warp|обход блокиров|промокод)\b', re.I)


def ydl_opts():
    return {
        'quiet': True, 'no_warnings': True, 'skip_download': True,
        'ignoreerrors': True, 'extract_flat': 'in_playlist', 'playlistend': 15,
        'retries': 2, 'socket_timeout': 20,
        'http_headers': {'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.5'},
    }


def get_channel_flat(cid: str):
    with YoutubeDL(ydl_opts()) as ydl:
        page = ydl.extract_info(f'https://www.youtube.com/channel/{cid}/shorts', download=False) or {}
    entries = [e for e in (page.get('entries') or []) if e and e.get('id')]
    return page, [e.get('id') for e in entries[:15]]


def extract_json_after(text: str, marker: str):
    i = text.find(marker)
    if i < 0:
        return None
    i = text.find('{', i + len(marker))
    if i < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for j in range(i, len(text)):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i:j+1])
                    except Exception:
                        return None
    return None


def meta_content(text: str, key: str, attr='itemprop'):
    pats = [
        rf'<meta[^>]+{attr}=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']*)',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+{attr}=["\']{re.escape(key)}["\']',
    ]
    for p in pats:
        m = re.search(p, text, re.I)
        if m:
            return html.unescape(m.group(1))
    return None


def parse_iso8601_duration(s: str | None):
    if not s:
        return None
    m = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s)
    if not m:
        return None
    h, mi, sec = [int(x or 0) for x in m.groups()]
    return h*3600 + mi*60 + sec


def get_video_meta(vid: str):
    url = f'https://www.youtube.com/shorts/{vid}?hl=ru&gl=RU'
    r = SESSION.get(url, timeout=25)
    text = r.text
    pr = extract_json_after(text, 'ytInitialPlayerResponse') or extract_json_after(text, 'var ytInitialPlayerResponse')
    title = meta_content(text, 'name')
    upload = meta_content(text, 'uploadDate')
    duration = parse_iso8601_duration(meta_content(text, 'duration'))
    views = meta_content(text, 'interactionCount')
    desc = meta_content(text, 'description') or ''
    thumb = None
    if pr:
        vd = pr.get('videoDetails') or {}
        micro = ((pr.get('microformat') or {}).get('playerMicroformatRenderer') or {})
        title = vd.get('title') or title
        desc = vd.get('shortDescription') or desc
        views = vd.get('viewCount') or views
        duration = int(vd.get('lengthSeconds') or 0) or duration
        upload = micro.get('uploadDate') or micro.get('publishDate') or upload
        thumbs = ((vd.get('thumbnail') or {}).get('thumbnails') or [])
        if thumbs:
            thumb = thumbs[-1].get('url')
    try:
        views_i = int(str(views).replace(',', '').replace(' ', '')) if views else 0
    except Exception:
        views_i = 0
    return {
        'id': vid, 'url': url, 'http_status': r.status_code, 'html_len': len(text),
        'title': title or '', 'upload_date': upload, 'duration': duration or 0,
        'views': views_i, 'description': desc[:3000], 'thumbnail': thumb,
        'vpn_text': bool(VPN_RE.search((title or '') + '\n' + desc)),
        'player_response_found': bool(pr),
    }


def download_thumb(vid: str, path: Path):
    for name in ('maxresdefault.jpg','sddefault.jpg','hqdefault.jpg'):
        try:
            rr = SESSION.get(f'https://i.ytimg.com/vi/{vid}/{name}', timeout=20)
            if rr.status_code == 200 and len(rr.content) > 5000:
                path.write_bytes(rr.content)
                return True
        except Exception:
            pass
    return False


def make_sheet(rec: dict, idx: int):
    imgs=[]
    for j,v in enumerate(rec['videos'][:15]):
        p=OUT/f'tmp_{idx}_{j}.jpg'
        if download_thumb(v['id'],p):
            try: imgs.append((v,Image.open(p).convert('RGB')))
            except Exception: pass
    if not imgs:
        return ''
    cw,ch=320,270
    canvas=Image.new('RGB',(cw*5,ch*3+110),'white')
    dr=ImageDraw.Draw(canvas)
    header=f"{rec['channel']} | {rec['subscribers']} subs | 14d:{rec['uploads_14d']} | median:{rec['median_views']} | contact:{rec['contact_class']}"
    dr.text((8,8),header[:190],fill='black')
    dr.text((8,34),rec['channel_url'],fill='black')
    dr.text((8,60),'contact: '+(rec.get('contact') or '-'),fill='black')
    dr.text((8,84),'VPN text: '+str(rec.get('vpn_text_any')),fill='black')
    for k,(v,im) in enumerate(imgs):
        x=(k%5)*cw; y=110+(k//5)*ch
        im.thumbnail((cw-8,ch-42))
        canvas.paste(im,(x+(cw-im.width)//2,y))
        caption=f"{v['upload_date'] or '?'} | {v['views']} | {v['id']}"
        dr.text((x+4,y+ch-38),caption[:48],fill='black')
        dr.text((x+4,y+ch-20),(v['title'] or '')[:48],fill='black')
    out=SHEETS/f'{idx:02d}_{re.sub(r"[^A-Za-z0-9А-Яа-я_-]+","_",rec["channel"])[:60]}.jpg'
    canvas.save(out,quality=90)
    for p in OUT.glob(f'tmp_{idx}_*.jpg'): p.unlink(missing_ok=True)
    return str(out)


def classify_contact(url: str):
    if not url:
        return {'url':'','class':'missing','status':None,'title':'','description':''}
    try:
        r=SESSION.get(url,timeout=25)
        text=r.text
    except Exception as e:
        return {'url':url,'class':'error','error':type(e).__name__}
    title=meta_content(text,'og:title','property') or ''
    desc=meta_content(text,'og:description','property') or ''
    plain=re.sub(r'<[^>]+>',' ',text)
    plain=html.unescape(re.sub(r'\s+',' ',plain))
    if 't.me/' in url:
        if re.search(r'\b(subscribers|members|подписчик|участник)\b',plain,re.I):
            cls='telegram_channel_or_group'
        elif 'you can contact' in plain.lower() or 'contact @' in (title+' '+desc).lower() or '@' in title:
            cls='personal_telegram'
        else:
            cls='telegram_uncertain'
    elif 'vk.com/' in url:
        if re.search(r'сообщество|community|public page|группа',plain,re.I): cls='vk_group'
        elif r.status_code==200: cls='vk_profile_or_uncertain'
        else: cls='vk_error'
    else:
        cls='other'
    return {'url':url,'class':cls,'status':r.status_code,'title':title,'description':desc[:500],'page_len':len(text)}


def main():
    results=[]
    now=datetime.now(timezone.utc)
    for idx,(cid,info) in enumerate(TARGETS.items(),1):
        print('CHANNEL',idx,len(TARGETS),info['label'],flush=True)
        try:
            page,ids=get_channel_flat(cid)
        except Exception as e:
            results.append({'channel_id':cid,'channel':info['label'],'error':type(e).__name__})
            continue
        vids=[]
        for j,vid in enumerate(ids,1):
            try: vm=get_video_meta(vid)
            except Exception as e: vm={'id':vid,'error':type(e).__name__,'views':0,'duration':0,'upload_date':None,'title':'','description':'','vpn_text':False}
            vids.append(vm)
            print(' VIDEO',j,len(ids),vid,vm.get('upload_date'),vm.get('views'),vm.get('http_status'),vm.get('player_response_found'),flush=True)
            time.sleep(.15)
        dates=[]
        for v in vids:
            d=v.get('upload_date')
            if d:
                try:
                    dt=datetime.fromisoformat(d.replace('Z','+00:00'))
                    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
                    dates.append(dt)
                except Exception: pass
        uploads7=sum((now-d).total_seconds()<=7*86400 for d in dates)
        uploads14=sum((now-d).total_seconds()<=14*86400 for d in dates)
        views=[v.get('views',0) for v in vids if v.get('views',0)>0]
        contact=classify_contact(info.get('contact',''))
        rec={
            'channel_id':cid,
            'channel':page.get('channel') or page.get('uploader') or info['label'],
            'channel_url':f'https://www.youtube.com/channel/{cid}/shorts',
            'subscribers':int(page.get('channel_follower_count') or page.get('uploader_follower_count') or 0),
            'description':page.get('description') or page.get('channel_description') or '',
            'uploads_7d':uploads7,'uploads_14d':uploads14,
            'median_views':int(statistics.median(views)) if views else 0,
            'views_ge_1500':sum(v>=1500 for v in views),
            'views_counted':len(views),
            'min_views':min(views) if views else 0,'max_views':max(views) if views else 0,
            'vpn_text_any':any(v.get('vpn_text') for v in vids) or bool(VPN_RE.search(page.get('description') or '')),
            'contact':info.get('contact',''),'contact_class':contact.get('class'),'contact_details':contact,
            'videos':vids,
        }
        rec['sheet']=make_sheet(rec,idx)
        results.append(rec)
        print(json.dumps({k:rec.get(k) for k in ('channel','subscribers','uploads_7d','uploads_14d','median_views','views_ge_1500','views_counted','vpn_text_any','contact_class')},ensure_ascii=False),flush=True)
    (OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    main()
