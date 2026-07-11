#!/usr/bin/env python3
from __future__ import annotations
import json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import requests
TARGETS='''UCChoJxse7Y8672wj5R3Vr-Q UCAu8UsUlABD-5nryI_mdRRg UC30WSEdcbNHcWGjdqNhCYLA UC2vwZBZMEZ3lTseOy_LKuIQ UCLkxOn4ELqcDlFjgsM_FT1w UCSCXQojcJl5XZMZ8us9hozQ UCOzdgAxhiNLZYy4fAu2V-8g UCYr-V8i1vqeb7U0OsCelIyw UCX7qCptH7lyblq5lLe7VJ3w UCZA_cZQcC6v4yNvdOjEMWFw UCQJ0MdZdhp-KeDNV8SkuvVg UC_AIgu2H9IRPArBWpsuy8xQ UCTmByGdvAWmhTtqSlxPMH2A UCxcLssL-MSdTHpyBD5oB7GA UCkn_NmK7vlxKrkK_HVcQwMA UCdyFrvlqzKkhXJo6GdZyL5w UCfMji4nqhjDfVbBAHauiUtw UCii4eZm84XkoHhp99Ptihqw UCgwAlpRvfeBr2BqC2D06C4w UCoRoZAlBD3FaCIVAC8CXjLA UCcmUV8J69s0yR2SgkVT98pg UCzMmxpbT9MF6N62LSivy2rg'''.split()
OUT=Path('expansion_ids_output');OUT.mkdir(exist_ok=True)
HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9'}
PAT=re.compile(r'"entityId":"shorts-shelf-item-([A-Za-z0-9_-]{11})"')
TITLE=re.compile(r'<meta property="og:title" content="([^"]+)')
def one(cid):
 r=requests.get(f'https://www.youtube.com/channel/{cid}/shorts?hl=ru&gl=RU',headers=HEADERS,timeout=30);raw=r.text if r.ok else ''
 ids=[]
 for v in PAT.findall(raw):
  if v not in ids:ids.append(v)
 m=TITLE.search(raw)
 return {'channel_id':cid,'title':m.group(1) if m else cid,'status':r.status_code,'video_ids':ids[:25]}
rows=[]
with ThreadPoolExecutor(max_workers=12) as ex:
 fs={ex.submit(one,c):c for c in TARGETS}
 for i,f in enumerate(as_completed(fs),1):
  try:r=f.result()
  except Exception as e:r={'channel_id':fs[f],'status':'ERROR','error':repr(e),'video_ids':[]}
  rows.append(r);print(i,len(TARGETS),r.get('title'),len(r.get('video_ids') or []),flush=True)
rows.sort(key=lambda r:r['channel_id'])
(OUT/'expansion_ids.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'channels':len(rows),'with_ids':sum(bool(r.get('video_ids')) for r in rows),'ids':sum(len(r.get('video_ids') or []) for r in rows)}))
