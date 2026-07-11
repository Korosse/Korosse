from __future__ import annotations
import json,re
from pathlib import Path
import requests

OUT=Path(__file__).resolve().parent/'channel_html_probe_output';OUT.mkdir(parents=True,exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'
CHANNELS={
 'UCfPJse-3skARpxs5LaSUiWA':['KNsXWuwDS68','C_iInSYomyY'],
 'UCVzSjpkPkhayIhYM390C2-A':['M3NEYC5N0V8','8m2W1WvejLE'],
 'UCaYmLqQi76Jhp7MuqAL3TzQ':[]
}

def extract_initial(raw):
 for marker in ('var ytInitialData = ','ytInitialData = '):
  i=raw.find(marker)
  if i>=0:
   try:return json.JSONDecoder().raw_decode(raw[i+len(marker):])[0]
   except Exception:pass
 for pat in [r'"ytInitialData"\s*:\s*({)',r'ytInitialData\s*=\s*({)']:
  m=re.search(pat,raw)
  if m:
   try:return json.JSONDecoder().raw_decode(raw[m.start(1):])[0]
   except Exception:pass
 return {}

def walk(x,path=()):
 if isinstance(x,dict):
  yield path,x
  for k,v in x.items():yield from walk(v,path+(str(k),))
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from walk(v,path+(str(i),))

def scalar_summary(obj):
 out={}
 if isinstance(obj,dict):
  for k,v in obj.items():
   if isinstance(v,(str,int,float,bool)) or v is None:out[k]=v
   elif isinstance(v,dict):
    if 'simpleText' in v:out[k]=v.get('simpleText')
    elif 'runs' in v and isinstance(v['runs'],list):out[k]=''.join(str(z.get('text','')) for z in v['runs'] if isinstance(z,dict))
 return out

result={}
for cid,targets in CHANNELS.items():
 url=f'https://www.youtube.com/channel/{cid}/shorts'
 raw=requests.get(url,headers={'User-Agent':UA,'Accept-Language':'ru-RU,ru;q=0.9,en;q=0.5'},timeout=40).text
 data=extract_initial(raw)
 ids=[];contexts={t:[] for t in targets};interesting=[]
 for path,obj in walk(data):
  if not isinstance(obj,dict):continue
  text=json.dumps(obj,ensure_ascii=False)
  vid=obj.get('videoId') or obj.get('video_id')
  if vid and vid not in ids:ids.append(str(vid))
  keys=set(obj.keys())
  if keys & {'publishedTimeText','relativeDateText','dateText','uploadDate','publishDate','timestamp','timeText','shortBylineText'}:
   interesting.append({'path':'/'.join(path),'summary':scalar_summary(obj),'keys':sorted(keys)})
  for t in targets:
   if t in text:
    contexts[t].append({'path':'/'.join(path),'summary':scalar_summary(obj),'keys':sorted(keys),'snippet':text[:2500]})
 result[cid]={'status_bytes':len(raw),'has_initial':bool(data),'video_ids':ids[:80],'target_contexts':{k:v[:20] for k,v in contexts.items()},'interesting':interesting[:200],'raw_counts':{w:raw.count(w) for w in ['publishedTimeText','relativeDateText','dateText','uploadDate','publishDate','timestamp','videoId']}}
 print(cid,len(raw),bool(data),len(ids),result[cid]['raw_counts'],flush=True)
(OUT/'probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
