from __future__ import annotations
import json,re,statistics,time
from datetime import datetime,timezone
from pathlib import Path
from yt_dlp import YoutubeDL

OUT=Path('target_output');OUT.mkdir(exist_ok=True)
TARGETS={
'UCiiqjbw9FKaVSHyE6kOncKQ':'Нарезка T2x2',
'UCWAs-6bnfm4lvCphK68m7YQ':'T2x2 BEST',
'UC8WrBIrZBZ2gaEBNILijxPQ':'T2x2 NEWS',
'UCfPJse-3skARpxs5LaSUiWA':'TWITCH НАРЕЗКИ T2X2',
'UCm1ntxZX0XAEydR70UABOUw':'Нарезки Стинта 2',
'UCWFet2M-JDh6XL-8RfPoFDg':'Stint Fun',
'UCb-SQh-EzmM4PViGtD_42bg':'Твич моменты',
'UC3z13cV53Pk3vrZjY7LHn-w':'MazelloFFMoments',
'UCbBUIeZzS_mOzk-sl2I0Wew':'Стинт лучшее',
'UCVtWdpa1--wS9TecNihXB4w':'Стинта Резка',
'UC-HRFcwTBoJhxOGBinNGniA':'Virtaz',
'UCAziG6T1Cj3zuo5mxODXrZQ':'Нарезочкин',
'UCKJURvnQLcZJjoCE-lIu1Qw':'DomerFan',
}
CONTACT_RE=re.compile(r'(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{4,})|(?:https?://)?vk\.com/([A-Za-z0-9_.-]+)|(?<![\w@])@([A-Za-z][A-Za-z0-9_]{4,})')
VPN_RE=re.compile(r'\b(vpn|впн|proxy|прокси|vless|xray|outline|amnezia|warp|обход блокиров)\b',re.I)

def opts(flat=False,end=None):
 d={'quiet':True,'no_warnings':True,'skip_download':True,'ignoreerrors':True,'retries':2,'extractor_retries':2,'socket_timeout':20,'extract_flat':'in_playlist' if flat else False,'http_headers':{'Accept-Language':'ru-RU,ru;q=0.9'}}
 if end:d['playlistend']=end
 return d

def one_video(v):
 try:
  with YoutubeDL(opts(False)) as y:return y.extract_info('https://www.youtube.com/watch?v='+v,download=False) or {}
 except Exception as e:return {'id':v,'error':type(e).__name__}

def channel(cid,label):
 try:
  with YoutubeDL(opts(True,18)) as y:p=y.extract_info('https://www.youtube.com/channel/'+cid+'/shorts',download=False) or {}
 except Exception as e:return {'cid':cid,'label':label,'error':type(e).__name__}
 ids=[e.get('id') for e in (p.get('entries') or []) if e and e.get('id')][:15]
 details=[]
 for i,v in enumerate(ids,1):
  d=one_video(v);details.append(d);print(' VIDEO',i,len(ids),v,d.get('view_count'),flush=True);time.sleep(.1)
 title=p.get('channel') or p.get('uploader') or (details[0].get('channel') if details else '') or label
 subs=int(p.get('channel_follower_count') or p.get('uploader_follower_count') or (details[0].get('channel_follower_count') if details else 0) or 0)
 desc=p.get('description') or p.get('channel_description') or ''
 alltext=[title,desc];views=[];recent7=recent14=0;now=datetime.now(timezone.utc).timestamp();videos=[]
 for d in details:
  text=(d.get('title') or '')+'\n'+(d.get('description') or '')
  alltext.append(text);duration=d.get('duration') or 0;ts=d.get('timestamp') or d.get('release_timestamp');vc=int(d.get('view_count') or 0)
  if 0<duration<=65:
   views.append(vc)
   if ts:
    age=(now-ts)/86400
    if age<=7:recent7+=1
    if age<=14:recent14+=1
  videos.append({'id':d.get('id'),'title':d.get('title'),'duration':duration,'views':vc,'timestamp':ts,'upload_date':d.get('upload_date'),'description':(d.get('description') or '')[:1500],'thumbnail':d.get('thumbnail')})
 text='\n'.join(alltext);contacts=[]
 for m in CONTACT_RE.finditer(text):
  if m.group(1):contacts.append('https://t.me/'+m.group(1))
  elif m.group(2):contacts.append('https://vk.com/'+m.group(2))
  elif m.group(3) and m.group(3).lower() not in {'youtube','shorts','instagram','telegram'}:contacts.append('@'+m.group(3))
 contacts=list(dict.fromkeys(contacts))
 return {'cid':cid,'label':label,'channel':title,'url':'https://www.youtube.com/channel/'+cid+'/shorts','subs':subs,'recent7':recent7,'recent14':recent14,'median_views':int(statistics.median(views)) if views else 0,'min_views':min(views) if views else 0,'max_views':max(views) if views else 0,'views':views,'contacts':contacts,'vpn_text':bool(VPN_RE.search(text)),'vpn_hits':sorted(set(x.lower() for x in VPN_RE.findall(text))),'description':desc[:3000],'videos':videos}

def main():
 out=[]
 for i,(cid,label) in enumerate(TARGETS.items(),1):
  print('CHANNEL',i,len(TARGETS),label,flush=True);r=channel(cid,label);out.append(r);print(json.dumps({k:r.get(k) for k in ('channel','subs','recent7','recent14','median_views','contacts','vpn_text','error')},ensure_ascii=False),flush=True)
 (OUT/'target_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
