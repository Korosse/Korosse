#!/usr/bin/env python3
import json, requests, re
import youtube_channel_research_v2 as c
CID='UCsUpkk_F9ClS2F0BkHTsnhA'; VID='NszWYr4zG2s'
page=c.fetch_channel(CID); key=page['api_key']
clients=[
 ('WEB', {'clientName':'WEB','clientVersion':page['client_version'],'hl':'ru','gl':'RU'}, {}),
 ('ANDROID', {'clientName':'ANDROID','clientVersion':'20.10.38','androidSdkVersion':30,'hl':'ru','gl':'RU'}, {'User-Agent':'com.google.android.youtube/20.10.38 (Linux; U; Android 11) gzip'}),
 ('ANDROID_VR', {'clientName':'ANDROID_VR','clientVersion':'1.60.19','androidSdkVersion':30,'hl':'ru','gl':'RU'}, {'User-Agent':'com.google.android.apps.youtube.vr.oculus/1.60.19 (Linux; U; Android 12) gzip'}),
 ('IOS', {'clientName':'IOS','clientVersion':'20.10.4','deviceMake':'Apple','deviceModel':'iPhone16,2','osName':'iPhone','osVersion':'18.3.1.22D72','hl':'ru','gl':'RU'}, {'User-Agent':'com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3_1 like Mac OS X;)'}),
 ('TVHTML5', {'clientName':'TVHTML5','clientVersion':'7.20260708.18.00','hl':'ru','gl':'RU'}, {'User-Agent':'Mozilla/5.0 (SMART-TV; LINUX; Tizen 7.0) AppleWebKit/537.36'}),
 ('WEB_EMBEDDED', {'clientName':'WEB_EMBEDDED_PLAYER','clientVersion':page['client_version'],'hl':'ru','gl':'RU','clientScreen':'EMBED'}, {'Origin':'https://www.youtube.com','Referer':f'https://www.youtube.com/embed/{VID}'}),
]
for name,client,extra in clients:
 body={'context':{'client':client},'videoId':VID,'contentCheckOk':True,'racyCheckOk':True}
 if name=='WEB_EMBEDDED': body['context']['thirdParty']={'embedUrl':'https://www.youtube.com/'}
 headers={**c.HEADERS,'Content-Type':'application/json',**extra}
 try:
  r=requests.post(f'https://www.youtube.com/youtubei/v1/player?key={key}',headers=headers,json=body,timeout=30)
  d=r.json()
  print('\nCLIENT',name,'STATUS',r.status_code,'LEN',len(r.content))
  print('PLAY',json.dumps(d.get('playabilityStatus'),ensure_ascii=False)[:1000])
  print('DETAILS',json.dumps(d.get('videoDetails'),ensure_ascii=False)[:2000])
  print('MICRO',json.dumps(d.get('microformat'),ensure_ascii=False)[:1200])
 except Exception as e: print(name,'ERROR',repr(e))

w=requests.get(f'https://www.youtube.com/watch?v={VID}&hl=ru&gl=RU',headers=c.HEADERS,timeout=30).text
pos=w.find('"videoDetails"')
print('\nWATCH_VIDEO_DETAILS_POS',pos)
print(w[pos:pos+5000])
for pat in [r'<meta itemprop="duration"[^>]+>',r'<meta itemprop="datePublished"[^>]+>',r'<meta itemprop="interactionCount"[^>]+>',r'"viewCount":"\d+"',r'"lengthSeconds":"\d+"',r'"publishDate":"[^"]+"']:
 print('PATTERN',pat,re.findall(pat,w)[:10])
