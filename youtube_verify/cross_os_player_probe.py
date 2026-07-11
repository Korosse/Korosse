from __future__ import annotations
import json, platform, re
from pathlib import Path
from urllib.request import Request, urlopen

OUT=Path(__file__).resolve().parent/'cross_os_probe_output';OUT.mkdir(parents=True,exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'
CHANNEL='https://www.youtube.com/channel/UCfPJse-3skARpxs5LaSUiWA/shorts'
VIDEOS=['KNsXWuwDS68','C_iInSYomyY','M3NEYC5N0V8','8m2W1WvejLE']

def get(url):
 req=Request(url,headers={'User-Agent':UA,'Accept-Language':'ru-RU,ru;q=0.9,en;q=0.5'})
 with urlopen(req,timeout=35) as r:return r.read().decode('utf-8','ignore')
raw=get(CHANNEL)
km=re.search(r'"INNERTUBE_API_KEY":"([^"]+)"',raw)
key=km.group(1) if km else ''
results={'platform':platform.platform(),'key_found':bool(key),'page_bytes':len(raw),'videos':{}}
clients=[
 {'clientName':'WEB','clientVersion':'2.20260708.00.00','hl':'ru','gl':'RU'},
 {'clientName':'WEB','clientVersion':'2.20260625.01.00','hl':'ru','gl':'RU'},
 {'clientName':'ANDROID','clientVersion':'20.10.38','androidSdkVersion':30,'hl':'ru','gl':'RU'},
]
for vid in VIDEOS:
 rows=[]
 for client in clients:
  payload=json.dumps({'context':{'client':client},'videoId':vid,'contentCheckOk':True,'racyCheckOk':True}).encode()
  req=Request(f'https://www.youtube.com/youtubei/v1/player?key={key}',data=payload,headers={'User-Agent':UA,'Content-Type':'application/json'},method='POST')
  try:
   with urlopen(req,timeout=35) as r:data=json.loads(r.read().decode('utf-8','ignore'))
   micro=((data.get('microformat') or {}).get('playerMicroformatRenderer') or {})
   rows.append({'client':client,'status':(data.get('playabilityStatus') or {}).get('status'),'reason':(data.get('playabilityStatus') or {}).get('reason'),'publishDate':micro.get('publishDate'),'uploadDate':micro.get('uploadDate'),'micro_keys':sorted(micro.keys()),'videoDetails_keys':sorted((data.get('videoDetails') or {}).keys())})
  except Exception as e:rows.append({'client':client,'error':f'{type(e).__name__}: {e}'})
 results['videos'][vid]=rows
print(json.dumps(results,ensure_ascii=False,indent=2))
(OUT/(platform.system().lower()+'.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
