from __future__ import annotations
import json,re
from pathlib import Path
from urllib.parse import quote_plus
import requests
OUT=Path(__file__).resolve().parent/'html_search_output';OUT.mkdir(parents=True,exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'
ITEMS=[
 ('KNsXWuwDS68','Toshka Mashup #t2x2 #t2x2','TWITCH НАРЕЗКИ T2X2'),
 ('C_iInSYomyY','ГЕНИАЛЬНЫЙ ПЛАН','TWITCH НАРЕЗКИ T2X2'),
 ('M3NEYC5N0V8','Стинт','Записи Стинта'),
 ('8m2W1WvejLE','Стинт','Записи Стинта'),
]
def textof(x):
 if isinstance(x,str):return x
 if isinstance(x,dict):
  if isinstance(x.get('simpleText'),str):return x['simpleText']
  return ''.join(str(r.get('text','')) for r in x.get('runs',[]) if isinstance(r,dict))
 return ''
def walk(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='videoRenderer' and isinstance(v,dict):yield v
   yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
def search(q):
 u='https://www.youtube.com/results?search_query='+quote_plus(q)
 r=requests.get(u,headers={'User-Agent':UA,'Accept-Language':'ru-RU,ru;q=0.9,en;q=0.5'},timeout=30)
 raw=r.text
 patterns=['var ytInitialData = ','ytInitialData = ']
 data={}
 for marker in patterns:
  i=raw.find(marker)
  if i>=0:
   try:data,_=json.JSONDecoder().raw_decode(raw[i+len(marker):]);break
   except Exception:pass
 if not data:
  m=re.search(r'ytInitialData"\s*:\s*({.+?})\s*,\s*"ytInitialPlayerResponse',raw)
  if m:
   try:data=json.loads(m.group(1))
   except Exception:pass
 rows=[]
 for v in walk(data):
  rows.append({'videoId':v.get('videoId'),'title':textof(v.get('title')),'publishedTimeText':textof(v.get('publishedTimeText')),'viewCountText':textof(v.get('viewCountText')),'owner':textof(v.get('ownerText')),'lengthText':textof(v.get('lengthText'))})
 return {'status':r.status_code,'bytes':len(raw),'rows':rows[:30],'has_data':bool(data),'title':re.search(r'<title>(.*?)</title>',raw,re.S).group(1) if re.search(r'<title>(.*?)</title>',raw,re.S) else ''}
out={}
for vid,title,channel in ITEMS:
 qs=[f'"{title}" {channel}',f'{title} {channel}',title]
 out[vid]={q:search(q) for q in qs}
 print(vid,[(q,next((x for x in z['rows'] if x['videoId']==vid),None)) for q,z in out[vid].items()],flush=True)
(OUT/'probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
