from __future__ import annotations
import csv, html, json, re, statistics, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from xml.etree import ElementTree as ET
import requests
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'discovery_output'; GRID=OUT/'grids'; THUMB=OUT/'thumbs'
for p in (OUT,GRID,THUMB):p.mkdir(parents=True,exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'
QUERIES=[
'стример сверху майнкрафт снизу shorts русский','стример сверху gameplay снизу shorts русский','говорящий человек сверху игра снизу shorts русский','подкаст сверху minecraft parkour снизу shorts русский','интервью сверху майнкрафт паркур снизу shorts','нарезки стримера minecraft parkour shorts','нарезки стримов gta parkour shorts русский','истории с реддита майнкрафт паркур shorts русский','истории reddit minecraft parkour русский shorts','озвучка истории minecraft parkour shorts русский','факты minecraft parkour shorts русский','психология minecraft parkour shorts русский','подкаст gameplay background shorts русский','реакция сверху minecraft снизу shorts русский','twitch clips minecraft parkour shorts русский',
't2x2 нарезки shorts','t2x2 лучшие моменты shorts','стинт нарезки shorts','стинт лучшие моменты shorts','фрост нарезки shorts','фрост лучшие моменты shorts','папич нарезки shorts','папич лучшие моменты shorts','бустер нарезки shorts','бустер лучшие моменты shorts','парадеевич нарезки shorts','парадеевич лучшие моменты shorts','мазеллов нарезки shorts','мазеллов лучшие моменты shorts','кореш нарезки shorts','кореш лучшие моменты shorts','эвалон нарезки shorts','эвалон лучшие моменты shorts','братишкин нарезки shorts','братишкин лучшие моменты shorts','дрейк нарезки shorts','drakeoffc нарезки shorts','даня кашин нарезки shorts','дк нарезки shorts','мелстрой нарезки shorts','некоглай нарезки shorts','дмитрий ликс нарезки shorts','рамиль нарезки стримов shorts','карина стримерша нарезки shorts','винди нарезки shorts','кубз скаут нарезки shorts','эдисон нарезки shorts','хесус нарезки shorts','зубарев нарезки shorts','полковник нарезки shorts','шадоукек нарезки shorts','бебей нарезки shorts','булджать нарезки shorts','вернидуб нарезки shorts','nix нарезки shorts русский','rostislav_999 нарезки shorts','exile нарезки shorts','koreshzy нарезки shorts','paradeevich rewind shorts','русские стримеры нарезки shorts свежие','лучшие моменты русских стримеров shorts','twitch нарезки русский shorts новые','стример реакции shorts русский gameplay','фан канал стримера shorts нарезки'
]

def run_json(cmd:list[str],timeout=120):
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        data=(json.loads(r.stdout) if r.stdout.strip() else {}) or {}
        return data,r.stderr[-500:]
    except Exception as exc:return {},f'{type(exc).__name__}: {exc}'

def search_query(q:str)->list[dict]:
    data,err=run_json(['yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','25','--skip-download','--no-warnings','--ignore-errors',f'ytsearch25:{q}'],180)
    out=[]
    for e in data.get('entries') or []:
        if not e:continue
        cid=str(e.get('channel_id') or e.get('uploader_id') or '')
        curl=str(e.get('channel_url') or e.get('uploader_url') or '')
        if not cid:
            m=re.search(r'UC[\w-]{20,}',curl);cid=m.group(0) if m else ''
        if cid:out.append({'channel_id':cid,'channel_url':curl,'channel':str(e.get('channel') or e.get('uploader') or ''),'source_query':q,'video_id':str(e.get('id') or '')})
    print('search',q,len(out),flush=True)
    return out

def flat_channel(seed:dict)->dict:
    cid=seed['channel_id'];url=f'https://www.youtube.com/channel/{cid}/shorts'
    data,err=run_json(['yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','15','--skip-download','--no-warnings','--ignore-errors',url],120)
    entries=[]
    for e in data.get('entries') or []:
        if e and e.get('id'):
            ts=e.get('thumbnails') or []
            thumb=str(ts[-1].get('url') or '') if ts else str(e.get('thumbnail') or '')
            entries.append({'id':str(e.get('id')),'title':str(e.get('title') or ''),'view_count':int(e.get('view_count') or 0),'thumbnail':thumb})
    return {'channel_id':cid,'title':str(data.get('channel') or data.get('uploader') or seed.get('channel') or ''),'url':url,'subscribers':int(data.get('channel_follower_count') or data.get('uploader_follower_count') or 0),'description':str(data.get('description') or ''),'source_queries':seed.get('source_queries',[]),'entries':entries[:15],'error':err if not entries else ''}

def rss_map(cid:str)->dict[str,str]:
    try:
        r=requests.get(f'https://www.youtube.com/feeds/videos.xml?channel_id={cid}',headers={'User-Agent':UA},timeout=25);r.raise_for_status();root=ET.fromstring(r.content)
    except Exception:return {}
    ns={'atom':'http://www.w3.org/2005/Atom','yt':'http://www.youtube.com/xml/schemas/2015'};out={}
    for entry in root.findall('atom:entry',ns):
        vid=entry.findtext('yt:videoId',default='',namespaces=ns);pub=entry.findtext('atom:published',default='',namespaces=ns)
        if vid:out[vid]=pub
    return out

def age_days(text:str):
    if not text:return None
    try:
        d=datetime.fromisoformat(text.replace('Z','+00:00'));return max(0,(datetime.now(timezone.utc)-d.astimezone(timezone.utc)).total_seconds()/86400)
    except Exception:return None

def clean_links(url:str)->list[str]:
    base=url.split('/shorts')[0].rstrip('/');found=[]
    for target in (base,base+'/about'):
        try:raw=requests.get(target,headers={'User-Agent':UA},timeout=25).text
        except Exception:continue
        decoded=html.unescape(raw).replace('\\u0026','&').replace('\\u003d','=').replace('\\/','/')
        for m in re.finditer(r'https://www\.youtube\.com/redirect\?[^"<> ]+',decoded,re.I):
            candidate=m.group(0)
            try:q=unquote(parse_qs(urlparse(candidate).query).get('q',[''])[0])
            except Exception:q=''
            if re.match(r'https?://(?:t\.me|telegram\.me|vk\.com)/',q,re.I):
                q=q.rstrip('/.,);]}')
                if not any(x in q.lower() for x in ('/club','/public','/event','/wall','/topic','joinchat','t.me/+')) and q.lower() not in [x.lower() for x in found]:found.append(q)
    return found

def download_thumb(v:dict):
    vid=v['id'];path=THUMB/f'{vid}.jpg'
    if path.exists() and path.stat().st_size>1000:return path
    urls=[v.get('thumbnail',''),f'https://i.ytimg.com/vi/{vid}/maxresdefault.jpg',f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg']
    for u in urls:
        if not u:continue
        try:
            b=requests.get(u,headers={'User-Agent':UA},timeout=20).content
            if len(b)>1000:
                path.write_bytes(b);Image.open(path).verify();return path
        except Exception:
            try:path.unlink()
            except Exception:pass
    return None

def make_grid(row:dict)->str:
    ims=[]
    for v in row['videos'][:15]:
        p=download_thumb(v)
        if p:
            try:ims.append((v,Image.open(p).convert('RGB')))
            except Exception:pass
    if not ims:return ''
    cw,ch=300,260;canvas=Image.new('RGB',(cw*5,60+ch*3),'white');d=ImageDraw.Draw(canvas);d.text((10,10),f"{row['title']} | {row['channel_id']}",fill='black')
    for i,(v,im) in enumerate(ims):
        x=(i%5)*cw;y=60+(i//5)*ch;im.thumbnail((cw-8,ch-55));canvas.paste(im,(x+(cw-im.width)//2,y));age=v.get('age_days');views=int(v.get('view_count') or 0);d.text((x+5,y+ch-48),f"{i+1:02d} | {views:,} | {age:.1f}d" if age is not None else f"{i+1:02d} | {views:,}",fill='black');d.text((x+5,y+ch-28),v.get('title','')[:40],fill='black')
    safe=re.sub(r'[^A-Za-z0-9А-Яа-я_-]+','_',row['title'])[:55];p=GRID/f'{safe}_{row["channel_id"]}.jpg';canvas.save(p,quality=90);return str(p.relative_to(ROOT))

def main():
    discovered={}
    with ThreadPoolExecutor(max_workers=14) as pool:
        futs=[pool.submit(search_query,q) for q in QUERIES]
        for fut in as_completed(futs):
            for x in fut.result():
                item=discovered.setdefault(x['channel_id'],{'channel_id':x['channel_id'],'channel':x['channel'],'source_queries':[]})
                if x['source_query'] not in item['source_queries']:item['source_queries'].append(x['source_query'])
    print('unique channels',len(discovered),flush=True)
    channels=[]
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs=[pool.submit(flat_channel,x) for x in discovered.values()]
        for i,fut in enumerate(as_completed(futs),1):
            try:channels.append(fut.result())
            except Exception as exc:print('channel error',exc,flush=True)
            if i%50==0:print('channels',i,'/',len(discovered),flush=True)
    rss={}
    with ThreadPoolExecutor(max_workers=24) as pool:
        futs={pool.submit(rss_map,c['channel_id']):c['channel_id'] for c in channels}
        for fut,cid in futs.items():
            try:rss[cid]=fut.result()
            except Exception:rss[cid]={}
    rows=[]
    for c in channels:
        dates=rss.get(c['channel_id'],{});videos=[]
        for e in c['entries']:
            pub=dates.get(e['id'],'');videos.append({**e,'publish_date':pub,'age_days':age_days(pub)})
        ages=[v['age_days'] for v in videos];known=[x for x in ages if x is not None];views=[int(v.get('view_count') or 0) for v in videos]
        row={**{k:c.get(k) for k in ('channel_id','title','url','subscribers','description','source_queries','error')},'videos_count':len(videos),'rss_matches':sum(bool(v.get('publish_date')) for v in videos),'videos_7d':sum(x is not None and x<=7 for x in ages),'videos_14d':sum(x is not None and x<=14 for x in ages),'days_since_last':round(min(known),2) if known else None,'median_views':int(statistics.median(views)) if views else 0,'above_1500':sum(x>=1500 for x in views),'contacts':[],'grid':'','videos':videos}
        row['objective_pass']=5000<=row['subscribers']<=50000 and row['videos_count']>=10 and (row['videos_7d']>=3 or row['videos_14d']>=6) and row['median_views']>=2000 and row['above_1500']>=8
        rows.append(row)
    passed=[r for r in rows if r['objective_pass']]
    print('objective pass',len(passed),flush=True)
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs={pool.submit(clean_links,r['url']):r for r in passed}
        for fut,r in futs.items():
            try:r['contacts']=fut.result()
            except Exception:r['contacts']=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs={pool.submit(make_grid,r):r for r in passed}
        for fut,r in futs.items():
            try:r['grid']=fut.result()
            except Exception as exc:r['grid_error']=str(exc)
    fields=['channel_id','title','url','subscribers','videos_count','rss_matches','videos_7d','videos_14d','days_since_last','median_views','above_1500','contacts','grid','source_queries','objective_pass','error']
    def flatrow(r):return {k:(' | '.join(r.get(k,[])) if isinstance(r.get(k),list) else r.get(k,'')) for k in fields}
    with (OUT/'all_channels.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([flatrow(r) for r in rows])
    with (OUT/'objective_pass.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([flatrow(r) for r in passed])
    (OUT/'objective_pass.json').write_text(json.dumps(passed,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE discovered',len(rows),'passed',len(passed),flush=True)

if __name__=='__main__':main()
