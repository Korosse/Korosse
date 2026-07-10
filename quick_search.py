from __future__ import annotations
import csv, json, re, time
from collections import defaultdict
from pathlib import Path
import requests
from PIL import Image, ImageDraw
from yt_dlp import YoutubeDL

OUT=Path('quick_output'); OUT.mkdir(exist_ok=True)
SHEETS=OUT/'sheets'; SHEETS.mkdir(exist_ok=True)
QUERIES=[
'проблема российского образования тиньков shorts','сколько хованский зарабатывает shorts','просто шел домой арестовали shorts','разогрев смешнее выступления романов shorts','странный хлеб в америке shorts','фреймтаймер попал в тюрьму shorts','полина смачно ударилась в дверь shorts','стинт смотрит фанаты сошли shorts','шоу голос калечит детскую shorts','россии лучшие рестораны поперечный shorts','твое какое дело дружок shorts','роботы рекламы следят за тобой shorts',
'нарезка подкаста minecraft parkour shorts русский','подкаст minecraft parkour shorts русский','подкаст gta parkour shorts русский','интервью subway surfers shorts русский','подкаст с геймплеем shorts русский','фрагмент подкаста с геймплеем shorts','субтитры подкаст геймплей shorts','подкаст сверху геймплей снизу shorts','интервью сверху майнкрафт снизу shorts','нарезка интервью minecraft shorts русский','цитаты из подкаста subway surfers shorts','истории с геймплеем minecraft shorts русский','говорящая голова minecraft parkour shorts',
'тиньков интервью shorts minecraft','хованский интервью shorts gta','поперечный интервью shorts minecraft','мазеллов подкаст shorts gameplay','парадеевич подкаст shorts gameplay','меллстрой интервью shorts minecraft','дк подкаст shorts minecraft','стинт интервью shorts gameplay','бустер интервью shorts minecraft','эдвард бил подкаст shorts gameplay','вписка нарезки shorts minecraft','50 вопросов shorts minecraft parkour','без души подкаст shorts gameplay','он реально это сказал shorts русский','последняя фраза убила shorts русский','бро выдал базу shorts русский','это жиза shorts подкаст','мужики поймут shorts интервью']

def opts(flat=True, end=None):
 d={'quiet':True,'no_warnings':True,'skip_download':True,'ignoreerrors':True,'retries':1,'extractor_retries':1,'socket_timeout':15,'extract_flat':'in_playlist' if flat else False,'http_headers':{'Accept-Language':'ru-RU,ru;q=0.9'}}
 if end:d['playlistend']=end
 return d

def search(q):
 with YoutubeDL(opts()) as y:
  x=y.extract_info('ytsearch20:'+q,download=False) or {}
 out=[]
 for e in x.get('entries') or []:
  if not e:continue
  cid=e.get('channel_id') or e.get('uploader_id'); vid=e.get('id')
  if cid and vid:out.append({'cid':cid,'vid':vid,'channel':e.get('channel') or e.get('uploader') or '','title':e.get('title') or '','q':q})
 return out

def channel_meta(cid):
 try:
  with YoutubeDL(opts(True,5)) as y:x=y.extract_info('https://www.youtube.com/channel/'+cid+'/shorts',download=False) or {}
  return {'channel':x.get('channel') or x.get('uploader') or '', 'subs':int(x.get('channel_follower_count') or x.get('uploader_follower_count') or 0), 'desc':x.get('description') or x.get('channel_description') or '', 'recent_ids':[e.get('id') for e in (x.get('entries') or []) if e and e.get('id')][:5]}
 except Exception as e:return {'error':type(e).__name__,'channel':'','subs':0,'desc':'','recent_ids':[]}

def thumb(vid,p):
 for n in ('maxresdefault.jpg','hqdefault.jpg'):
  try:
   r=requests.get('https://i.ytimg.com/vi/'+vid+'/'+n,timeout=10)
   if r.status_code==200 and len(r.content)>5000:p.write_bytes(r.content); return True
  except:pass
 return False

def sheet(r,i):
 vids=list(dict.fromkeys(r['recent_ids']+r['source_ids']))[:8]; ims=[]
 for j,v in enumerate(vids):
  p=OUT/f'tmp_{i}_{j}.jpg'
  if thumb(v,p):
   try:ims.append((v,Image.open(p).convert('RGB')))
   except:pass
 if not ims:return ''
 canvas=Image.new('RGB',(1280,610),'white'); dr=ImageDraw.Draw(canvas)
 dr.text((8,8),f"{r['channel']} | {r['subs']} subs | hits {r['query_hits']}",fill='black')
 dr.text((8,30),r['url'],fill='black')
 for k,(v,im) in enumerate(ims):
  im.thumbnail((315,250)); x=(k%4)*320; y=70+(k//4)*270; canvas.paste(im,(x+(315-im.width)//2,y)); dr.text((x+5,y+250),v,fill='black')
 name=re.sub(r'[^A-Za-z0-9А-Яа-я_-]+','_',r['channel'] or r['cid'])[:60]
 out=SHEETS/f'{i:03d}_{name}.jpg'; canvas.save(out,quality=88)
 for p in OUT.glob(f'tmp_{i}_*.jpg'):p.unlink(missing_ok=True)
 return str(out)

def main():
 hits=defaultdict(list)
 for i,q in enumerate(QUERIES,1):
  try:rows=search(q)
  except Exception as e:rows=[]
  for r in rows:hits[r['cid']].append(r)
  print('SEARCH',i,len(QUERIES),len(rows),q,flush=True)
 def score(cid):
  rs=hits[cid]; qs={r['q'] for r in rs}; exact=sum(r['q'] in QUERIES[:12] for r in rs); fmt=sum(any(x in r['q'].lower() for x in ('minecraft','gta','subway','геймп','паркур','parkour')) for r in rs); return len(qs)*20+exact*10+fmt*4
 ranked=sorted(hits,key=score,reverse=True)[:100]
 recs=[]
 for i,cid in enumerate(ranked,1):
  m=channel_meta(cid); rs=hits[cid]; source=list(dict.fromkeys(r['vid'] for r in rs)); titles=list(dict.fromkeys(r['title'] for r in rs)); qs=list(dict.fromkeys(r['q'] for r in rs)); text=(m.get('channel','')+' '+m.get('desc','')+' '+' '.join(titles)); ru=len(re.findall('[А-Яа-яЁё]',text))/max(1,len(re.findall('[A-Za-zА-Яа-яЁё]',text)))
  r={'cid':cid,'channel':m.get('channel') or rs[0]['channel'],'subs':m.get('subs',0),'ru':round(ru,3),'url':'https://www.youtube.com/channel/'+cid+'/shorts','query_hits':len(qs),'queries':qs,'source_ids':source,'recent_ids':m.get('recent_ids',[]),'source_titles':titles,'desc':m.get('desc',''),'error':m.get('error','')}
  recs.append(r); print('CHANNEL',i,len(ranked),r['channel'],r['subs'],r['query_hits'],flush=True)
 candidates=[r for r in recs if 3000<=r['subs']<=70000 and r['ru']>=.15]
 candidates.sort(key=lambda r:(5000<=r['subs']<=50000,r['query_hits'],score(r['cid'])),reverse=True)
 for i,r in enumerate(candidates[:60],1):r['sheet']=sheet(r,i)
 (OUT/'results.json').write_text(json.dumps(recs,ensure_ascii=False,indent=2),encoding='utf-8')
 (OUT/'candidates.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2),encoding='utf-8')
 with (OUT/'candidates.csv').open('w',newline='',encoding='utf-8-sig') as f:
  fields=['channel','url','subs','ru','query_hits','queries','source_titles','source_ids','recent_ids','sheet']; w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in candidates:
   z={k:r.get(k,'') for k in fields}
   for k in ('queries','source_titles','source_ids','recent_ids'):z[k]=' | '.join(z[k])
   w.writerow(z)
 print('CANDIDATES',len(candidates),flush=True)
 for r in candidates[:25]:print(json.dumps({k:r.get(k) for k in ('channel','url','subs','query_hits','queries')},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
