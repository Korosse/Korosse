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

OUT = Path('final_verify_output')
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

S = requests.Session()
S.headers.update({
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36',
    'Accept-Language':'ru-RU,ru;q=0.9,en;q=0.5',
})
S.cookies.set('CONSENT','YES+cb.20210328-17-p0.en+FX+667')
VPN_RE = re.compile(r'\b(vpn|впн|proxy|прокси|vless|xray|outline|amnezia|warp|обход блокиров|промокод)\b',re.I)


def ydl_opts():
    return {'quiet':True,'no_warnings':True,'skip_download':True,'ignoreerrors':True,'extract_flat':'in_playlist','playlistend':15,'retries':2,'socket_timeout':20,'http_headers':{'Accept-Language':'ru-RU,ru;q=0.9'}}


def channel_flat(cid):
    with YoutubeDL(ydl_opts()) as y:
        p=y.extract_info(f'https://www.youtube.com/channel/{cid}/shorts',download=False) or {}
    ids=[e.get('id') for e in (p.get('entries') or []) if e and e.get('id')][:15]
    return p,ids


def balanced_json(text,start):
    i=text.find('{',start)
    if i<0:return None
    depth=0;ins=False;esc=False
    for j in range(i,len(text)):
        c=text[j]
        if ins:
            if esc:esc=False
            elif c=='\\':esc=True
            elif c=='"':ins=False
        else:
            if c=='"':ins=True
            elif c=='{':depth+=1
            elif c=='}':
                depth-=1
                if depth==0:
                    try:return json.loads(text[i:j+1])
                    except:return None
    return None


def regex_json_string(text,key):
    m=re.search(r'"'+re.escape(key)+r'"\s*:\s*"((?:\\.|[^"\\])*)"',text)
    if not m:return None
    try:return json.loads('"'+m.group(1)+'"')
    except:return m.group(1)


def parse_views(s):
    if not s:return 0
    s=s.replace('\u00a0',' ').replace('\xa0',' ').lower()
    nums=re.findall(r'[\d\s.,]+',s)
    if not nums:return 0
    raw=nums[0].strip().replace(' ','').replace(',','.')
    try:n=float(raw)
    except:return 0
    if 'млн' in s or 'million' in s:n*=1_000_000
    elif 'тыс' in s or 'k ' in s:n*=1_000
    return int(n)


def age_days(s):
    if not s:return None
    t=s.lower().replace('\u00a0',' ')
    if any(x in t for x in ['минут','час','сегодня','только что']):return 0
    m=re.search(r'(\d+)\s*(день|дня|дней|day)',t)
    if m:return int(m.group(1))
    m=re.search(r'(\d+)\s*(недел|week)',t)
    if m:return int(m.group(1))*7
    m=re.search(r'(\d+)\s*(месяц|месяца|месяцев|month)',t)
    if m:return int(m.group(1))*30
    m=re.search(r'(\d+)\s*(год|года|лет|year)',t)
    if m:return int(m.group(1))*365
    if 'вчера' in t:return 1
    return None


def parse_video(vid):
    r=S.get(f'https://www.youtube.com/watch?v={vid}&hl=ru&gl=RU',timeout=25)
    t=r.text
    title='';views=0;age_text='';days=None;duration=0;publish=None;desc=''
    marker='"playerOverlayVideoDetailsRenderer":'
    pos=t.find(marker)
    if pos>=0:
        obj=balanced_json(t,pos+len(marker)) or {}
        title=((obj.get('title') or {}).get('simpleText') or '')
        runs=((obj.get('subtitle') or {}).get('runs') or [])
        texts=[str(x.get('text') or '') for x in runs]
        if len(texts)>=5:
            views=parse_views(texts[2]);age_text=texts[4];days=age_days(age_text)
        else:
            joined=' | '.join(texts)
            for x in texts:
                if 'просмотр' in x.lower() or re.search(r'\d',x):
                    pv=parse_views(x)
                    if pv>views:views=pv
                ad=age_days(x)
                if ad is not None:days=ad;age_text=x
    # Exact videoDetails and microformat fallback
    p2=t.find('"videoDetails":{"videoId":"'+vid+'"')
    if p2>=0:
        obj2=balanced_json(t,p2+len('"videoDetails":')) or {}
        title=obj2.get('title') or title
        desc=obj2.get('shortDescription') or ''
        try:duration=int(obj2.get('lengthSeconds') or 0)
        except:duration=0
        try:views=max(views,int(obj2.get('viewCount') or 0))
        except:pass
    for key in ['publishDate','uploadDate']:
        val=regex_json_string(t,key)
        if val:
            publish=val;break
    if publish:
        try:
            dt=datetime.fromisoformat(publish.replace('Z','+00:00'))
            if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
            days=max(0,(datetime.now(timezone.utc)-dt.astimezone(timezone.utc)).days)
        except:pass
    if not title:
        title=regex_json_string(t,'title') or ''
    if not desc:
        desc=regex_json_string(t,'shortDescription') or ''
    # RYD view fallback
    if not views:
        try:
            rr=S.get('https://returnyoutubedislikeapi.com/votes?videoId='+vid,timeout=15)
            if rr.status_code==200:views=int((rr.json() or {}).get('viewCount') or 0)
        except:pass
    return {'id':vid,'title':title,'views':views,'age_text':age_text,'age_days':days,'duration':duration,'publish_date':publish,'description':desc[:2500],'vpn_text':bool(VPN_RE.search(title+'\n'+desc)),'http_status':r.status_code,'html_len':len(t)}


def contact_class(url):
    if not url:return {'class':'missing'}
    try:r=S.get(url,timeout=20);t=r.text
    except Exception as e:return {'class':'error','error':type(e).__name__}
    plain=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',t)))
    title='';desc=''
    m=re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)',t,re.I)
    if m:title=html.unescape(m.group(1))
    m=re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']*)',t,re.I)
    if m:desc=html.unescape(m.group(1))
    if 't.me/' in url:
        if re.search(r'\b(subscribers|members|подписчик|участник)\b',plain,re.I):c='telegram_channel_or_group'
        elif 'you can contact' in plain.lower() or '@' in title or 'contact' in desc.lower():c='personal_telegram'
        else:c='telegram_uncertain'
    elif 'vk.com/' in url:
        if re.search(r'сообщество|community|public page|группа',plain,re.I):c='vk_group'
        else:c='vk_profile_or_uncertain'
    else:c='other'
    return {'class':c,'status':r.status_code,'title':title,'description':desc[:500]}


def thumb(vid,path):
    for n in ('maxresdefault.jpg','sddefault.jpg','hqdefault.jpg'):
        try:
            r=S.get(f'https://i.ytimg.com/vi/{vid}/{n}',timeout=15)
            if r.status_code==200 and len(r.content)>5000:path.write_bytes(r.content);return True
        except:pass
    return False


def sheet(rec,idx):
    imgs=[]
    for j,v in enumerate(rec['videos']):
        p=OUT/f'tmp_{idx}_{j}.jpg'
        if thumb(v['id'],p):
            try:imgs.append((v,Image.open(p).convert('RGB')))
            except:pass
    if not imgs:return ''
    cw,ch=320,285
    can=Image.new('RGB',(cw*5,ch*3+120),'white');d=ImageDraw.Draw(can)
    d.text((8,8),f"{rec['channel']} | subs {rec['subscribers']} | 7d {rec['shorts_7d']} | 14d {rec['shorts_14d']} | median {rec['median_views']} | >=1500 {rec['views_ge1500']}/{rec['views_counted']}",fill='black')
    d.text((8,34),rec['channel_url'],fill='black')
    d.text((8,60),f"contact {rec['contact']} ({rec['contact_check'].get('class')})",fill='black')
    d.text((8,86),f"VPN text {rec['vpn_text_any']}",fill='black')
    for k,(v,im) in enumerate(imgs):
        x=(k%5)*cw;y=120+(k//5)*ch
        im.thumbnail((cw-8,ch-60));can.paste(im,(x+(cw-im.width)//2,y))
        d.text((x+4,y+ch-56),f"{v['age_text'] or v['publish_date'] or '?'} | {v['views']} views",fill='black')
        d.text((x+4,y+ch-38),v['id'],fill='black')
        d.text((x+4,y+ch-20),(v['title'] or '')[:48],fill='black')
    out=SHEETS/f'{idx:02d}_{re.sub(r"[^A-Za-z0-9А-Яа-я_-]+","_",rec["channel"])[:60]}.jpg';can.save(out,quality=90)
    for p in OUT.glob(f'tmp_{idx}_*.jpg'):p.unlink(missing_ok=True)
    return str(out)


def main():
    rows=[]
    for idx,(cid,info) in enumerate(TARGETS.items(),1):
        print('CHANNEL',idx,len(TARGETS),info['label'],flush=True)
        try:p,ids=channel_flat(cid)
        except Exception as e:
            rows.append({'channel_id':cid,'channel':info['label'],'error':type(e).__name__});continue
        vids=[]
        for j,vid in enumerate(ids,1):
            try:v=parse_video(vid)
            except Exception as e:v={'id':vid,'title':'','views':0,'age_text':'','age_days':None,'duration':0,'publish_date':None,'description':'','vpn_text':False,'error':type(e).__name__}
            vids.append(v);print(' VIDEO',j,len(ids),vid,v.get('age_text') or v.get('publish_date'),v.get('views'),flush=True);time.sleep(.08)
        valid=[v['views'] for v in vids if v.get('views',0)>0]
        rec={'channel_id':cid,'channel':p.get('channel') or p.get('uploader') or info['label'],'channel_url':f'https://www.youtube.com/channel/{cid}/shorts','subscribers':int(p.get('channel_follower_count') or p.get('uploader_follower_count') or 0),'description':p.get('description') or p.get('channel_description') or '',
             'shorts_7d':sum(v.get('age_days') is not None and v.get('age_days')<=7 for v in vids),'shorts_14d':sum(v.get('age_days') is not None and v.get('age_days')<=14 for v in vids),'median_views':int(statistics.median(valid)) if valid else 0,'views_ge1500':sum(x>=1500 for x in valid),'views_counted':len(valid),'min_views':min(valid) if valid else 0,'max_views':max(valid) if valid else 0,'vpn_text_any':any(v.get('vpn_text') for v in vids) or bool(VPN_RE.search(p.get('description') or '')),'contact':info.get('contact',''),'contact_check':contact_class(info.get('contact','')),'videos':vids}
        rec['sheet']=sheet(rec,idx);rows.append(rec)
        print(json.dumps({k:rec.get(k) for k in ('channel','subscribers','shorts_7d','shorts_14d','median_views','views_ge1500','views_counted','vpn_text_any')},ensure_ascii=False),flush=True)
    (OUT/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
