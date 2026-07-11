from __future__ import annotations
import json,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import requests
OUT=Path(__file__).resolve().parent/'instance_output';OUT.mkdir(parents=True,exist_ok=True)
TEST='UCfPJse-3skARpxs5LaSUiWA'
UA='Mozilla/5.0 Chrome/130 Safari/537.36'
try:
 data=requests.get('https://api.invidious.io/instances.json',timeout=30).json()
except Exception as e:
 data=[]
urls=[]
for name,meta in data:
 api=meta.get('api') if isinstance(meta,dict) else False
 uri=(meta.get('uri') if isinstance(meta,dict) else None) or ('https://'+name)
 if api and uri.startswith('https://'): urls.append(uri.rstrip('/'))
urls=list(dict.fromkeys(urls))
def test(u):
 t=time.time()
 try:
  r=requests.get(f'{u}/api/v1/channels/{TEST}',headers={'User-Agent':UA,'Accept':'application/json'},timeout=18)
  ok=r.status_code==200 and r.text.lstrip().startswith('{')
  d=r.json() if ok else {}
  return {'url':u,'ok':ok,'status':r.status_code,'elapsed':round(time.time()-t,2),'author':d.get('author'),'videos':len(d.get('latestVideos') or []),'body':r.text[:120] if not ok else ''}
 except Exception as e:return {'url':u,'ok':False,'status':None,'elapsed':round(time.time()-t,2),'error':f'{type(e).__name__}: {e}'}
results=[]
with ThreadPoolExecutor(max_workers=20) as ex:
 fs=[ex.submit(test,u) for u in urls]
 for f in as_completed(fs):
  x=f.result();results.append(x);print(x,flush=True)
results.sort(key=lambda x:(not x['ok'],x['elapsed']))
(OUT/'instances.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('DONE tested',len(results),'working',sum(x['ok'] for x in results),flush=True)
