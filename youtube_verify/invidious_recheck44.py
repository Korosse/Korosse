from __future__ import annotations
import csv,json,statistics,subprocess,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'inv44_output';OUT.mkdir(parents=True,exist_ok=True)
INST='https://inv.zoomerville.com'
UA='Mozilla/5.0 Chrome/130 Safari/537.36'


def flat(cid):
 url=f'https://www.youtube.com/channel/{cid}/shorts'
 try:
  r=subprocess.run(['yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','15','--skip-download','--no-warnings','--ignore-errors',url],capture_output=True,text=True,timeout=120)
  d=(json.loads(r.stdout) if r.stdout.strip() else {}) or {}
 except Exception as e:return {'channel_id':cid,'url':url,'entries':[],'error':str(e)}
 es=[]
 for x in d.get('entries') or []:
  if x and x.get('id'):es.append({'id':str(x.get('id')),'title':str(x.get('title') or ''),'views':int(x.get('view_count') or 0)})
 return {'channel_id':cid,'url':url,'title':str(d.get('channel') or d.get('uploader') or cid),'subscribers':int(d.get('channel_follower_count') or 0),'entries':es[:15],'error':r.stderr[-300:] if not es else ''}

def inv(cid):
 try:
  r=requests.get(f'{INST}/api/v1/channels/{cid}',headers={'User-Agent':UA},timeout=40)
  d=r.json() if r.status_code==200 else {}
  vids=d.get('latestVideos') or []
  return {'status':r.status_code,'author':d.get('author'),'subCount':d.get('subCount'),'videos':{str(v.get('videoId')):{'published':v.get('published'),'publishedText':v.get('publishedText'),'title':v.get('title')} for v in vids if v.get('videoId')},'count':len(vids)}
 except Exception as e:return {'error':f'{type(e).__name__}: {e}','videos':{},'count':0}

def age(ts):
 if not ts:return None
 return max(0,(datetime.now(timezone.utc)-datetime.fromtimestamp(float(ts),timezone.utc)).total_seconds()/86400)

def main():
 ids=[x.strip() for x in (ROOT/'base44.txt').read_text().splitlines() if x.strip()]
 with ThreadPoolExecutor(max_workers=16) as p: channels=list(p.map(flat,ids))
 maps={}
 with ThreadPoolExecutor(max_workers=10) as p:
  futs={p.submit(inv,c['channel_id']):c['channel_id'] for c in channels}
  for f,cid in futs.items():maps[cid]=f.result()
 rows=[]
 for c in channels:
  m=maps.get(c['channel_id'],{}); lookup=m.get('videos',{}); videos=[]
  for e in c['entries']:
   meta=lookup.get(e['id'],{}); ts=meta.get('published');videos.append({**e,'published':ts,'publishedText':meta.get('publishedText',''),'age_days':age(ts)})
  ages=[v['age_days'] for v in videos];known=[x for x in ages if x is not None];views=[v['views'] for v in videos]
  row={'channel_id':c['channel_id'],'title':c['title'],'url':c['url'],'subscribers':c['subscribers'] or int(m.get('subCount') or 0),'videos_count':len(videos),'invidious_latest_count':m.get('count',0),'date_matches':sum(v['published'] is not None for v in videos),'videos_7d':sum(x is not None and x<=7 for x in ages),'videos_14d':sum(x is not None and x<=14 for x in ages),'days_since_last':round(min(known),2) if known else None,'median_views':int(statistics.median(views)) if views else 0,'above_1500':sum(x>=1500 for x in views),'video_dates':' | '.join(v.get('publishedText','') for v in videos),'video_ids':' | '.join(v['id'] for v in videos),'error':c.get('error','')+' '+str(m.get('error','')),'videos':videos}
  rows.append(row);print(row['title'],row['date_matches'],row['videos_7d'],row['videos_14d'],row['invidious_latest_count'],flush=True)
 fields=['channel_id','title','url','subscribers','videos_count','invidious_latest_count','date_matches','videos_7d','videos_14d','days_since_last','median_views','above_1500','video_dates','video_ids','error']
 with (OUT/'inv44.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows([{k:r.get(k,'') for k in fields} for r in rows])
 (OUT/'inv44.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 passed=[r for r in rows if r['date_matches']>=10 and (r['videos_7d']>=3 or r['videos_14d']>=6)]
 (OUT/'activity_pass.json').write_text(json.dumps(passed,ensure_ascii=False,indent=2),encoding='utf-8')
 print('DONE',len(rows),'pass',len(passed),flush=True)
if __name__=='__main__':main()
