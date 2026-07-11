#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

TARGETS='''
UCAJoJ8DNyhN20DmcKH68nag UCJJDYZV2VxXUxYqNC1BVwTQ UC9Seuv1mUvolm-KASUppAnw UCFQ5YRKGPoKMFZALO77YTBw
UCQ_uevm6_y6oC9zb7IS-upA UCN2ng4c2D0hfPkHKB7JoH6A UC-aqhCCsWGapELBHr7EjL0w UCV9SkXB1Ip1NRg_C8P-qzqQ
UCa9egqdHusL57dBNYGvl9VA UCX-7YXnIsEbKFx48zAxWjnw UC8MpdU0rU2g8QYtOa9KgTPg UCXwxCN1C5wXKrYZxk-t-K4Q
UCPc6_TH0eOBYSHTiNZFfAug UCRr5Ecr1Jya5nF74tK2tmPA UCdLcpkzuiNmdba6c4UVWKyw UC37YEIGd2IgOUtg5BiWbb2A
UC3z13cV53Pk3vrZjY7LHn-w UCRa_qceoYo0tlvnra6pVNbw UCWtcaoN-VA4wseYrws-csKw UCSBL8ohURyEzTjJvZq2x_AA
UC1bXbIOyWaZhxkxzS0PMfEg UCcBbiCpR-eBwL5l6H63lgfg UCWFet2M-JDh6XL-8RfPoFDg UCRBs1Sz_vCrTa0xZrVyxA9Q
UC6kA_7pKR-_kmn8vVVe9xNg UCWAs-6bnfm4lvCphK68m7YQ UC8WrBIrZBZ2gaEBNILijxPQ UC1zjgoomO6brXH_6FM0qCCw
UC5lgeMM9RaykOUEo8vPKUcQ UCfawj80iIlmu4jZSRgTT4MQ UCaclRtm8V-XEOxQHUashj7g UCcsIkGwv57xZ352MvtlkrdQ
UCU_djQrl4K2Ks_0QSvAMw0w UCUZvlXe_j5sNn4KzCsnO_hw UCLXuTQh0d_FWM7DwEGnBMPQ UCIMrKuuS2FqqVTDyLdJ3GUQ
UCGMjSQB4JHm5IBikN_wKCCQ UCV0y4hM0s_MGgRnKdK7iCmA UCcFrVvDW8DAqxage-nPFYnQ UCQc0XnhYi9wwSpkoKv70xEw
UCCLebUSqBAyHBpSoikN9oNw UC6ICrmgzYYlvutuA5HKJpcQ UCNC4w-0Ag7La8KTQ023kJFQ UCWuixjKBXLfTqx_DELz58Jw
UCYd9hPaMWpryh_LCh_0A8Vw UCVzSjpkPkhayIhYM390C2-A UCQxhaB5nc0UWpsjHMCQLhdQ UCbX_Gc1mRP76B190cleARFg
UCF0Wq1twErLA9TcMOtB-Upg UCOgqAJZpda4RjKU_vSL3-ng UCCfCgk2ktkKiHnc3y1ejx1w UCPSvj4dXjnigdx4lZzPiBuA
UCAziG6T1Cj3zuo5mxODXrZQ UC1H458Ar25FoJ0TJvd1OPiA UC_jJJRp6yZTvWvtLIK6a4Rg UCMD4hJWS--0MhwUIbFPRlPg
UCEyTi43GDVhgWfMfPWlW3LQ UCLLG0bsQyTIleADWVpkAEkw UCR6AVYAAA3Dij6-HOVf9SxA UCbIxZ4MRRtYDHJ7gthi-ZYQ
UCZ8LsN8Odr0NeLuAKq0lAqA UCf5QtXFu7aJfUTob5lyhzMA UC8IWXgUQ_Btgh5D5zqRbi8w UCAlKWectI6Uyt4SCpp2_Eww
UCAFt4mlKDKNcKIJL2kUYmNA UC75SXjpLrY_AIgHuNaQktrg UC_yvQhmimAyunkFvvuTkYFA UCWM1aGorQna4LnMk8HOoq8g
UC1oCL_-uYRSfFj_XC1DV3_g UCI4XxMwT2GLMmKMVdlTVM-g UCgaJHUXTXGB5heKlKRvu8sg
'''.split()
OUT=Path('fast_ids_output');OUT.mkdir(exist_ok=True)
HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9'}
PAT=re.compile(r'"entityId":"shorts-shelf-item-([A-Za-z0-9_-]{11})"')
TITLE=re.compile(r'<meta property="og:title" content="([^"]+)')

def one(cid):
 r=requests.get(f'https://www.youtube.com/channel/{cid}/shorts?hl=ru&gl=RU',headers=HEADERS,timeout=25)
 raw=r.text if r.ok else ''
 ids=[]
 for v in PAT.findall(raw):
  if v not in ids:ids.append(v)
 t=TITLE.search(raw)
 return {'channel_id':cid,'title':t.group(1) if t else cid,'status':r.status_code,'video_ids':ids[:25]}
rows=[]
with ThreadPoolExecutor(max_workers=18) as ex:
 fs={ex.submit(one,cid):cid for cid in TARGETS}
 for i,f in enumerate(as_completed(fs),1):
  try:x=f.result()
  except Exception as e:x={'channel_id':fs[f],'status':'ERROR','error':repr(e),'video_ids':[]}
  rows.append(x);print(i,len(TARGETS),x.get('status'),x.get('title'),len(x.get('video_ids') or []),flush=True)
rows.sort(key=lambda x:x['channel_id'])
(OUT/'fast_ids.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'fast_ids.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=['channel_id','title','status','video_ids']);w.writeheader()
 for x in rows:w.writerow({'channel_id':x['channel_id'],'title':x.get('title'),'status':x.get('status'),'video_ids':';'.join(x.get('video_ids') or [])})
print(json.dumps({'channels':len(rows),'with_ids':sum(bool(x.get('video_ids')) for x in rows),'ids':sum(len(x.get('video_ids') or []) for x in rows)}))
