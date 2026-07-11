from __future__ import annotations
import csv, json, re, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
import requests

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'rss_output'; OUT.mkdir(parents=True,exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'


def flat_channel(url:str)->dict:
    cmd=['yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','15','--skip-download','--no-warnings','--ignore-errors',url]
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
        data=(json.loads(r.stdout) if r.stdout.strip() else {}) or {}
    except Exception as exc:
        return {'url':url,'error':f'{type(exc).__name__}: {exc}','entries':[]}
    entries=[]
    for e in data.get('entries') or []:
        if e and e.get('id'):
            entries.append({'id':str(e.get('id')),'title':str(e.get('title') or ''),'view_count':int(e.get('view_count') or 0)})
    cid=str(data.get('channel_id') or data.get('uploader_id') or '')
    if not cid:
        m=re.search(r'UC[\w-]{20,}',url); cid=m.group(0) if m else ''
    return {'url':url,'channel_id':cid,'title':str(data.get('channel') or data.get('uploader') or data.get('title') or ''),'subscribers':int(data.get('channel_follower_count') or data.get('uploader_follower_count') or 0),'entries':entries[:15],'error':r.stderr[-500:] if r.returncode and not entries else ''}


def rss_map(cid:str)->dict[str,str]:
    if not cid:return {}
    try:
        r=requests.get(f'https://www.youtube.com/feeds/videos.xml?channel_id={cid}',headers={'User-Agent':UA},timeout=30)
        r.raise_for_status(); root=ET.fromstring(r.content)
    except Exception:return {}
    ns={'atom':'http://www.w3.org/2005/Atom','yt':'http://www.youtube.com/xml/schemas/2015'}
    out={}
    for entry in root.findall('atom:entry',ns):
        vid=entry.findtext('yt:videoId',default='',namespaces=ns)
        pub=entry.findtext('atom:published',default='',namespaces=ns)
        if vid:out[vid]=pub
    return out


def age_days(text:str):
    if not text:return None
    try:
        d=datetime.fromisoformat(text.replace('Z','+00:00'))
        return max(0,(datetime.now(timezone.utc)-d.astimezone(timezone.utc)).total_seconds()/86400)
    except Exception:return None


def main():
    seeds=[x.strip() for x in (ROOT/'seeds.txt').read_text(encoding='utf-8').splitlines() if x.strip()]
    channels=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs=[pool.submit(flat_channel,u) for u in seeds]
        for fut in as_completed(futs):
            try:channels.append(fut.result())
            except Exception as exc:print('flat error',exc,flush=True)
    rss={}
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs={pool.submit(rss_map,c.get('channel_id','')):c.get('channel_id','') for c in channels}
        for fut,cid in [(f,c) for f,c in futs.items()]:
            try:rss[cid]=fut.result()
            except Exception:rss[cid]={}
    rows=[]
    for c in channels:
        dates=rss.get(c.get('channel_id',''),{})
        videos=[]
        for e in c.get('entries') or []:
            pub=dates.get(e['id'],'')
            videos.append({**e,'publish_date':pub,'age_days':age_days(pub)})
        ages=[v['age_days'] for v in videos]
        known=[x for x in ages if x is not None]
        views=[int(v.get('view_count') or 0) for v in videos]
        ss=sorted(views); n=len(ss); med=int((ss[(n-1)//2]+ss[n//2])/2) if n else 0
        row={'channel_id':c.get('channel_id',''),'title':c.get('title',''),'url':c.get('url',''),'subscribers':int(c.get('subscribers') or 0),'videos_count':len(videos),'rss_matches':sum(bool(v.get('publish_date')) for v in videos),'videos_7d':sum(x is not None and x<=7 for x in ages),'videos_14d':sum(x is not None and x<=14 for x in ages),'days_since_last':round(min(known),2) if known else None,'median_views':med,'above_1500':sum(x>=1500 for x in views),'video_dates':' | '.join(v.get('publish_date','') for v in videos),'video_ids':' | '.join(v.get('id','') for v in videos),'error':c.get('error',''),'videos':videos}
        rows.append(row); print(row['title'],row['rss_matches'],row['videos_7d'],row['videos_14d'],flush=True)
    fields=['channel_id','title','url','subscribers','videos_count','rss_matches','videos_7d','videos_14d','days_since_last','median_views','above_1500','video_dates','video_ids','error']
    with (OUT/'rss_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:r.get(k,'') for k in fields} for r in rows])
    (OUT/'rss_all.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE',len(rows),flush=True)

if __name__=='__main__':main()
