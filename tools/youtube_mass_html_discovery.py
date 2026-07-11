#!/usr/bin/env python3
from __future__ import annotations

import html, json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

NAMES = [
'Nix','Dread','SilverName','Recrent','StRoGo','Buster','Evelone','Bratishkin','Tenderlybae','Mokrivskiy','Shadowkek','Zloy','Kamazz','Rostik','skywhywalker','Mellstroy','Exile','Sasavot','Mazellov','T2x2','Stint','Papich','Arthas','Bebey','Zubarev','Frost','Solek','Kuertov','Koresh','Paradeevich','Hazyaeva','Bad Guy','Плохой парень','Eastercake','Nixan','Aunkere','m0nesy','donk','buster cs','ceh9','shoke','unlost','Dota NS','Alohadance','Stray228','Dyrachyo','Yatoro','RAMZES','Solo dota','Iceberg dota','Nix dota','Dread dota','SilverName hearthstone','Recrent valorant','Shadowkek cs2','Evelone cs2','Buster minecraft','Bratishkin minecraft','Tenderlybae minecraft','Mokrivskiy twitch','Freak Squad','Hesus','JesusAVGN','Windy31','Pyaterka','Genсуха','Lavellas','Dmitry Lixxx','Hard Play','Kuplinov','Marmok','Bulkin','FixPlay','EdisonPts','Nerkin','Zakviel','Sleduck','Rera seal','vtuber русский','Dota streamer русский','CS2 streamer русский','Rust streamer русский','GTA RP streamer русский','Minecraft streamer русский','Valorant streamer русский','Warface streamer русский'
]
QUERIES=[]
for n in NAMES:
    QUERIES += [f'{n} нарезки shorts', f'{n} моменты shorts', f'{n} рофлы shorts']
QUERIES += [
'стример сверху игра снизу shorts русский','лицо сверху minecraft снизу shorts русский','facecam cs2 shorts русский','подкаст сверху minecraft снизу shorts русский','интервью сверху gameplay снизу shorts','реакция сверху игра снизу shorts русский','нарезки twitch с субтитрами shorts русский','лучшие моменты стримеров shorts русский','рофлы стримеров gameplay shorts','человек сверху roblox снизу shorts','говорящая голова minecraft parkour shorts русский','истории из жизни minecraft parkour shorts русский','мужская психология gameplay shorts русский','девушка сверху subway surfers снизу shorts русский','подкаст нарезки subway surfers shorts русский','видео сверху игра снизу субтитры shorts русский','двойной экран streamer shorts русский','стримерские новости gameplay shorts русский','vtuber clips русский shorts','нарезки витуберов русский shorts'
]
QUERIES=list(dict.fromkeys(QUERIES))

OUT=Path('mass_html_discovery'); GRID=OUT/'grids'; GRID.mkdir(parents=True,exist_ok=True)
HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9,en;q=0.5'}
S=requests.Session(); S.headers.update(HEADERS)


def parse_initial(raw):
    for pat in [r'var ytInitialData = (\{.*?\});</script>',r'ytInitialData"\s*:\s*(\{.*?\})\s*,\s*"ytInitialPlayerResponse']:
        m=re.search(pat,raw)
        if m:
            try:return json.loads(m.group(1))
            except Exception:pass
    return None

def text_of(obj):
    if not isinstance(obj,dict):return ''
    if obj.get('simpleText'):return obj['simpleText']
    return ''.join(x.get('text','') for x in obj.get('runs') or [])

def search_one(q):
    try:r=S.get('https://www.youtube.com/results?search_query='+quote(q)+'&hl=ru&gl=RU',timeout=45)
    except Exception:return []
    d=parse_initial(r.text); rows=[]
    if not d:return rows
    def walk(x):
        if isinstance(x,dict):
            v=x.get('videoRenderer')
            if isinstance(v,dict):
                owner=v.get('ownerText',{}).get('runs') or v.get('shortBylineText',{}).get('runs') or []
                if owner:
                    cid=owner[0].get('navigationEndpoint',{}).get('browseEndpoint',{}).get('browseId','')
                    if cid.startswith('UC'):
                        rows.append({'query':q,'video_id':v.get('videoId',''),'video_title':text_of(v.get('title',{})),'channel_id':cid,'channel':owner[0].get('text','')})
            for y in x.values():walk(y)
        elif isinstance(x,list):
            for y in x:walk(y)
    walk(d)
    return rows[:30]

def norm(raw):
    x=raw
    for _ in range(4):x=html.unescape(x).replace('\\u0026','&').replace('\\/','/'); x=unquote(x)
    return x

def parse_num(t):
    if not t:return None
    s=t.lower().replace('\xa0',' ').replace(' ','').replace(',','.').replace('подписчиков','').replace('подписчика','').replace('подписчик','').replace('subscribers','').strip()
    mult=1
    if 'млн' in s or s.endswith('m'):mult=1_000_000
    elif 'тыс' in s or s.endswith('k'):mult=1_000
    s=re.sub(r'[^0-9.]','',s)
    try:return int(float(s)*mult)
    except:return None

def subscriber_count(raw):
    pats=[r'"subscriberCountText":\{"simpleText":"([^"]+)"',r'"subscriberCountText":\{"accessibility".*?"simpleText":"([^"]+)"',r'"subscriberCountText":\{"runs":\[\{"text":"([^"]+)"']
    vals=[]
    for p in pats:
        for t in re.findall(p,raw):
            n=parse_num(t)
            if n is not None:vals.append(n)
    return vals[0] if vals else None

def expand_urls(raw):
    raw=norm(raw); vals=[]
    for u in re.findall(r'https?://[^"\\\s<>]+',raw,re.I):
        u=u.rstrip('.,;\"\'\])}')
        vals.append(u)
        try:
            qs=parse_qs(urlparse(u).query)
            for k in ('q','url','u'):
                vals += [unquote(v) for v in qs.get(k,[])]
        except:pass
    for user in re.findall(r'(?i)(?:telegram|телеграм|тг|tg|связь|реклама|сотрудничество)[^@\n]{0,90}@([A-Za-z0-9_]{5,32})',raw):
        vals.append('https://t.me/'+user)
    return list(dict.fromkeys(vals))

def direct_candidate(u):
    try:p=urlparse(u); host=p.netloc.lower().replace('www.',''); path=p.path.strip('/'); low=path.lower()
    except:return False
    if host in ('t.me','telegram.me'):
        return path and '/' not in path and not low.startswith(('+','joinchat','s/','share','proxy')) and not low.endswith('bot')
    if host=='vk.com':
        return path and '/' not in path and not low.startswith(('club','public','event','wall','video','clip','market','im'))
    return False

def verify_tg(u):
    try:
        r=S.get(u,timeout=25); raw=r.text; low=raw.lower()
        title='';desc=''
        mt=re.search(r'<meta property="og:title" content="([^"]*)"',raw); md=re.search(r'<meta property="og:description" content="([^"]*)"',raw)
        if mt:title=html.unescape(mt.group(1))
        if md:desc=html.unescape(md.group(1))
        if re.search(r'\b[0-9][0-9\s,.]*(subscribers|members|подписчик|участник)',title+' '+desc,flags=re.I) or 'tgme_page_extra' in raw and ('subscribers' in low or 'members' in low):
            return {'url':u,'kind':'CHANNEL_OR_GROUP','title':title,'description':desc}
        if 'you can contact @' in low or title.lower().startswith('telegram: contact @') or ('tgme_page_action' in raw and 'send message' in low):
            return {'url':u,'kind':'PERSONAL','title':title,'description':desc}
        return {'url':u,'kind':'UNCLEAR','title':title,'description':desc}
    except Exception as e:return {'url':u,'kind':'ERROR','error':repr(e)}

def channel_data(cid,title):
    texts=[]
    for suf in ('shorts','about',''):
        try:
            r=S.get(f'https://www.youtube.com/channel/{cid}/{suf}?hl=ru&gl=RU',timeout=40)
            if r.ok:texts.append(r.text)
        except:pass
    raw='\n'.join(texts); decoded=norm(raw)
    subs=subscriber_count(raw)
    ids=[]
    for pat in [r'"entityId":"shorts-shelf-item-([A-Za-z0-9_-]{11})"',r'"videoId":"([A-Za-z0-9_-]{11})"']:
        for v in re.findall(pat,raw):
            if v not in ids:ids.append(v)
    candidates=[u for u in expand_urls(decoded) if direct_candidate(u)]
    checked=[]
    for u in candidates[:12]:
        if 't.me' in u or 'telegram.me' in u:checked.append(verify_tg(u))
        else:checked.append({'url':u,'kind':'VK_CANDIDATE'})
    personal=[x for x in checked if x.get('kind') in ('PERSONAL','VK_CANDIDATE')]
    return {'channel_id':cid,'title':title,'subs':subs,'short_ids':ids[:15],'contacts_checked':checked,'personal_contacts':personal}

def img(vid):
    for n in ('oardefault.jpg','oar2.jpg','maxresdefault.jpg','hq720.jpg','hqdefault.jpg'):
        try:
            r=S.get(f'https://i.ytimg.com/vi/{vid}/{n}',timeout=20)
            if r.ok and len(r.content)>3000:
                im=Image.open(BytesIO(r.content)).convert('RGB')
                if im.width>100 and im.height>100:return im
        except:pass
    return None

def safe(s):return re.sub(r'[^A-Za-zА-Яа-я0-9_-]+','_',s).strip('_')[:65]
def grid(row):
    cw,ch=250,460; can=Image.new('RGB',(cw*5,ch*3+90),'white');d=ImageDraw.Draw(can);f=ImageFont.load_default()
    d.text((8,7),f"{row['title']} | {row['subs']} | {row['channel_id']}",fill='black',font=f)
    d.text((8,27),'contacts: '+'; '.join(x['url'] for x in row['personal_contacts']),fill='black',font=f)
    for i,v in enumerate(row['short_ids'][:15]):
        x=(i%5)*cw;y=65+(i//5)*ch; im=img(v)
        if im:
            im=ImageOps.fit(im,(cw-6,ch-35),method=Image.Resampling.LANCZOS);can.paste(im,(x+3,y+3))
        d.text((x+4,y+ch-27),v,fill='black',font=f)
    p=GRID/f"{safe(row['title'])}_{row['channel_id']}.jpg";can.save(p,quality=88);return str(p)

allrows=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    fs={ex.submit(search_one,q):q for q in QUERIES}
    for i,f in enumerate(as_completed(fs),1):
        try:r=f.result()
        except Exception:r=[]
        allrows.extend(r)
        if i%20==0:print('search',i,len(QUERIES),'rows',len(allrows),flush=True)
by={}
for r in allrows:
    x=by.setdefault(r['channel_id'],{'channel_id':r['channel_id'],'title':r['channel'],'queries':[],'samples':[]})
    if r['query'] not in x['queries']:x['queries'].append(r['query'])
    if r['video_id'] and len(x['samples'])<8:x['samples'].append({'video_id':r['video_id'],'title':r['video_title']})
print('unique channels',len(by),flush=True)
rows=[]
with ThreadPoolExecutor(max_workers=10) as ex:
    fs={ex.submit(channel_data,cid,x['title']):cid for cid,x in by.items()}
    for i,f in enumerate(as_completed(fs),1):
        try:r=f.result()
        except Exception as e:r={'channel_id':fs[f],'title':by[fs[f]]['title'],'error':repr(e),'subs':None,'personal_contacts':[],'short_ids':[]}
        r['queries']=by[fs[f]]['queries'];r['samples']=by[fs[f]]['samples'];rows.append(r)
        if i%50==0:print('channels',i,len(by),flush=True)
eligible=[r for r in rows if r.get('subs') is not None and 5000<=r['subs']<=50000 and r.get('personal_contacts') and len(r.get('short_ids') or [])>=10]
print('eligible previsual',len(eligible),flush=True)
with ThreadPoolExecutor(max_workers=6) as ex:
    fs={ex.submit(grid,r):r for r in eligible}
    for f,r in [(f,fs[f]) for f in as_completed(fs)]:
        try:r['grid']=f.result()
        except Exception as e:r['grid_error']=repr(e)
(OUT/'all_search_rows.json').write_text(json.dumps(allrows,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'all_channels.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'eligible.json').write_text(json.dumps(eligible,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'queries':len(QUERIES),'search_rows':len(allrows),'channels':len(by),'eligible':len(eligible)},ensure_ascii=False))
