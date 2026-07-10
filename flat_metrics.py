from __future__ import annotations
import json
from pathlib import Path
from yt_dlp import YoutubeDL
TARGETS={
'UCiiqjbw9FKaVSHyE6kOncKQ':'Нарезка T2x2','UCWAs-6bnfm4lvCphK68m7YQ':'T2x2 BEST','UC8WrBIrZBZ2gaEBNILijxPQ':'T2x2 NEWS','UCfPJse-3skARpxs5LaSUiWA':'TWITCH НАРЕЗКИ T2X2','UCm1ntxZX0XAEydR70UABOUw':'Нарезки Стинта 2','UCWFet2M-JDh6XL-8RfPoFDg':'Stint Fun','UCb-SQh-EzmM4PViGtD_42bg':'Твич моменты','UC3z13cV53Pk3vrZjY7LHn-w':'MazelloFFMoments','UCbBUIeZzS_mOzk-sl2I0Wew':'Стинт лучшее','UCVtWdpa1--wS9TecNihXB4w':'Стинта Резка','UC-HRFcwTBoJhxOGBinNGniA':'Virtaz','UCAziG6T1Cj3zuo5mxODXrZQ':'Нарезочкин','UCKJURvnQLcZJjoCE-lIu1Qw':'DomerFan'}
opts={'quiet':True,'no_warnings':True,'skip_download':True,'ignoreerrors':True,'extract_flat':'in_playlist','playlistend':20,'retries':2,'socket_timeout':20,'http_headers':{'Accept-Language':'ru-RU,ru;q=0.9'}}
out=[]
for i,(cid,label) in enumerate(TARGETS.items(),1):
 print('CHANNEL',i,len(TARGETS),label,flush=True)
 try:
  with YoutubeDL(opts) as y:p=y.extract_info('https://www.youtube.com/channel/'+cid+'/shorts',download=False) or {}
  entries=[]
  for e in p.get('entries') or []:
   if not e:continue
   entries.append({k:e.get(k) for k in ['id','title','url','webpage_url','duration','view_count','timestamp','release_timestamp','upload_date','live_status','availability','channel','channel_id','uploader','description']})
  out.append({'cid':cid,'label':label,'channel':p.get('channel') or p.get('uploader'),'subs':p.get('channel_follower_count') or p.get('uploader_follower_count'),'description':p.get('description') or p.get('channel_description'),'entries':entries})
  print(json.dumps(entries[:2],ensure_ascii=False),flush=True)
 except Exception as e:out.append({'cid':cid,'label':label,'error':repr(e)})
Path('flat_output').mkdir(exist_ok=True)
Path('flat_output/flat_metrics.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
