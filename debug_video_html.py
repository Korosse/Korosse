import json,re,html
from pathlib import Path
import requests

IDS=['KNsXWuwDS68','21EPiAR2Jos','1M64NpYz3Es','_mdw9KHDjf8','_hW5m3a4k3o','jCZlsHRvAuw','ZF3iGhOb8K0']
S=requests.Session();S.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9'});S.cookies.set('CONSENT','YES+cb.20210328-17-p0.en+FX+667')
out=[]
for vid in IDS:
 r=S.get('https://www.youtube.com/watch?v='+vid+'&hl=ru&gl=RU',timeout=25)
 t=r.text
 item={'id':vid,'status':r.status_code,'len':len(t),'matches':{}}
 for key in ['publishDate','uploadDate','viewCount','lengthSeconds','shortDescription','videoId','title']:
  vals=[]
  for m in re.finditer(r'"'+re.escape(key)+r'"\s*:\s*("(?:\\.|[^"\\])*"|\d+|true|false|null)',t):
   vals.append(m.group(1)[:500])
   if len(vals)>=10:break
  item['matches'][key]=vals
 # meta tags
 for patname,pat in {
  'meta_interaction':r'<meta[^>]+itemprop=["\']interactionCount["\'][^>]+content=["\']([^"\']+)',
  'meta_upload':r'<meta[^>]+itemprop=["\']uploadDate["\'][^>]+content=["\']([^"\']+)',
  'meta_duration':r'<meta[^>]+itemprop=["\']duration["\'][^>]+content=["\']([^"\']+)',
  'og_title':r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
 }.items():
  mm=re.findall(pat,t,re.I);item['matches'][patname]=mm[:5]
 # snippets around videoDetails and playabilityStatus
 for marker in ['videoDetails','playabilityStatus','publishDate','interactionCount']:
  pos=t.find(marker)
  item['matches']['snippet_'+marker]=t[max(0,pos-300):pos+1200] if pos>=0 else ''
 out.append(item)
 print(vid,r.status_code,len(t),{k:len(v) if isinstance(v,list) else bool(v) for k,v in item['matches'].items()},flush=True)
Path('debug_output').mkdir(exist_ok=True)
Path('debug_output/debug.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
