#!/usr/bin/env python3
from __future__ import annotations
import csv, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import youtube_channel_research_v2 as c

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
OUT=Path('page_ids_output'); OUT.mkdir(exist_ok=True)

def one(cid):
    p=c.fetch_channel(cid)
    return {'channel_id':cid,'title':p.get('title') or cid,'subscribers':p.get('subscribers') or 0,'contacts':p.get('contacts') or [],'video_ids':(p.get('video_ids') or [])[:30]}
rows=[]
with ThreadPoolExecutor(max_workers=10) as ex:
    fs={ex.submit(one,cid):cid for cid in TARGETS}
    for i,f in enumerate(as_completed(fs),1):
        try:r=f.result()
        except Exception as e:r={'channel_id':fs[f],'error':repr(e),'video_ids':[]}
        rows.append(r); print(i,len(TARGETS),r.get('title',r['channel_id']),len(r.get('video_ids') or []),flush=True)
rows.sort(key=lambda r:r.get('title',''))
(OUT/'page_ids.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'page_ids.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=['channel_id','title','subscribers','contacts','video_ids']);w.writeheader()
    for r in rows:w.writerow({'channel_id':r['channel_id'],'title':r.get('title'),'subscribers':r.get('subscribers'),'contacts':'; '.join(r.get('contacts') or []),'video_ids':';'.join(r.get('video_ids') or [])})
print(json.dumps({'channels':len(rows),'ids':sum(len(r.get('video_ids') or []) for r in rows)},ensure_ascii=False))
