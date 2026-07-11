from __future__ import annotations
import csv, html, json, os, re, statistics, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from xml.etree import ElementTree as ET
import requests
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SHARD = int(os.environ.get('SHARD', '0'))
TOTAL = int(os.environ.get('TOTAL_SHARDS', '8'))
OUT = ROOT / f'rss_discovery_output/shard_{SHARD}'
GRID = OUT / 'grids'
THUMB = OUT / 'thumbs'
for p in (OUT, GRID, THUMB):
    p.mkdir(parents=True, exist_ok=True)

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'
S = requests.Session()
S.headers.update({'User-Agent': UA, 'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.5'})
VPN = ('vpn','впн','proxy','прокси','vless','xray','outline','amnezia','warp','nordvpn','expressvpn','proton vpn','surfshark')


def run_json(cmd: list[str], timeout: int = 180) -> tuple[dict, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        data = (json.loads(p.stdout) if p.stdout.strip() else {}) or {}
        return data, p.stderr[-800:]
    except Exception as exc:
        return {}, f'{type(exc).__name__}: {exc}'


def search_query(q: str) -> list[dict]:
    data, _ = run_json([
        'yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','30',
        '--skip-download','--no-warnings','--ignore-errors',f'ytsearch30:{q}'
    ], 210)
    out = []
    for e in data.get('entries') or []:
        if not e:
            continue
        cid = str(e.get('channel_id') or e.get('uploader_id') or '')
        curl = str(e.get('channel_url') or e.get('uploader_url') or '')
        if not cid:
            m = re.search(r'UC[\w-]{20,}', curl)
            cid = m.group(0) if m else ''
        if cid:
            out.append({'channel_id': cid, 'title': str(e.get('channel') or e.get('uploader') or ''), 'query': q})
    print('SEARCH', q, len(out), flush=True)
    return out


def flat_channel(seed: dict) -> dict:
    cid = seed['channel_id']
    url = f'https://www.youtube.com/channel/{cid}/shorts'
    data, err = run_json([
        'yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','15',
        '--skip-download','--no-warnings','--ignore-errors',url
    ], 150)
    entries = []
    for e in data.get('entries') or []:
        if not e or not e.get('id'):
            continue
        thumbs = e.get('thumbnails') or []
        thumb = str(thumbs[-1].get('url') or '') if thumbs else str(e.get('thumbnail') or '')
        entries.append({
            'id': str(e.get('id')),
            'title': str(e.get('title') or ''),
            'view_count': int(e.get('view_count') or 0),
            'duration': e.get('duration'),
            'thumbnail': thumb,
        })
    return {
        'channel_id': cid,
        'title': str(data.get('channel') or data.get('uploader') or seed.get('title') or cid),
        'url': url,
        'subscribers': int(data.get('channel_follower_count') or data.get('uploader_follower_count') or 0),
        'description': str(data.get('description') or ''),
        'queries': seed.get('queries', []),
        'videos': entries[:15],
        'error': err if not entries else '',
    }


def rss_map(cid: str) -> dict[str, str]:
    try:
        r = S.get(f'https://www.youtube.com/feeds/videos.xml?channel_id={cid}', timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception:
        return {}
    ns = {'atom':'http://www.w3.org/2005/Atom','yt':'http://www.youtube.com/xml/schemas/2015'}
    out = {}
    for entry in root.findall('atom:entry', ns):
        vid = entry.findtext('yt:videoId', default='', namespaces=ns)
        pub = entry.findtext('atom:published', default='', namespaces=ns)
        if vid:
            out[vid] = pub
    return out


def age_days(text: str):
    if not text:
        return None
    try:
        d = datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(timezone.utc)
        return max(0, (datetime.now(timezone.utc) - d).total_seconds() / 86400)
    except Exception:
        return None


def contact_links(channel_url: str, description: str) -> list[str]:
    base = channel_url.split('/shorts')[0].rstrip('/')
    blobs = [description]
    for target in (base, base + '/about'):
        try:
            blobs.append(S.get(target, timeout=25).text)
        except Exception:
            pass
    text = html.unescape(' '.join(blobs)).replace('\\u0026','&').replace('\\u003d','=').replace('\\/','/')
    found = []
    # Resolve YouTube redirects first
    for m in re.finditer(r'https://www\.youtube\.com/redirect\?[^"<> ]+', text, re.I):
        try:
            q = unquote(parse_qs(urlparse(m.group(0)).query).get('q', [''])[0])
        except Exception:
            q = ''
        if q:
            text += ' ' + q
    pats = re.findall(r'https?://(?:t\.me|telegram\.me|vk\.com)/[A-Za-z0-9_.+/-]+|(?:t\.me|telegram\.me|vk\.com)/[A-Za-z0-9_.+/-]+|@[A-Za-z0-9_]{4,}', text, re.I)
    for x in pats:
        if x.startswith('@'):
            x = 'https://t.me/' + x[1:]
        elif not x.startswith('http'):
            x = 'https://' + x
        x = x.rstrip('/.,);]}')
        low = x.lower()
        if any(z in low for z in ('/club','/public','/event','/wall','/topic','joinchat','t.me/+','/bot')):
            continue
        if low not in [y.lower() for y in found]:
            found.append(x)
    return found


def download_thumb(v: dict):
    p = THUMB / f"{v['id']}.jpg"
    if p.exists() and p.stat().st_size > 1000:
        return p
    urls = [v.get('thumbnail',''), f"https://i.ytimg.com/vi/{v['id']}/maxresdefault.jpg", f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg"]
    for u in urls:
        if not u:
            continue
        try:
            b = S.get(u, timeout=22).content
            if len(b) > 1000:
                p.write_bytes(b)
                Image.open(p).verify()
                return p
        except Exception:
            try: p.unlink()
            except Exception: pass
    return None


def make_grid(row: dict) -> str:
    ims = []
    for v in row['videos'][:15]:
        p = download_thumb(v)
        if p:
            try:
                ims.append((v, Image.open(p).convert('RGB')))
            except Exception:
                pass
    if not ims:
        return ''
    cw, ch = 300, 260
    canvas = Image.new('RGB', (cw*5, 60+ch*3), 'white')
    d = ImageDraw.Draw(canvas)
    d.text((10,10), f"{row['title']} | {row['channel_id']}", fill='black')
    for i,(v,im) in enumerate(ims):
        x=(i%5)*cw; y=60+(i//5)*ch
        im.thumbnail((cw-8, ch-55))
        canvas.paste(im, (x+(cw-im.width)//2, y))
        a=v.get('age_days'); vv=int(v.get('view_count') or 0)
        d.text((x+5,y+ch-48), f"{i+1:02d} | {vv:,} | {a:.1f}d" if a is not None else f"{i+1:02d} | {vv:,} | ?", fill='black')
        d.text((x+5,y+ch-28), v.get('title','')[:40], fill='black')
    safe=re.sub(r'[^A-Za-z0-9А-Яа-яЁё_-]+','_',row['title'])[:55]
    p=GRID/f'{safe}_{row["channel_id"]}.jpg'
    canvas.save(p, quality=90)
    return str(p.relative_to(ROOT))


def main():
    all_queries=[x.strip() for x in (ROOT/'round2_queries.txt').read_text(encoding='utf-8').splitlines() if x.strip()]
    queries=all_queries[SHARD::TOTAL]
    discovered={}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs=[ex.submit(search_query,q) for q in queries]
        for fut in as_completed(futs):
            for x in fut.result():
                item=discovered.setdefault(x['channel_id'], {'channel_id':x['channel_id'],'title':x['title'],'queries':[]})
                if x['query'] not in item['queries']:
                    item['queries'].append(x['query'])
    print('UNIQUE', len(discovered), flush=True)

    channels=[]
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs=[ex.submit(flat_channel,x) for x in discovered.values()]
        for i,fut in enumerate(as_completed(futs),1):
            try: channels.append(fut.result())
            except Exception as exc: print('CHANNEL_ERROR',exc,flush=True)
            if i%50==0: print('CHANNELS',i,'/',len(discovered),flush=True)

    base=[]
    for c in channels:
        views=[int(v.get('view_count') or 0) for v in c['videos']]
        c['videos_count']=len(c['videos'])
        c['median_views']=int(statistics.median(views)) if views else 0
        c['above_1500']=sum(v>=1500 for v in views)
        if 5000 <= c['subscribers'] <= 50000 and c['videos_count'] >= 10 and c['median_views'] >= 2000 and c['above_1500'] >= 8:
            base.append(c)
    print('BASE',len(base),flush=True)

    rss_maps={}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs={ex.submit(rss_map,c['channel_id']):c['channel_id'] for c in base}
        for fut,cid in futs.items():
            try: rss_maps[cid]=fut.result()
            except Exception: rss_maps[cid]={}

    active=[]
    for c in base:
        lookup=rss_maps.get(c['channel_id'],{})
        for v in c['videos']:
            pub=lookup.get(v['id'],'')
            v['publish_date']=pub
            v['age_days']=age_days(pub)
        ages=[v['age_days'] for v in c['videos']]
        known=[x for x in ages if x is not None]
        c['rss_matches']=sum(x is not None for x in ages)
        c['videos_7d']=sum(x is not None and x<=7 for x in ages)
        c['videos_14d']=sum(x is not None and x<=14 for x in ages)
        c['days_since_last']=round(min(known),2) if known else None
        c['contacts']=contact_links(c['url'],c.get('description',''))
        blob=(c.get('description') or '').lower()
        c['vpn_text']=' | '.join(x for x in VPN if x in blob)
        c['activity_pass']=c['rss_matches']>=10 and (c['videos_7d']>=3 or c['videos_14d']>=6)
        if c['activity_pass']:
            active.append(c)
        print('RSS',c['title'],c['rss_matches'],c['videos_7d'],c['videos_14d'],len(c['contacts']),flush=True)

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs={ex.submit(make_grid,c):c for c in active}
        for fut,c in futs.items():
            try:c['grid']=fut.result()
            except Exception as exc:c['grid_error']=str(exc)

    fields=['channel_id','title','url','subscribers','videos_count','median_views','above_1500','rss_matches','videos_7d','videos_14d','days_since_last','contacts','vpn_text','grid','queries','error']
    def outrow(c):
        return {k:(' | '.join(str(x) for x in c.get(k,[])) if isinstance(c.get(k),list) else c.get(k,'')) for k in fields}
    for name,data in [('all',channels),('base',base),('active',active)]:
        with (OUT/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([outrow(c) for c in data])
    (OUT/'active.json').write_text(json.dumps(active,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE shard',SHARD,'queries',len(queries),'unique',len(discovered),'base',len(base),'active',len(active),flush=True)

if __name__=='__main__':
    main()
