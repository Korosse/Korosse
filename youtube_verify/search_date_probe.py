from __future__ import annotations
import json,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent/'search_date_output';OUT.mkdir(parents=True,exist_ok=True)
VIDEOS=['KNsXWuwDS68','C_iInSYomyY','M3NEYC5N0V8','8m2W1WvejLE']
r={}
for vid in VIDEOS:
 item={}
 for query in [vid,f'https://www.youtube.com/shorts/{vid}',f'https://www.youtube.com/watch?v={vid}']:
  cmd=['yt-dlp','--dump-single-json','--flat-playlist','--playlist-end','5','--skip-download','--no-warnings','--ignore-errors',f'ytsearch5:{query}']
  try:
   p=subprocess.run(cmd,capture_output=True,text=True,timeout=120);d=(json.loads(p.stdout) if p.stdout.strip() else {}) or {};es=d.get('entries') or []
   item[query]={'returncode':p.returncode,'entries':[{'id':e.get('id'),'title':e.get('title'),'timestamp':e.get('timestamp'),'upload_date':e.get('upload_date'),'release_timestamp':e.get('release_timestamp'),'live_status':e.get('live_status'),'duration':e.get('duration'),'view_count':e.get('view_count'),'availability':e.get('availability'),'keys':sorted(e.keys())} for e in es if e][:5],'stderr':p.stderr[-400:]}
  except Exception as e:item[query]={'error':f'{type(e).__name__}: {e}'}
 r[vid]=item
(OUT/'probe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2))
