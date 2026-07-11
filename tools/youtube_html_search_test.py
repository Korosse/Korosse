#!/usr/bin/env python3
import json,re,requests
from urllib.parse import quote

Q='nix нарезки shorts'
url='https://www.youtube.com/results?search_query='+quote(Q)+'&hl=ru&gl=RU'
h={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9'}
r=requests.get(url,headers=h,timeout=40)
print('status',r.status_code,'len',len(r.text))
m=re.search(r'var ytInitialData = (\{.*?\});</script>',r.text)
if not m:m=re.search(r'ytInitialData"\s*:\s*(\{.*?\})\s*,\s*"ytInitialPlayerResponse',r.text)
print('initial',bool(m), 'channelIds', len(set(re.findall(r'"channelId":"(UC[A-Za-z0-9_-]+)"',r.text))))
rows=[]
if m:
 d=json.loads(m.group(1))
 def walk(x):
  if isinstance(x,dict):
   if 'videoRenderer' in x:
    v=x['videoRenderer']; vid=v.get('videoId')
    title=''.join(t.get('text','') for t in (v.get('title',{}).get('runs') or []))
    owner=v.get('ownerText',{}).get('runs') or v.get('shortBylineText',{}).get('runs') or []
    ch='';cid=''
    if owner:
     ch=owner[0].get('text',''); cid=owner[0].get('navigationEndpoint',{}).get('browseEndpoint',{}).get('browseId','')
    if cid.startswith('UC'):rows.append({'video_id':vid,'title':title,'channel_id':cid,'channel':ch})
   if 'reelItemRenderer' in x:
    v=x['reelItemRenderer']; vid=v.get('videoId'); title=(v.get('headline') or {}).get('simpleText','')
    rows.append({'video_id':vid,'title':title,'channel_id':'','channel':''})
   for y in x.values():walk(y)
  elif isinstance(x,list):
   for y in x:walk(y)
 walk(d)
print(json.dumps(rows[:30],ensure_ascii=False,indent=2))
open('html_search_test.json','w',encoding='utf-8').write(json.dumps({'status':r.status_code,'len':len(r.text),'rows':rows},ensure_ascii=False,indent=2))
