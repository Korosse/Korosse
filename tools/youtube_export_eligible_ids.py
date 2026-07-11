#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

TARGETS='''
UC0YUDNP3sMfSLXVIK1d8EOA UC156i8-zUY2qdJGPC4KxWzQ UC1Xrc8ziKhlB1-npGwbOdVA UC5KD_Q_rS3lVfP_hMDZ3HwQ
UC5UWlmRI0FTIcoBrnLQx8Gw UC7eRXTtrNb9fJ_wzwve7o0w UCAjQd3mUYdaPDSFR01KJEYw UCAvnUFQiGERhAqnnPRgBQyw
UCDocmrzfOQmHkTOdhUTOrEw UCEjBZONzvfiUbG2lfncJKmQ UCGla_NKMy5_m4J5d4pRmV5g UCGoEPWV00IrmRdnWTYf3HJA
UCGwb9SioMSO3OpwZH_dczGA UCH3giddBL9GGgculbNTMe5Q UCHcKojNUJgyBvaCHpHwlMPA UCNTCV2AsxALUWAYxTbxiZag
UCNW5NSIqFGXWmeGAxkNyOfw UCO9vkOzYyHJYfTwvJwuL56A UCP_OKgx8b17EcmPe-uq2krw UCQB_eP3LyOAt-PFZZzCQBhw
UCRJEIA0IXTUwPn4aSt17Skw UCScadn4f1l5GsRfyZet-zAQ UCSv-XT7QgOBKIL898D8jsOw UCTJ6iXgdWdPLcWxCGTaa0Kg
UCTYqDIlPrb-GUWOohsv90nQ UCVncLhqp3y1KDhHaJh3Wrrg UCa4-DzRXobidyHig4xlxJrw UCbY-Oi636gF_kzAs9HVyKvw
UCbc1jpyQqPsjh_xJK4oCaqg UCfiloj1zXZqdnPplW2Ik2dw UChMbbyOAvxmrLi3SExSmG0g UChMolkYFLzP5legR_rFCkFQ
UCiR8IdaaRTEPsL4I4y6B6_g UCn8B40JbXKz-oZtjOFODP8g UCqcC5OjfvOJmJRJTGH4C1Iw UCrMySZP0MM3WrPU_1ur8FOg
UCsJfpTdAGDF7n2jISCkpLGg UCsS4z_j7eyt12t1wokJXOqA UCtnR2kwp66ytnM9AWt50yIQ UCwJVnO_0BLY5IBtDePn_4Jw
UCwiUh7_nAqwDRMJKIyegKTA UCzjQKCbFItZLrbXD9NtB1Pw
'''.split()
OUT=Path('eligible_ids_output'); OUT.mkdir(exist_ok=True)
HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9'}
PAT=re.compile(r'"entityId":"shorts-shelf-item-([A-Za-z0-9_-]{11})"')
TITLE=re.compile(r'<meta property="og:title" content="([^"]+)')

def one(cid):
    r=requests.get(f'https://www.youtube.com/channel/{cid}/shorts?hl=ru&gl=RU',headers=HEADERS,timeout=30)
    raw=r.text if r.ok else ''
    ids=[]
    for vid in PAT.findall(raw):
        if vid not in ids: ids.append(vid)
    m=TITLE.search(raw)
    return {'channel_id':cid,'title':m.group(1) if m else cid,'status':r.status_code,'video_ids':ids[:25]}

rows=[]
with ThreadPoolExecutor(max_workers=14) as ex:
    futures={ex.submit(one,cid):cid for cid in TARGETS}
    for i,f in enumerate(as_completed(futures),1):
        try: row=f.result()
        except Exception as e: row={'channel_id':futures[f],'status':'ERROR','error':repr(e),'video_ids':[]}
        rows.append(row)
        print(i,len(TARGETS),row.get('status'),row.get('title'),len(row.get('video_ids') or []),flush=True)
rows.sort(key=lambda x:x['channel_id'])
(OUT/'eligible_ids.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'eligible_ids.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=['channel_id','title','status','video_ids']); w.writeheader()
    for row in rows: w.writerow({'channel_id':row['channel_id'],'title':row.get('title'),'status':row.get('status'),'video_ids':';'.join(row.get('video_ids') or [])})
print(json.dumps({'channels':len(rows),'with_ids':sum(bool(r.get('video_ids')) for r in rows),'ids':sum(len(r.get('video_ids') or []) for r in rows)}))
