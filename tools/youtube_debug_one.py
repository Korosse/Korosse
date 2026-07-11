#!/usr/bin/env python3
import json, re, requests
import youtube_channel_research_v2 as c

CID='UCsUpkk_F9ClS2F0BkHTsnhA'
flat=c.run_json(['--flat-playlist','--playlist-end','5','--dump-single-json',f'https://www.youtube.com/channel/{CID}/shorts'],240)
print('FLAT_TOP_KEYS', sorted((flat or {}).keys()))
entries=(flat or {}).get('entries') or []
for i,e in enumerate(entries[:5]):
    print('ENTRY',i,json.dumps({k:e.get(k) for k in ['id','title','url','channel_id','uploader_id','channel','uploader','view_count','timestamp','upload_date','duration']},ensure_ascii=False))
page=c.fetch_channel(CID)
print('PAGE',json.dumps({k:page.get(k) if k!='raw' else len(page.get(k,'')) for k in page},ensure_ascii=False))
for e in entries[:2]:
    vid=e.get('id')
    print('\nVIDEO',vid)
    body={'context':{'client':{'clientName':'WEB','clientVersion':page.get('client_version'),'hl':'ru','gl':'RU'}},'videoId':vid,'contentCheckOk':True,'racyCheckOk':True}
    headers={**c.HEADERS,'Content-Type':'application/json','Origin':'https://www.youtube.com','X-Youtube-Client-Name':'1','X-Youtube-Client-Version':page.get('client_version')}
    r=requests.post(f"https://www.youtube.com/youtubei/v1/player?key={page.get('api_key')}",headers=headers,json=body,timeout=30)
    print('PLAYER_STATUS',r.status_code,'LEN',len(r.content),'TYPE',r.headers.get('content-type'))
    try:
        d=r.json(); print('PLAYABILITY',d.get('playabilityStatus')); print('DETAILS',json.dumps(d.get('videoDetails'),ensure_ascii=False)[:2000]); print('MICRO',json.dumps(d.get('microformat'),ensure_ascii=False)[:2000])
    except Exception as ex: print('PLAYER_TEXT',r.text[:2000],repr(ex))
    w=requests.get(f'https://www.youtube.com/watch?v={vid}&hl=ru&gl=RU',headers=c.HEADERS,timeout=30)
    print('WATCH_STATUS',w.status_code,'LEN',len(w.content),'TITLE',re.findall(r'<title>(.*?)</title>',w.text[:200000],re.S)[:1])
    for marker in ['var ytInitialPlayerResponse = ','ytInitialPlayerResponse = ','"videoDetails"','"playabilityStatus"']:
        print('MARKER',marker,w.text.find(marker))
    print('WATCH_HEAD',w.text[:500].replace('\n',' '))
