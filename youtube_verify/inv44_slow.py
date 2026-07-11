from __future__ import annotations
import json,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'inv44_slow_output';OUT.mkdir(parents=True,exist_ok=True)
ids=[x.strip() for x in (ROOT/'base44.txt').read_text().splitlines() if x.strip()]
instances=['https://inv.zoomerville.com','https://invidious.f5.si','https://inv.nadeko.net']
s=requests.Session();s.headers.update({'User-Agent':'Mozilla/5.0 Chrome/130 Safari/537.36','Accept':'application/json'})
out={}
for i,cid in enumerate(ids,1):
 best=None
 for attempt in range(4):
  for inst in instances:
   try:
    r=s.get(f'{inst}/api/v1/channels/{cid}',timeout=45)
    text=r.text
    if r.status_code==200 and text.lstrip().startswith('{'):
     d=r.json(); vids=d.get('latestVideos') or []
     best={'instance':inst,'status':200,'author':d.get('author'),'subCount':d.get('subCount'),'videos':[{'videoId':v.get('videoId'),'published':v.get('published'),'publishedText':v.get('publishedText'),'title':v.get('title')} for v in vids]}
     break
    else:
     best={'instance':inst,'status':r.status_code,'body':text[:300]}
   except Exception as e:best={'instance':inst,'error':f'{type(e).__name__}: {e}'}
   time.sleep(1.0)
  if best and best.get('status')==200:break
  time.sleep(3+attempt*2)
 out[cid]=best
 print(i,'/',len(ids),cid,best.get('status') if best else None,len(best.get('videos',[])) if best else 0,flush=True)
 time.sleep(1.5)
(OUT/'channels.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('DONE success',sum(1 for x in out.values() if x and x.get('status')==200),'/',len(out),flush=True)
