#!/usr/bin/env python3
from __future__ import annotations
import json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from io import BytesIO
from pathlib import Path
import requests
from PIL import Image,ImageDraw,ImageFont,ImageOps
import youtube_channel_research_v2 as c
CANDIDATES={'UC30WSEdcbNHcWGjdqNhCYLA':'Sledovatel Shorts','UCcmUV8J69s0yR2SgkVT98pg':'SleDak | Нарезки Sleduck','UCii4eZm84XkoHhp99Ptihqw':'Sleduck shorts'}
OUT=Path('sleduck_grids');OUT.mkdir(exist_ok=True)
HEADERS=c.HEADERS
PAT=re.compile(r'"entityId":"shorts-shelf-item-([A-Za-z0-9_-]{11})"')
def thumb(vid):
 for n in ('oardefault.jpg','oar2.jpg','maxresdefault.jpg','hq720.jpg','hqdefault.jpg'):
  try:
   r=requests.get(f'https://i.ytimg.com/vi/{vid}/{n}',headers=HEADERS,timeout=25)
   if r.ok and len(r.content)>3000:
    im=Image.open(BytesIO(r.content)).convert('RGB')
    if im.width>100:return im
  except Exception:pass
 return None
def build(cid,title):
 p=c.fetch_channel(cid);ids=p.get('video_ids') or []
 if len(ids)<10:
  raw=requests.get(f'https://www.youtube.com/channel/{cid}/shorts?hl=ru&gl=RU',headers=HEADERS,timeout=30).text
  ids=[]
  for v in PAT.findall(raw):
   if v not in ids:ids.append(v)
 ids=ids[:15];cw,ch=300,550
 canvas=Image.new('RGB',(cw*5,ch*3+100),'white');d=ImageDraw.Draw(canvas);font=ImageFont.load_default()
 d.text((10,10),f'{title} | {cid}',fill='black',font=font);d.text((10,32),'contacts: '+'; '.join(p.get('contacts') or []),fill='black',font=font)
 for i,vid in enumerate(ids):
  x=(i%5)*cw;y=80+(i//5)*ch;im=thumb(vid)
  if im:
   im=ImageOps.fit(im,(cw-8,ch-45),method=Image.Resampling.LANCZOS);canvas.paste(im,(x+4,y+4))
  d.text((x+5,y+ch-35),f'{i+1}. {vid}',fill='black',font=font)
 path=OUT/(re.sub(r'[^A-Za-zА-Яа-я0-9_-]+','_',title)+'_'+cid+'.jpg');canvas.save(path,quality=91)
 return {'channel_id':cid,'title':title,'contacts':p.get('contacts') or [],'video_ids':ids,'grid':str(path)}
rows=[]
with ThreadPoolExecutor(max_workers=3) as ex:
 fs={ex.submit(build,cid,title):cid for cid,title in CANDIDATES.items()}
 for f in as_completed(fs):
  try:r=f.result()
  except Exception as e:r={'channel_id':fs[f],'error':repr(e)}
  rows.append(r);print(r,flush=True)
(OUT/'info.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
