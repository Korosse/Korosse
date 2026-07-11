#!/usr/bin/env python3
from __future__ import annotations

import json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

CANDIDATES = {
    'UC0YUDNP3sMfSLXVIK1d8EOA': 'Alex Milya',
    'UC1Xrc8ziKhlB1-npGwbOdVA': 'More NateWantsToBattle',
    'UC5KD_Q_rS3lVfP_hMDZ3HwQ': 'Нарезка Папича',
    'UC5UWlmRI0FTIcoBrnLQx8Gw': 'r1kflagttv',
    'UCGla_NKMy5_m4J5d4pRmV5g': 'Денис Стоп',
    'UCH3giddBL9GGgculbNTMe5Q': 'Universe of Fame',
    'UCHcKojNUJgyBvaCHpHwlMPA': 'RoyGod',
    'UCRJEIA0IXTUwPn4aSt17Skw': 'CupOfKathi',
    'UCScadn4f1l5GsRfyZet-zAQ': 'Watermelon',
    'UCSv-XT7QgOBKIL898D8jsOw': 'Trending Truths',
    'UCTJ6iXgdWdPLcWxCGTaa0Kg': 'SleDuck Shorts',
    'UCTYqDIlPrb-GUWOohsv90nQ': 'Kt0Takoy?',
    'UCVncLhqp3y1KDhHaJh3Wrrg': 'Shp1onkA',
    'UCa4-DzRXobidyHig4xlxJrw': 'FlashMovieAI',
    'UCbY-Oi636gF_kzAs9HVyKvw': 'Belyashik',
    'UCfiloj1zXZqdnPplW2Ik2dw': 'Cobra_ClipsXx',
    'UCiR8IdaaRTEPsL4I4y6B6_g': 'URODSK Shorts',
    'UCn8B40JbXKz-oZtjOFODP8g': '89_rezki',
    'UCrMySZP0MM3WrPU_1ur8FOg': 'Animal Scroll',
}
OUT=Path('candidate_grids'); OUT.mkdir(exist_ok=True)
HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9'}
PAT=re.compile(r'"entityId":"shorts-shelf-item-([A-Za-z0-9_-]{11})"')
TG=re.compile(r'https?://(?:www\.)?(?:t\.me|telegram\.me)/[A-Za-z0-9_+./-]+',re.I)
VK=re.compile(r'https?://(?:www\.)?vk\.com/[A-Za-z0-9_.-]+',re.I)
AT=re.compile(r'(?i)(?:telegram|телеграм|тг|tg|связь|реклама)[^@\n]{0,50}@([A-Za-z0-9_]{5,32})')

def safe(s): return re.sub(r'[^A-Za-zА-Яа-я0-9_-]+','_',s).strip('_')[:70]
def personal(link):
    from urllib.parse import urlparse
    u=urlparse(link); p=u.path.strip('/'); low=p.lower()
    if not p:return False
    if 't.me' in u.netloc.lower() or 'telegram.me' in u.netloc.lower():
        return '/' not in p and not low.startswith(('+','joinchat','s/','share','proxy')) and not low.endswith('bot')
    if 'vk.com' in u.netloc.lower():
        return '/' not in p and not low.startswith(('club','public','event','wall','video','clip','market'))
    return False

def fetch_channel(cid):
    texts=[]
    for suffix in ('shorts','about'):
        try:
            r=requests.get(f'https://www.youtube.com/channel/{cid}/{suffix}?hl=ru&gl=RU',headers=HEADERS,timeout=30)
            if r.ok:texts.append(r.text)
        except Exception:pass
    raw='\n'.join(texts)
    ids=[]
    for v in PAT.findall(raw):
        if v not in ids:ids.append(v)
    contacts=[]
    decoded=raw.replace('\\u0026','&').replace('\\/','/')
    for pat in (TG,VK):
        for link in pat.findall(decoded):
            link=link.rstrip('.,;\"\'')]}')
            if personal(link) and link not in contacts: contacts.append(link)
    for user in AT.findall(decoded):
        link=f'https://t.me/{user}'
        if personal(link) and link not in contacts:contacts.append(link)
    return ids[:15],contacts

def image_for(vid):
    for name in ('oardefault.jpg','oar2.jpg','maxresdefault.jpg','hq720.jpg','hqdefault.jpg'):
        try:
            r=requests.get(f'https://i.ytimg.com/vi/{vid}/{name}',headers=HEADERS,timeout=25)
            if r.ok and len(r.content)>3000:
                im=Image.open(BytesIO(r.content)).convert('RGB')
                if im.width>100 and im.height>100:return im
        except Exception:pass
    return None

def build(cid,title):
    ids,contacts=fetch_channel(cid)
    cw,ch=300,550
    canvas=Image.new('RGB',(cw*5,ch*3+100),'white'); draw=ImageDraw.Draw(canvas); font=ImageFont.load_default()
    draw.text((10,10),f'{title} | {cid}',fill='black',font=font)
    draw.text((10,32),'contacts: '+'; '.join(contacts),fill='black',font=font)
    draw.text((10,54),f'https://www.youtube.com/channel/{cid}/shorts',fill='black',font=font)
    for i,vid in enumerate(ids):
        x=(i%5)*cw; y=80+(i//5)*ch
        im=image_for(vid)
        if im:
            im=ImageOps.fit(im,(cw-8,ch-45),method=Image.Resampling.LANCZOS)
            canvas.paste(im,(x+4,y+4))
        draw.text((x+5,y+ch-35),f'{i+1}. {vid}',fill='black',font=font)
    path=OUT/f'{safe(title)}_{cid}.jpg'; canvas.save(path,quality=91)
    return {'channel_id':cid,'title':title,'contacts':contacts,'video_ids':ids,'grid':str(path)}

rows=[]
with ThreadPoolExecutor(max_workers=8) as ex:
    fs={ex.submit(build,cid,title):cid for cid,title in CANDIDATES.items()}
    for i,f in enumerate(as_completed(fs),1):
        try:r=f.result()
        except Exception as e:r={'channel_id':fs[f],'error':repr(e)}
        rows.append(r); print(i,len(CANDIDATES),r.get('title'),len(r.get('video_ids') or []),r.get('contacts'),flush=True)
(OUT/'candidate_info.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
