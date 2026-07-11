from __future__ import annotations
import json,re,subprocess
from pathlib import Path
import requests

OUT=Path(__file__).resolve().parent/'date_probe_output';OUT.mkdir(parents=True,exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'
VIDEOS=['KNsXWuwDS68','C_iInSYomyY','M3NEYC5N0V8','8m2W1WvejLE']
raw=requests.get('https://www.youtube.com',headers={'User-Agent':UA},timeout=30).text
km=re.search(r'"INNERTUBE_API_KEY":"([^"]+)"',raw);vm=re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"',raw)
key=km.group(1) if km else '';version=vm.group(1) if vm else '2.20260710.00.00'
result={'key_found':bool(key),'version':version,'videos':{}}
clients=[
 ('WEB',{'clientName':'WEB','clientVersion':version,'hl':'ru','gl':'RU'}),
 ('ANDROID',{'clientName':'ANDROID','clientVersion':'20.10.38','androidSdkVersion':30,'hl':'ru','gl':'RU'}),
 ('IOS',{'clientName':'IOS','clientVersion':'20.10.4','deviceMake':'Apple','deviceModel':'iPhone16,2','hl':'ru','gl':'RU'}),
 ('TVHTML5',{'clientName':'TVHTML5','clientVersion':'7.20260701.18.00','hl':'ru','gl':'RU'}),
 ('WEB_EMBEDDED',{'clientName':'WEB_EMBEDDED_PLAYER','clientVersion':version,'clientScreen':'EMBED','hl':'ru','gl':'RU'}),
]
for vid in VIDEOS:
    item={'player':{},'yt_dlp':{},'data_api':{}}
    for name,client in clients:
        try:
            data=requests.post(f'https://www.youtube.com/youtubei/v1/player?key={key}',json={'context':{'client':client},'videoId':vid,'contentCheckOk':True,'racyCheckOk':True},headers={'User-Agent':UA},timeout=25).json()
            micro=((data.get('microformat') or {}).get('playerMicroformatRenderer') or {})
            item['player'][name]={'status':((data.get('playabilityStatus') or {}).get('status')),'publishDate':micro.get('publishDate'),'uploadDate':micro.get('uploadDate'),'dateText':micro.get('dateText'),'liveBroadcastDetails':micro.get('liveBroadcastDetails'),'micro_keys':sorted(micro.keys())}
        except Exception as exc:item['player'][name]={'error':f'{type(exc).__name__}: {exc}'}
    for clientarg in ['web','android_vr','web_safari','tv','ios','mweb','default']:
        cmd=['yt-dlp','--dump-single-json','--skip-download','--no-warnings','--extractor-args',f'youtube:player_client={clientarg}',f'https://www.youtube.com/watch?v={vid}']
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=90);d=(json.loads(r.stdout) if r.stdout.strip() else {}) or {}
            item['yt_dlp'][clientarg]={'returncode':r.returncode,'upload_date':d.get('upload_date'),'timestamp':d.get('timestamp'),'release_timestamp':d.get('release_timestamp'),'availability':d.get('availability'),'error':r.stderr[-400:]}
        except Exception as exc:item['yt_dlp'][clientarg]={'error':f'{type(exc).__name__}: {exc}'}
    try:
        r=requests.get('https://www.googleapis.com/youtube/v3/videos',params={'part':'snippet','id':vid,'key':key},headers={'User-Agent':UA},timeout=25)
        item['data_api']={'status':r.status_code,'body':r.text[:1500]}
    except Exception as exc:item['data_api']={'error':f'{type(exc).__name__}: {exc}'}
    result['videos'][vid]=item
(OUT/'date_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
