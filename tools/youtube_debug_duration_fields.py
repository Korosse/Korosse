#!/usr/bin/env python3
from __future__ import annotations
import json, re, requests
import youtube_channel_research_v2 as c

CID='UCsUpkk_F9ClS2F0BkHTsnhA'
VID='NszWYr4zG2s'

flat=c.run_json(['--flat-playlist','--playlist-end','3','--dump-single-json',f'https://www.youtube.com/channel/{CID}/shorts'],240)
print('FLAT_ENTRY_FULL')
print(json.dumps(((flat or {}).get('entries') or [{}])[0],ensure_ascii=False,indent=2)[:30000])

raw=requests.get(f'https://www.youtube.com/channel/{CID}/shorts?hl=ru&gl=RU',headers=c.HEADERS,timeout=40).text
print('\nRAW_LEN',len(raw),'VID_OCCURRENCES',raw.count(VID))

patterns=[
 r'"duration[^"\\]*"\s*:\s*(?:"([^"]+)"|(\d+))',
 r'"length[^"\\]*"\s*:\s*(?:"([^"]+)"|(\d+))',
 r'"timeStatusRenderer"\s*:\s*\{.{0,1500}?\}',
 r'"thumbnailOverlayTimeStatusRenderer"\s*:\s*\{.{0,1500}?\}',
 r'"accessibilityText"\s*:\s*"([^"]{0,500})"',
 r'"accessibility"\s*:\s*\{.{0,1200}?\}',
 r'"text"\s*:\s*"(\d{1,2}:\d{2}(?::\d{2})?)"',
 r'"simpleText"\s*:\s*"(\d{1,2}:\d{2}(?::\d{2})?)"',
 r'\b\d{1,2}:\d{2}\b',
]
for pat in patterns:
    matches=re.findall(pat,raw,re.I|re.S)
    print('\nPATTERN',pat,'COUNT',len(matches))
    print(matches[:50])

# Print snippets around every target video occurrence, emphasizing duration/time/accessibility keys nearby.
positions=[m.start() for m in re.finditer(re.escape(VID),raw)]
for i,pos in enumerate(positions[:20]):
    snippet=raw[max(0,pos-2500):min(len(raw),pos+5000)]
    if re.search(r'duration|length|timeStatus|accessibility|simpleText|viewCount|publishedTime',snippet,re.I):
        print(f'\n--- VID SNIPPET {i} POS {pos} ---')
        print(snippet[:7500])

# Parse ytInitialData and recursively report paths matching duration/time/accessibility near the target ID.
def after_marker(text, marker):
    p=text.find(marker)
    if p<0:return None
    p+=len(marker)
    while p<len(text) and text[p] in ' \r\n\t=:':p+=1
    try:return json.JSONDecoder().raw_decode(text[p:])[0]
    except Exception:return None

data=None
for marker in ['var ytInitialData = ','ytInitialData = ','window["ytInitialData"] = ']:
    data=after_marker(raw,marker)
    if data:break
print('\nINITIAL_DATA',type(data).__name__ if data else None)

results=[]
def walk(obj,path='root',context_has_vid=False):
    if len(results)>500:return
    if isinstance(obj,dict):
        here=context_has_vid or any(isinstance(v,str) and VID in v for v in obj.values())
        for k,v in obj.items():
            key=str(k)
            if re.search(r'duration|length|time|accessibility|view|published',key,re.I):
                val=v
                text=json.dumps(val,ensure_ascii=False) if not isinstance(val,str) else val
                if here or re.search(r'\d{1,2}:\d{2}|секунд|минут|view|просмотр|день|час',text,re.I):
                    results.append((path+'.'+key,text[:2000]))
            walk(v,path+'.'+key,here)
    elif isinstance(obj,list):
        for i,v in enumerate(obj):walk(v,f'{path}[{i}]',context_has_vid)
walk(data)
print('\nRECURSIVE_RESULTS',len(results))
for item in results[:500]:print(item[0],'=>',item[1])
