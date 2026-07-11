#!/usr/bin/env python3
import json, requests
VID='NszWYr4zG2s'
urls=[
 f'https://inv.nadeko.net/api/v1/videos/{VID}',
 f'https://yewtu.be/api/v1/videos/{VID}',
 f'https://inv.us.projectsegfau.lt/api/v1/videos/{VID}',
 f'https://invidious.nerdvpn.de/api/v1/videos/{VID}',
 f'https://pipedapi.kavin.rocks/streams/{VID}',
 f'https://pipedapi.adminforge.de/streams/{VID}',
 f'https://pipedapi.reallyaweso.me/streams/{VID}',
 f'https://pipedapi.leptons.xyz/streams/{VID}',
]
for url in urls:
 try:
  r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=25)
  print('\nURL',url,'STATUS',r.status_code,'LEN',len(r.content),'TYPE',r.headers.get('content-type'))
  try:
   data=r.json()
   keys=['title','duration','lengthSeconds','views','viewCount','uploadDate','published','publishedText','uploader','uploaderUrl']
   print(json.dumps({k:data.get(k) for k in keys if k in data},ensure_ascii=False)[:3000])
   print('KEYS',list(data)[:50] if isinstance(data,dict) else type(data).__name__)
  except Exception: print(r.text[:1000])
 except Exception as e: print('\nURL',url,'ERROR',repr(e))
