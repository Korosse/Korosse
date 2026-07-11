from __future__ import annotations
import json,re
from pathlib import Path
from urllib.parse import quote_plus
import requests

OUT=Path(__file__).resolve().parent/'search_activity_probe_output';OUT.mkdir(parents=True,exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'
CHANNELS=['TWITCH НАРЕЗКИ T2X2','T2x2 NEWS','FrostoRezka','Нарезка Папича','Стинт Рофлс','PARADEEVICH REWIND']

def textof(x):
 if isinstance(x,str):return x
 if isinstance(x,dict):
  if isinstance(x.get('simpleText'),str):return x['simpleText']
  return ''.join(str(r.get('text','')) for r in x.get('runs',[]) if isinstance(r,dict))
 return ''
def walk(x):
 if isinstance(x,dict):
  for k,v in x.items():
   if k in ('videoRenderer','compactVideoRenderer') and isinstance(v,dict):yield v
   yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
def extract(raw):
 for marker in ('var ytInitialData = ','ytInitialData = '):
  i=raw.find(marker)
  if i>=0:
   try:return json.JSONDecoder().raw_decode(raw[i+len(marker):])[0]
   except Exception:pass
 return {}
def parse_duration(s):
 m=re.fullmatch(r'(?:(\d+):)?(\d+):(\d+)',s.strip())
 if not m:return None
 h=int(m.group(1) or 0);return h*3600+int(m.group(2))*60+int(m.group(3))
def norm(s):return re.sub(r'[^a-zа-яё0-9]+','',s.lower())
def age_days(s):
 s=s.lower().strip()
 if any(x in s for x in ('только что','сегодня','час назад','минут','секунд')):return 0
 if 'вчера' in s:return 1
 m=re.search(r'(\d+)\s*(?:дн|день|дня|дней)',s)
 if m:return int(m.group(1))
 m=re.search(r'(\d+)\s*(?:нед|недел)',s)
 if m:return int(m.group(1))*7
 m=re.search(r'(\d+)\s*(?:месяц|месяца|месяцев)',s)
 if m:return int(m.group(1))*30
 m=re.search(r'(\d+)\s*(?:год|года|лет)',s)
 if m:return int(m.group(1))*365
 return None
def search(q,sp):
 url='https://www.youtube.com/results?search_query='+quote_plus(q)+'&sp='+sp
 r=requests.get(url,headers={'User-Agent':UA,'Accept-Language':'ru-RU,ru;q=0.9,en;q=0.5'},timeout=35)
 data=extract(r.text);rows=[]
 for v in walk(data):
  rows.append({'id':v.get('videoId'),'title':textof(v.get('title')),'owner':textof(v.get('ownerText') or v.get('longBylineText') or v.get('shortBylineText')),'published':textof(v.get('publishedTimeText')),'views':textof(v.get('viewCountText')),'length':textof(v.get('lengthText'))})
 return {'status':r.status_code,'bytes':len(r.text),'rows':rows[:100]}
result={}
# CAI%3D decoded once by requests URL handling => date sort; also try double-encoded value
for ch in CHANNELS:
 item={}
 for sp in ['CAI%253D','CAI%3D','CAI=']:
  res=search('"'+ch+'"',sp)
  match=[]
  nch=norm(ch)
  for x in res['rows']:
   no=norm(x['owner'])
   if nch and (nch in no or no in nch):
    dur=parse_duration(x['length']);ad=age_days(x['published'])
    match.append({**x,'duration_seconds':dur,'age_days':ad,'is_short':dur is not None and dur<=60})
  item[sp]={'status':res['status'],'bytes':res['bytes'],'all_count':len(res['rows']),'matches':match[:30],'shorts_7d':sum(x['is_short'] and x['age_days'] is not None and x['age_days']<=7 for x in match),'shorts_14d':sum(x['is_short'] and x['age_days'] is not None and x['age_days']<=14 for x in match)}
 result[ch]=item
 print(ch,{k:(v['all_count'],len(v['matches']),v['shorts_7d'],v['shorts_14d']) for k,v in item.items()},flush=True)
(OUT/'probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
