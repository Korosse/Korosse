from __future__ import annotations
import csv, html, json, re, statistics, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import requests
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'base44_output'; GRID=OUT/'grids'; THUMB=OUT/'thumbs'
for p in (OUT,GRID,THUMB): p.mkdir(parents=True,exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'
S=requests.Session(); S.headers.update({'User-Agent':UA,'Accept-Language':'ru,en;q=0.8'})


def flat_channel(cid:str)->dict:
    url=f'https://www.youtube.com/channel/{cid}/shorts'
    cmd=['yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','15','--skip-download','--no-warnings','--ignore-errors',url]
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        data=(json.loads(r.stdout) if r.stdout.strip() else {}) or {}
    except Exception as exc:
        return {'channel_id':cid,'url':url,'entries':[],'error':f'{type(exc).__name__}: {exc}'}
    entries=[]
    for e in data.get('entries') or []:
        if not e or not e.get('id'): continue
        ts=e.get('thumbnails') or []
        thumb=str(ts[-1].get('url') or '') if ts else str(e.get('thumbnail') or '')
        entries.append({'id':str(e.get('id')),'title':str(e.get('title') or ''),'view_count':int(e.get('view_count') or 0),'thumbnail':thumb})
    return {'channel_id':cid,'title':str(data.get('channel') or data.get('uploader') or data.get('title') or cid),'url':url,'subscribers':int(data.get('channel_follower_count') or data.get('uploader_follower_count') or 0),'entries':entries[:15],'error':r.stderr[-500:] if not entries else ''}


def raw_date(vid:str)->str:
    patterns=[r'"publishDate":"(\d{4}-\d{2}-\d{2})"',r'"uploadDate":"(\d{4}-\d{2}-\d{2})"',r'itemprop="uploadDate" content="(\d{4}-\d{2}-\d{2})"']
    for url in (f'https://www.youtube.com/watch?v={vid}',f'https://www.youtube.com/shorts/{vid}'):
        try: raw=S.get(url,timeout=25).text
        except Exception: continue
        for pat in patterns:
            m=re.search(pat,raw)
            if m:return m.group(1)
    return ''


def age_days(text:str):
    if not text:return None
    try:
        d=datetime.strptime(text[:10],'%Y-%m-%d').replace(tzinfo=timezone.utc)
        return max(0,(datetime.now(timezone.utc)-d).total_seconds()/86400)
    except Exception:return None


def clean_links(channel_url:str)->list[str]:
    base=channel_url.split('/shorts')[0].rstrip('/'); found=[]
    for target in (base,base+'/about'):
        try:raw=S.get(target,timeout=25).text
        except Exception:continue
        decoded=html.unescape(raw).replace('\\u0026','&').replace('\\u003d','=').replace('\\/','/')
        for m in re.finditer(r'https://www\.youtube\.com/redirect\?[^"<> ]+',decoded,re.I):
            try:q=unquote(parse_qs(urlparse(m.group(0)).query).get('q',[''])[0])
            except Exception:q=''
            if re.match(r'https?://(?:t\.me|telegram\.me|vk\.com)/',q,re.I):
                q=q.rstrip('/.,);]}')
                low=q.lower()
                if any(x in low for x in ('/club','/public','/event','/wall','/topic','joinchat','t.me/+')):continue
                if low not in [x.lower() for x in found]:found.append(q)
    return found


def download(v:dict):
    path=THUMB/f"{v['id']}.jpg"
    if path.exists() and path.stat().st_size>1000:return path
    for u in (v.get('thumbnail',''),f"https://i.ytimg.com/vi/{v['id']}/maxresdefault.jpg",f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg"):
        if not u:continue
        try:
            b=S.get(u,timeout=20).content
            if len(b)>1000:
                path.write_bytes(b);Image.open(path).verify();return path
        except Exception:
            try:path.unlink()
            except Exception:pass
    return None


def grid(row:dict)->str:
    ims=[]
    for v in row['videos'][:15]:
        p=download(v)
        if p:
            try:ims.append((v,Image.open(p).convert('RGB')))
            except Exception:pass
    if not ims:return ''
    cw,ch=300,260;canvas=Image.new('RGB',(cw*5,60+ch*3),'white');d=ImageDraw.Draw(canvas);d.text((10,10),f"{row['title']} | {row['channel_id']}",fill='black')
    for i,(v,im) in enumerate(ims):
        x=(i%5)*cw;y=60+(i//5)*ch;im.thumbnail((cw-8,ch-55));canvas.paste(im,(x+(cw-im.width)//2,y));a=v.get('age_days');vv=int(v.get('view_count') or 0);d.text((x+5,y+ch-48),f"{i+1:02d} | {vv:,} | {a:.1f}d" if a is not None else f"{i+1:02d} | {vv:,} | date?",fill='black');d.text((x+5,y+ch-28),v.get('title','')[:40],fill='black')
    safe=re.sub(r'[^A-Za-z0-9А-Яа-я_-]+','_',row['title'])[:55];p=GRID/f'{safe}_{row["channel_id"]}.jpg';canvas.save(p,quality=90);return str(p.relative_to(ROOT))


def main():
    ids=[x.strip() for x in (ROOT/'base44.txt').read_text().splitlines() if x.strip()]
    channels=[]
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs=[pool.submit(flat_channel,cid) for cid in ids]
        for fut in as_completed(futs):channels.append(fut.result())
    vids=list(dict.fromkeys(v['id'] for c in channels for v in c.get('entries',[])))
    dates={}
    with ThreadPoolExecutor(max_workers=36) as pool:
        futs={pool.submit(raw_date,v):v for v in vids}
        for i,fut in enumerate(as_completed(futs),1):
            dates[futs[fut]]=fut.result()
            if i%100==0:print('dates',i,'/',len(vids),flush=True)
    rows=[]
    for c in channels:
        videos=[]
        for e in c.get('entries',[]):
            pub=dates.get(e['id'],'');videos.append({**e,'publish_date':pub,'age_days':age_days(pub)})
        ages=[v['age_days'] for v in videos];known=[x for x in ages if x is not None];views=[int(v.get('view_count') or 0) for v in videos]
        row={'channel_id':c['channel_id'],'title':c.get('title',''),'url':c['url'],'subscribers':int(c.get('subscribers') or 0),'videos_count':len(videos),'date_matches':sum(bool(v.get('publish_date')) for v in videos),'videos_7d':sum(x is not None and x<=7 for x in ages),'videos_14d':sum(x is not None and x<=14 for x in ages),'days_since_last':round(min(known),2) if known else None,'median_views':int(statistics.median(views)) if views else 0,'above_1500':sum(x>=1500 for x in views),'contacts':[],'grid':'','videos':videos,'error':c.get('error','')}
        rows.append(row)
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs={pool.submit(clean_links,r['url']):r for r in rows}
        for fut,r in futs.items():
            try:r['contacts']=fut.result()
            except Exception:r['contacts']=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs={pool.submit(grid,r):r for r in rows}
        for fut,r in futs.items():
            try:r['grid']=fut.result()
            except Exception as exc:r['grid_error']=str(exc)
    fields=['channel_id','title','url','subscribers','videos_count','date_matches','videos_7d','videos_14d','days_since_last','median_views','above_1500','contacts','grid','error']
    def rr(r):return {k:(' | '.join(r.get(k,[])) if isinstance(r.get(k),list) else r.get(k,'')) for k in fields}
    with (OUT/'base44.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([rr(r) for r in rows])
    (OUT/'base44.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    passed=[r for r in rows if r['date_matches']>=10 and (r['videos_7d']>=3 or r['videos_14d']>=6)]
    (OUT/'activity_pass.json').write_text(json.dumps(passed,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE',len(rows),'activity_pass',len(passed),'date_matches',sum(r['date_matches'] for r in rows),flush=True)

if __name__=='__main__':main()
