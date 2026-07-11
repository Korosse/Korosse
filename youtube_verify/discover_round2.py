from __future__ import annotations
import csv,html,json,re,statistics,subprocess,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import parse_qs,unquote,urlparse
import requests
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'round2_output';GRID=OUT/'grids';THUMB=OUT/'thumbs'
for p in (OUT,GRID,THUMB):p.mkdir(parents=True,exist_ok=True)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'
S=requests.Session();S.headers.update({'User-Agent':UA,'Accept-Language':'ru,en;q=0.8','Accept':'application/json'})
INST='https://inv.zoomerville.com'
VPN=('vpn','впн','proxy','прокси','vless','xray','outline','amnezia','warp','nordvpn','expressvpn','proton vpn','surfshark')

def run_json(cmd,timeout=150):
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
  return ((json.loads(r.stdout) if r.stdout.strip() else {}) or {}),r.stderr[-500:]
 except Exception as e:return {},f'{type(e).__name__}: {e}'

def search(q):
 d,e=run_json(['yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','25','--skip-download','--no-warnings','--ignore-errors',f'ytsearch25:{q}'],180)
 out=[]
 for x in d.get('entries') or []:
  if not x:continue
  cid=str(x.get('channel_id') or x.get('uploader_id') or '')
  curl=str(x.get('channel_url') or x.get('uploader_url') or '')
  if not cid:
   m=re.search(r'UC[\w-]{20,}',curl);cid=m.group(0) if m else ''
  if cid:out.append((cid,str(x.get('channel') or x.get('uploader') or ''),q))
 print('Q',q,len(out),flush=True);return out

def flat(item):
 cid=item['channel_id'];url=f'https://www.youtube.com/channel/{cid}/shorts'
 d,e=run_json(['yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','15','--skip-download','--no-warnings','--ignore-errors',url],120)
 es=[]
 for x in d.get('entries') or []:
  if x and x.get('id'):
   ts=x.get('thumbnails') or [];thumb=str(ts[-1].get('url') or '') if ts else str(x.get('thumbnail') or '')
   es.append({'id':str(x.get('id')),'title':str(x.get('title') or ''),'views':int(x.get('view_count') or 0),'thumb':thumb})
 return {'channel_id':cid,'title':str(d.get('channel') or d.get('uploader') or item.get('title') or cid),'url':url,'subscribers':int(d.get('channel_follower_count') or d.get('uploader_follower_count') or 0),'description':str(d.get('description') or ''),'queries':item['queries'],'videos':es[:15],'error':e if not es else ''}

def inv(cid):
 last={}
 for attempt in range(4):
  try:
   r=S.get(f'{INST}/api/v1/channels/{cid}',timeout=45)
   if r.status_code==200 and r.text.lstrip().startswith('{'):
    d=r.json();return {'status':200,'author':d.get('author'),'subCount':d.get('subCount'),'description':str(d.get('description') or ''),'descriptionHtml':str(d.get('descriptionHtml') or ''),'videos':{str(v.get('videoId')):{'published':v.get('published'),'publishedText':v.get('publishedText'),'title':v.get('title')} for v in (d.get('latestVideos') or []) if v.get('videoId')},'count':len(d.get('latestVideos') or [])}
   last={'status':r.status_code,'body':r.text[:200]}
  except Exception as e:last={'error':f'{type(e).__name__}: {e}'}
  time.sleep(3+attempt*2)
 return last

def age(ts):
 if not ts:return None
 return max(0,(datetime.now(timezone.utc)-datetime.fromtimestamp(float(ts),timezone.utc)).total_seconds()/86400)

def links(blob):
 text=html.unescape(unquote(blob or '')).replace('\\/','/')
 found=[]
 for x in re.findall(r'https?://(?:t\.me|telegram\.me|vk\.com)/[A-Za-z0-9_.+/-]+|(?:t\.me|telegram\.me|vk\.com)/[A-Za-z0-9_.+/-]+|@[A-Za-z0-9_]{4,}',text,re.I):
  if x.startswith('@'):x='https://t.me/'+x[1:]
  elif not x.startswith('http'):x='https://'+x
  x=x.rstrip('/.,);]}');low=x.lower()
  if any(z in low for z in ('/club','/public','/event','/wall','/topic','joinchat','t.me/+','/bot')):continue
  if low not in [y.lower() for y in found]:found.append(x)
 return found

def dl(v):
 p=THUMB/f"{v['id']}.jpg"
 if p.exists() and p.stat().st_size>1000:return p
 for u in (v.get('thumb',''),f"https://i.ytimg.com/vi/{v['id']}/maxresdefault.jpg",f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg"):
  if not u:continue
  try:
   b=S.get(u,timeout=20).content
   if len(b)>1000:p.write_bytes(b);Image.open(p).verify();return p
  except Exception:
   try:p.unlink()
   except Exception:pass
 return None

def grid(r):
 ims=[]
 for v in r['videos'][:15]:
  p=dl(v)
  if p:
   try:ims.append((v,Image.open(p).convert('RGB')))
   except Exception:pass
 if not ims:return ''
 cw,ch=300,260;c=Image.new('RGB',(1500,840),'white');d=ImageDraw.Draw(c);d.text((10,10),f"{r['title']} | {r['channel_id']}",fill='black')
 for i,(v,im) in enumerate(ims):
  x=(i%5)*cw;y=60+(i//5)*ch;im.thumbnail((292,205));c.paste(im,(x+(cw-im.width)//2,y));a=v.get('age_days');d.text((x+5,y+210),f"{i+1:02d} | {v['views']:,} | {a:.1f}d" if a is not None else f"{i+1:02d} | {v['views']:,} | ?",fill='black');d.text((x+5,y+230),v['title'][:40],fill='black')
 safe=re.sub(r'[^A-Za-z0-9А-Яа-я_-]+','_',r['title'])[:55];p=GRID/f'{safe}_{r["channel_id"]}.jpg';c.save(p,quality=90);return str(p.relative_to(ROOT))

def main():
 qs=[x.strip() for x in (ROOT/'round2_queries.txt').read_text().splitlines() if x.strip()]
 pool={}
 with ThreadPoolExecutor(max_workers=14) as ex:
  fs=[ex.submit(search,q) for q in qs]
  for f in as_completed(fs):
   for cid,title,q in f.result():
    z=pool.setdefault(cid,{'channel_id':cid,'title':title,'queries':[]})
    if q not in z['queries']:z['queries'].append(q)
 print('UNIQUE',len(pool),flush=True)
 chans=[]
 with ThreadPoolExecutor(max_workers=20) as ex:
  fs=[ex.submit(flat,x) for x in pool.values()]
  for i,f in enumerate(as_completed(fs),1):
   chans.append(f.result())
   if i%100==0:print('CHANNELS',i,flush=True)
 base=[]
 for c in chans:
  views=[v['views'] for v in c['videos']]
  c['median_views']=int(statistics.median(views)) if views else 0;c['above_1500']=sum(x>=1500 for x in views)
  if 5000<=c['subscribers']<=50000 and len(c['videos'])>=10 and c['median_views']>=2000 and c['above_1500']>=8:base.append(c)
 print('BASE',len(base),flush=True)
 for i,c in enumerate(base,1):
  m=inv(c['channel_id']);c['inv']=m;lookup=m.get('videos',{}) if isinstance(m,dict) else {}
  for v in c['videos']:
   z=lookup.get(v['id'],{});v['published']=z.get('published');v['publishedText']=z.get('publishedText','');v['age_days']=age(v['published'])
  ages=[v['age_days'] for v in c['videos']];known=[x for x in ages if x is not None]
  c['date_matches']=sum(x is not None for x in ages);c['videos_7d']=sum(x is not None and x<=7 for x in ages);c['videos_14d']=sum(x is not None and x<=14 for x in ages);c['days_since_last']=round(min(known),2) if known else None
  blob=' '.join([c.get('description',''),m.get('description','') if isinstance(m,dict) else '',m.get('descriptionHtml','') if isinstance(m,dict) else ''])
  c['contacts']=links(blob);c['vpn_text']=' | '.join(t for t in VPN if t in blob.lower())
  c['activity_pass']=c['date_matches']>=10 and (c['videos_7d']>=3 or c['videos_14d']>=6)
  print('INV',i,'/',len(base),c['title'],c['date_matches'],c['videos_7d'],c['videos_14d'],len(c['contacts']),flush=True);time.sleep(2.0)
 active=[c for c in base if c.get('activity_pass')]
 with ThreadPoolExecutor(max_workers=8) as ex:
  fs={ex.submit(grid,c):c for c in active}
  for f,c in fs.items():
   try:c['grid']=f.result()
   except Exception as e:c['grid_error']=str(e)
 fields=['channel_id','title','url','subscribers','median_views','above_1500','date_matches','videos_7d','videos_14d','days_since_last','contacts','vpn_text','grid','queries','error']
 def row(c):return {k:(' | '.join(c.get(k,[])) if isinstance(c.get(k),list) else c.get(k,'')) for k in fields}
 for name,data in [('base',base),('active',active)]:
  with (OUT/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows([row(c) for c in data])
 (OUT/'active.json').write_text(json.dumps(active,ensure_ascii=False,indent=2),encoding='utf-8')
 print('DONE unique',len(pool),'base',len(base),'active',len(active),flush=True)
if __name__=='__main__':main()
