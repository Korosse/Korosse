#!/usr/bin/env python3
import json,re,requests
vid='NszWYr4zG2s'
h={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9'}
r=requests.get(f'https://www.youtube.com/watch?v={vid}&hl=ru&gl=RU',headers=h,timeout=40)
raw=r.text
patterns={
'duration_meta':r'<meta itemprop="duration" content="([^"]+)"',
'upload_meta':r'<meta itemprop="uploadDate" content="([^"]+)"',
'interaction_meta':r'<meta itemprop="interactionCount" content="([^"]+)"',
'publishDate':r'"publishDate":"([^"]+)"',
'uploadDate':r'"uploadDate":"([^"]+)"',
'lengthSeconds':r'"lengthSeconds":"([^"]+)"',
'viewCount':r'"viewCount":"([^"]+)"',
'approxDurationMs':r'"approxDurationMs":"([^"]+)"'
}
out={'status':r.status_code,'len':len(raw),'matches':{k:(re.search(p,raw).group(1) if re.search(p,raw) else None) for k,p in patterns.items()},'bot':('confirm you’re not a bot' in raw.lower() or 'подтвердить, что вы не бот' in raw.lower())}
print(json.dumps(out,ensure_ascii=False,indent=2));open('watch_meta_test.json','w').write(json.dumps(out,ensure_ascii=False,indent=2))
