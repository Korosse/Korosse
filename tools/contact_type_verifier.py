#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
import requests
URLS='''
https://t.me/r1kflag
https://t.me/kt0takoy
https://t.me/nebudetgg
https://t.me/nebudetafk
https://t.me/thestint
https://t.me/igmail
https://t.me/sleduck
https://t.me/sledovatel_game
https://t.me/Kiljaedentg
https://t.me/Tosyanx6
https://t.me/GrooveStreetTG
https://t.me/darkzz
https://t.me/suchflame
https://t.me/Tiveriy
https://t.me/qwastOff
https://t.me/ra1ph_d
https://t.me/maxmediamanager
https://t.me/tashini_999
https://t.me/Dm1triy25
https://vk.com/r1kflag
https://vk.com/kt0takoy
https://vk.com/rera_seal
https://vk.com/spawnyek
'''.split()
OUT=Path('contact_verification');OUT.mkdir(exist_ok=True)
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9,en;q=0.7'}
def meta(raw,prop):
 m=re.search(r'<meta[^>]+(?:property|name)=["\']'+re.escape(prop)+r'["\'][^>]+content=["\']([^"\']*)',raw,re.I)
 if not m:m=re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']'+re.escape(prop)+r'["\']',raw,re.I)
 return m.group(1) if m else ''
rows=[]
for url in URLS:
 try:
  r=requests.get(url,headers=H,timeout=30,allow_redirects=True);raw=r.text
  title=meta(raw,'og:title');desc=meta(raw,'og:description');typ=meta(raw,'og:type')
  text=re.sub(r'<[^>]+>',' ',raw);text=re.sub(r'\s+',' ',text)
  subs=re.findall(r'([0-9][0-9 .,KМтыс]*)(?: subscribers| подписчик| members| участник)',text,re.I)
  if 't.me/' in url:
   low=(title+' '+desc+' '+text[:5000]).lower()
   if 'subscribers' in low or 'подписчик' in low or 'view in telegram' in low and ('channel' in low or 'канал' in low):kind='TELEGRAM_CHANNEL_OR_GROUP'
   elif 'contact' in low or 'send message' in low or 'написать' in low or 'telegram: contact' in low:kind='LIKELY_PERSONAL_TELEGRAM'
   else:kind='TELEGRAM_UNCLEAR'
  else:
   low=(title+' '+desc+' '+raw[:10000]).lower()
   if 'community' in low or 'club' in low or 'group' in low or 'сообщество' in low:kind='VK_COMMUNITY'
   elif 'profile' in low or 'человек' in low or 'people' in low:kind='LIKELY_PERSONAL_VK'
   else:kind='VK_UNCLEAR'
  rows.append({'url':url,'status':r.status_code,'final_url':r.url,'title':title,'description':desc,'og_type':typ,'subscriber_matches':subs[:5],'kind':kind,'length':len(raw)})
 except Exception as e:rows.append({'url':url,'kind':'ERROR','error':repr(e)})
(OUT/'contacts.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
for x in rows:print(json.dumps(x,ensure_ascii=False),flush=True)
