from __future__ import annotations
import json
from pathlib import Path
import requests

OUT=Path(__file__).resolve().parent/'invidious_probe_output';OUT.mkdir(parents=True,exist_ok=True)
INSTANCES=['https://inv.zoomerville.com','https://invidious.nerdvpn.de','https://invidious.f5.si','https://inv.nadeko.net','https://yt.chocolatemoo53.com']
VIDEOS=['KNsXWuwDS68','C_iInSYomyY','M3NEYC5N0V8']
CHANNELS=['UCfPJse-3skARpxs5LaSUiWA','UCVzSjpkPkhayIhYM390C2-A','UCq5cMlXa_G9ipcyidhJkBnw']
r={}
for inst in INSTANCES:
    item={'videos':{},'channels':{}}
    for vid in VIDEOS:
        try:
            x=requests.get(f'{inst}/api/v1/videos/{vid}',timeout=30)
            try:data=x.json()
            except Exception:data={'raw':x.text[:1000]}
            item['videos'][vid]={'status':x.status_code,'published':data.get('published'),'publishedText':data.get('publishedText'),'title':data.get('title'),'error':data.get('error'),'keys':list(data.keys())[:30]}
        except Exception as e:item['videos'][vid]={'error':f'{type(e).__name__}: {e}'}
    for cid in CHANNELS:
        try:
            x=requests.get(f'{inst}/api/v1/channels/{cid}',timeout=30)
            try:data=x.json()
            except Exception:data={'raw':x.text[:1000]}
            vids=data.get('latestVideos') or []
            item['channels'][cid]={'status':x.status_code,'author':data.get('author'),'subCount':data.get('subCount'),'error':data.get('error'),'latest':[{'videoId':v.get('videoId'),'published':v.get('published'),'publishedText':v.get('publishedText'),'title':v.get('title')} for v in vids[:5]],'keys':list(data.keys())[:30]}
        except Exception as e:item['channels'][cid]={'error':f'{type(e).__name__}: {e}'}
    r[inst]=item
(OUT/'probe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2))
