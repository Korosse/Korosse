from __future__ import annotations
import csv, html, json, os, re, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dates_output'
OUT.mkdir(parents=True, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'


def flat_channel(url: str) -> dict:
    cmd = ['yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','15','--skip-download','--no-warnings','--ignore-errors',url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        data = json.loads(r.stdout) if r.stdout.strip() else {}
    except Exception as exc:
        return {'url':url,'error':f'{type(exc).__name__}: {exc}','entries':[]}
    entries=[]
    for e in data.get('entries') or []:
        if not e or not e.get('id'): continue
        entries.append({'id':str(e.get('id')),'title':str(e.get('title') or ''),'view_count':int(e.get('view_count') or 0)})
    return {
        'url':url,
        'channel_id':str(data.get('channel_id') or data.get('uploader_id') or ''),
        'title':str(data.get('channel') or data.get('uploader') or data.get('title') or ''),
        'subscribers':int(data.get('channel_follower_count') or data.get('uploader_follower_count') or 0),
        'description':str(data.get('description') or ''),
        'entries':entries[:15],
        'error':r.stderr[-500:] if r.returncode and not entries else ''
    }


def get_key_and_client() -> tuple[str,str]:
    raw = requests.get('https://www.youtube.com',headers={'User-Agent':UA},timeout=30).text
    km = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', raw)
    vm = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', raw)
    return (km.group(1) if km else '', vm.group(1) if vm else '2.20260710.00.00')


def player_meta(video_id: str, key: str, version: str) -> dict:
    if not key: return {'id':video_id,'error':'no_api_key'}
    payload={
        'context':{'client':{'clientName':'WEB','clientVersion':version,'hl':'ru','gl':'RU'}},
        'videoId':video_id,'contentCheckOk':True,'racyCheckOk':True
    }
    try:
        r=requests.post(f'https://www.youtube.com/youtubei/v1/player?key={key}',json=payload,headers={'User-Agent':UA},timeout=25)
        data=r.json()
        details=data.get('videoDetails') or {}
        micro=((data.get('microformat') or {}).get('playerMicroformatRenderer') or {})
        return {
            'id':video_id,
            'title':str(details.get('title') or ''),
            'view_count':int(details.get('viewCount') or 0),
            'duration':int(details.get('lengthSeconds') or 0),
            'publish_date':str(micro.get('publishDate') or micro.get('uploadDate') or ''),
            'short_description':str(details.get('shortDescription') or ''),
            'error':''
        }
    except Exception as exc:
        return {'id':video_id,'error':f'{type(exc).__name__}: {exc}'}


def clean_external_links(channel_url: str) -> list[str]:
    base=channel_url.split('/shorts')[0].rstrip('/')
    found=[]
    for target in (base,base+'/about'):
        try: raw=requests.get(target,headers={'User-Agent':UA},timeout=25).text
        except Exception: continue
        decoded=html.unescape(raw).replace('\\u0026','&').replace('\\u003d','=')
        for m in re.finditer(r'https://www\.youtube\.com/redirect\?[^"<> ]+',decoded,re.I):
            candidate=m.group(0).replace('\\/','/')
            try:
                q=parse_qs(urlparse(candidate).query).get('q',[''])[0]
                q=unquote(q)
            except Exception: q=''
            if re.match(r'https?://(?:t\.me|telegram\.me|vk\.com)/',q,re.I):
                q=q.rstrip('/.,);]}')
                if q and q.lower() not in [x.lower() for x in found]: found.append(q)
    return found


def age_days(date_text: str):
    if not date_text: return None
    try:
        d=datetime.strptime(date_text[:10],'%Y-%m-%d').replace(tzinfo=timezone.utc)
        return max(0,(datetime.now(timezone.utc)-d).total_seconds()/86400)
    except Exception: return None


def main():
    seeds=[x.strip() for x in (ROOT/'seeds.txt').read_text(encoding='utf-8').splitlines() if x.strip()]
    channels=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs={pool.submit(flat_channel,u):u for u in seeds}
        for fut in as_completed(futs):
            row=fut.result(); channels.append(row); print('flat',row.get('title'),len(row.get('entries') or []),flush=True)
    key,version=get_key_and_client()
    ids=[]
    for c in channels:
        ids.extend([e['id'] for e in c.get('entries') or []])
    ids=list(dict.fromkeys(ids))
    metadata={}
    with ThreadPoolExecutor(max_workers=36) as pool:
        futs={pool.submit(player_meta,v,key,version):v for v in ids}
        for i,fut in enumerate(as_completed(futs),1):
            m=fut.result(); metadata[m['id']]=m
            if i%50==0: print('player',i,'/',len(ids),flush=True)
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        contact_map={c.get('url'):f for c,f in [(c,pool.submit(clean_external_links,c.get('url',''))) for c in channels]}
        for c in channels:
            videos=[]
            for e in c.get('entries') or []:
                m=metadata.get(e['id'],{})
                videos.append({**e,**m,'view_count':int(m.get('view_count') or e.get('view_count') or 0)})
            ages=[age_days(v.get('publish_date','')) for v in videos]
            known=[x for x in ages if x is not None]
            views=[int(v.get('view_count') or 0) for v in videos]
            views_sorted=sorted(views)
            n=len(views_sorted)
            median=int((views_sorted[(n-1)//2]+views_sorted[n//2])/2) if n else 0
            contacts=[]
            try: contacts=contact_map[c.get('url')].result()
            except Exception: pass
            row={
                'channel_id':c.get('channel_id',''),'title':c.get('title',''),'url':c.get('url',''),
                'subscribers':int(c.get('subscribers') or 0),'videos_count':len(videos),
                'videos_7d':sum(x is not None and x<=7 for x in ages),
                'videos_14d':sum(x is not None and x<=14 for x in ages),
                'days_since_last':round(min(known),2) if known else None,
                'median_views':median,'above_1500':sum(x>=1500 for x in views),
                'contacts':' | '.join(contacts),'description':c.get('description',''),
                'video_dates':' | '.join(v.get('publish_date','') for v in videos),
                'video_ids':' | '.join(v.get('id','') for v in videos),
                'errors':c.get('error','')+' | '+'; '.join(v.get('error','') for v in videos if v.get('error')),
                'videos':videos
            }
            rows.append(row)
    fields=['channel_id','title','url','subscribers','videos_count','videos_7d','videos_14d','days_since_last','median_views','above_1500','contacts','video_dates','video_ids','errors']
    with (OUT/'date_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in rows])
    (OUT/'date_all.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE channels',len(rows),'videos',len(ids),'api_key',bool(key),flush=True)

if __name__=='__main__': main()
