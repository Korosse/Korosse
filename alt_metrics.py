from __future__ import annotations
import json, time, xml.etree.ElementTree as ET
from pathlib import Path
import requests

OUT=Path('alt_metrics_output');OUT.mkdir(exist_ok=True)
TARGETS={
'UCiiqjbw9FKaVSHyE6kOncKQ':'Нарезка T2x2','UCbBUIeZzS_mOzk-sl2I0Wew':'Стинт лучшее','UCWFet2M-JDh6XL-8RfPoFDg':'Stint Fun','UCfPJse-3skARpxs5LaSUiWA':'TWITCH НАРЕЗКИ T2X2','UCm1ntxZX0XAEydR70UABOUw':'Нарезки Стинта 2','UCWAs-6bnfm4lvCphK68m7YQ':'T2x2 BEST','UC8WrBIrZBZ2gaEBNILijxPQ':'T2x2 NEWS','UC3z13cV53Pk3vrZjY7LHn-w':'MazelloFFMoments','UCb-SQh-EzmM4PViGtD_42bg':'Твич моменты','UCAziG6T1Cj3zuo5mxODXrZQ':'Нарезочкин'}
S=requests.Session();S.headers.update({'User-Agent':'Mozilla/5.0','Accept-Language':'ru-RU,ru;q=0.9'})
NS={'atom':'http://www.w3.org/2005/Atom','yt':'http://www.youtube.com/xml/schemas/2015','media':'http://search.yahoo.com/mrss/'}

def fetch_json(url):
 try:
  r=S.get(url,timeout=15)
  try:data=r.json()
  except:data={'text':r.text[:500]}
  return {'status':r.status_code,'data':data,'len':len(r.content)}
 except Exception as e:return {'error':type(e).__name__}

out=[]
for i,(cid,label) in enumerate(TARGETS.items(),1):
 print('CHANNEL',i,len(TARGETS),label,flush=True)
 rss_url=f'https://www.youtube.com/feeds/videos.xml?channel_id={cid}'
 try:
  r=S.get(rss_url,timeout=20); root=ET.fromstring(r.content)
  entries=[]
  for e in root.findall('atom:entry',NS):
   vid=e.findtext('yt:videoId',default='',namespaces=NS); title=e.findtext('atom:title',default='',namespaces=NS); pub=e.findtext('atom:published',default='',namespaces=NS); upd=e.findtext('atom:updated',default='',namespaces=NS)
   entries.append({'id':vid,'title':title,'published':pub,'updated':upd})
 except Exception as e:
  entries=[]; r=type('R',(),{'status_code':0,'content':b''})(); print(' RSS ERROR',type(e).__name__,flush=True)
 print(' RSS',r.status_code,len(entries),flush=True)
 for ent in entries[:15]:
  vid=ent['id']
  ent['ryd']=fetch_json('https://returnyoutubedislikeapi.com/votes?videoId='+vid)
  ent['lemnos']=fetch_json('https://yt.lemnoslife.com/noKey/videos?part=statistics,snippet,contentDetails&id='+vid)
  print(' ',vid,ent['ryd'].get('status'),ent['lemnos'].get('status'),flush=True)
  time.sleep(.08)
 out.append({'channel_id':cid,'channel':label,'rss_status':r.status_code,'entries':entries})
Path(OUT/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
