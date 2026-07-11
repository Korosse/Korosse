#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

QUERIES = [
'истории из жизни minecraft shorts русский','истории из жизни subway surfers shorts русский','реддит истории minecraft shorts русский','reddit истории subway surfers русский shorts','апвоут истории shorts','подслушано истории minecraft shorts','анонимные истории minecraft parkour shorts','страшные истории minecraft parkour shorts русский','криповые истории gameplay shorts русский','отношения minecraft parkour shorts','отношения subway surfers shorts русский','психология minecraft parkour shorts русский','мужская психология gameplay shorts','женская психология subway surfers shorts','мотивация minecraft parkour shorts русский','мотивация subway surfers shorts русский','факты minecraft parkour shorts русский','факты subway surfers shorts русский','интересные факты gameplay shorts русский','история с реддита gameplay shorts','треды reddit minecraft русский','треды из твиттера gameplay shorts','истории подписчиков minecraft shorts','школьные истории minecraft parkour','истории про отношения gameplay shorts','жизненные истории subway surfers','истории из интернета minecraft shorts','смешные истории minecraft parkour','поучительные истории gameplay shorts','правдивые истории subway surfers','подкаст фрагмент minecraft parkour shorts','подкаст нарезки gameplay shorts русский','интервью фрагмент minecraft shorts','говорящая голова gameplay снизу shorts','человек сверху minecraft снизу shorts','подкаст сверху игра снизу shorts русский','стример сверху cs2 снизу shorts','facecam cs2 shorts русский','facecam roblox shorts русский','роблокс стример нарезки shorts','cs2 стример нарезки shorts русский','valorant стример нарезки shorts русский','dota стример нарезки shorts русский','gta rp стример нарезки shorts русский','minecraft стример нарезки shorts русский','нарезки стримера с субтитрами shorts','лучшие моменты стримеров субтитры shorts','моменты twitch с субтитрами русский shorts','рофлы стримеров с субтитрами shorts','реакции стримеров gameplay shorts','реакция сверху игра снизу shorts русский','ютубер сверху игра снизу shorts','мемы сверху gameplay снизу shorts','вирусное видео снизу подкаст сверху shorts','нарезка подкаста subway surfers shorts','нарезка интервью minecraft parkour shorts','истории звезд gameplay shorts','цитаты подкаста gameplay shorts','советы психолога minecraft parkour shorts','мужские мысли gameplay shorts','женские мысли gameplay shorts','деньги мотивация minecraft parkour shorts','бизнес подкаст gameplay shorts русский','саморазвитие subway surfers shorts русский','интересные истории gameplay снизу','shorts с двумя видео русский','split screen shorts русский подкаст','двойной экран shorts русский','игра на фоне истории shorts русский','майнкрафт на фоне истории shorts','сабвей серферс на фоне истории shorts','parkour background русский shorts','удерживающий геймплей снизу shorts','minecraft parkour background русский рассказ','roblox gameplay история русский shorts','gta parkour подкаст shorts','minecraft снизу интервью shorts','subway surfers снизу интервью shorts','нарезки тикток подкаст gameplay','нарезки reels подкаст minecraft','видео сверху игра снизу субтитры','два экрана субтитры shorts','история человека minecraft parkour','невероятные истории subway surfers','тайны minecraft parkour shorts','загадки gameplay shorts русский','детективные истории minecraft shorts','криминальные истории subway surfers shorts','страшилки gameplay shorts русский','мистические истории minecraft parkour','случаи из жизни gameplay shorts','признания подписчиков minecraft shorts','переписки minecraft parkour shorts','истории из переписок gameplay shorts','отношения reddit stories русский','истории с форумов minecraft shorts','тру крайм gameplay shorts русский','true crime minecraft parkour русский','новости блогеров gameplay shorts','драма блогеров gameplay shorts','стримерские новости gameplay shorts','twitch news shorts русский','нарезки витуберов русский shorts','витубер сверху игра снизу shorts','vtuber clips русский shorts','роблокс истории с субтитрами shorts'
]
OUT=Path('broad_split_discovery');OUT.mkdir(exist_ok=True)
def search(q):
 cmd=['yt-dlp','--skip-download','--quiet','--no-warnings','--ignore-errors','--flat-playlist','--playlist-end','40','--dump-single-json',f'ytsearch40:{q}']
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
  d=json.loads(p.stdout) if p.stdout.strip() else {}
 except Exception:return []
 rows=[]
 for e in d.get('entries') or []:
  if not isinstance(e,dict):continue
  cid=e.get('channel_id') or e.get('uploader_id')
  if isinstance(cid,str) and cid.startswith('UC'):
   rows.append({'query':q,'channel_id':cid,'channel':e.get('channel') or e.get('uploader') or '', 'video_id':e.get('id') or '', 'video_title':e.get('title') or ''})
 return rows
all_rows=[]
with ThreadPoolExecutor(max_workers=8) as ex:
 fs={ex.submit(search,q):q for q in QUERIES}
 for i,f in enumerate(as_completed(fs),1):
  try:r=f.result()
  except Exception:r=[]
  all_rows.extend(r);print(i,len(QUERIES),fs[f],len(r),flush=True)
by={}
for r in all_rows:
 x=by.setdefault(r['channel_id'],{'channel_id':r['channel_id'],'channel':r['channel'],'queries':[],'samples':[]})
 if r['query'] not in x['queries']:x['queries'].append(r['query'])
 if r['video_title'] and len(x['samples'])<8:x['samples'].append({'video_id':r['video_id'],'title':r['video_title']})
rows=sorted(by.values(),key=lambda x:(-len(x['queries']),x['channel'].lower()))
(OUT/'channels.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'raw_results.json').write_text(json.dumps(all_rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'queries':len(QUERIES),'raw':len(all_rows),'channels':len(rows)},ensure_ascii=False))
