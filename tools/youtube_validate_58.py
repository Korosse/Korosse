#!/usr/bin/env python3
from __future__ import annotations
import html,json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.parse import parse_qs,unquote,urlparse
import requests

CANDS={"UCAJoJ8DNyhN20DmcKH68nag":"89Sklad","UCJJDYZV2VxXUxYqNC1BVwTQ":"ALina_astrID","UC9Seuv1mUvolm-KASUppAnw":"AlexBit25","UCFQ5YRKGPoKMFZALO77YTBw":"Alina Rin Shorts","UCQ_uevm6_y6oC9zb7IS-upA":"ArtKov","UCN2ng4c2D0hfPkHKB7JoH6A":"BezobrazieAndCrazy","UCV9SkXB1Ip1NRg_C8P-qzqQ":"CHICHICOV STREAM","UCa9egqdHusL57dBNYGvl9VA":"DEN TV","UCX-7YXnIsEbKFx48zAxWjnw":"Danny Di","UC8MpdU0rU2g8QYtOa9KgTPg":"GALBEST","UCXwxCN1C5wXKrYZxk-t-K4Q":"ImSan","UCPc6_TH0eOBYSHTiNZFfAug":"JudeLow На Русском!","UCdLcpkzuiNmdba6c4UVWKyw":"MGE_SVOROB","UC37YEIGd2IgOUtg5BiWbb2A":"MLBB WTF MOMENTS","UC3z13cV53Pk3vrZjY7LHn-w":"MazelloFFMoments","UCRa_qceoYo0tlvnra6pVNbw":"Michail Shirma","UCSBL8ohURyEzTjJvZq2x_AA":"Parradix","UC1bXbIOyWaZhxkxzS0PMfEg":"Say CS2 Clips","UCcBbiCpR-eBwL5l6H63lgfg":"Skyeng","UCWFet2M-JDh6XL-8RfPoFDg":"Stint Fun","UCRBs1Sz_vCrTa0xZrVyxA9Q":"Stintik Clips","UC6kA_7pKR-_kmn8vVVe9xNg":"T2X2 | CUT","UCWAs-6bnfm4lvCphK68m7YQ":"T2x2 BEST","UC8WrBIrZBZ2gaEBNILijxPQ":"T2x2 NEWS","UC5lgeMM9RaykOUEo8vPKUcQ":"Therr Maitz","UCaclRtm8V-XEOxQHUashj7g":"Twitch rofls 2.0","UCcsIkGwv57xZ352MvtlkrdQ":"Twix Ubewaka","UCLXuTQh0d_FWM7DwEGnBMPQ":"Zilim","UCIMrKuuS2FqqVTDyLdJ3GUQ":"iceio","UCGMjSQB4JHm5IBikN_wKCCQ":"stay_ugly A","UCV0y4hM0s_MGgRnKdK7iCmA":"stay_ugly B","UCcFrVvDW8DAqxage-nPFYnQ":"zar","UCQc0XnhYi9wwSpkoKv70xEw":"Анимешнич","UCCLebUSqBAyHBpSoikN9oNw":"Архивный Клинок","UC6ICrmgzYYlvutuA5HKJpcQ":"Боджон","UCNC4w-0Ag7La8KTQ023kJFQ":"Дюшес Shorts","UCWuixjKBXLfTqx_DELz58Jw":"Единственный зритель","UCVzSjpkPkhayIhYM390C2-A":"Записи Стинта","UCQxhaB5nc0UWpsjHMCQLhdQ":"Кишечная палочка","UCbX_Gc1mRP76B190cleARFg":"Конструктивный SASAVOT","UCF0Wq1twErLA9TcMOtB-Upg":"Лещина","UCOgqAJZpda4RjKU_vSL3-ng":"НАРЕЗКИ СО СТРИМОВ","UCPSvj4dXjnigdx4lZzPiBuA":"Нарезка Solek","UCAziG6T1Cj3zuo5mxODXrZQ":"Нарезочкин","UC_jJJRp6yZTvWvtLIK6a4Rg":"Нейро Болото","UCLLG0bsQyTIleADWVpkAEkw":"Русский Человек","UCR6AVYAAA3Dij6-HOVf9SxA":"СТИНТ.MP4","UCbIxZ4MRRtYDHJ7gthi-ZYQ":"Скретч","UCZ8LsN8Odr0NeLuAKq0lAqA":"Стинт Нарезки","UCf5QtXFu7aJfUTob5lyhzMA":"Стинт Рофлс","UC8IWXgUQ_Btgh5D5zqRbi8w":"Т2x2 CUTS","UCAlKWectI6Uyt4SCpp2_Eww":"Таверна Грува","UCAFt4mlKDKNcKIJL2kUYmNA":"ФРИК БАНДА ТВИЧА","UC75SXjpLrY_AIgHuNaQktrg":"ХОЗЯЕВА РЕАКЦИИ","UCWM1aGorQna4LnMk8HOoq8g":"ШУКАША ТВ","UC1oCL_-uYRSfFj_XC1DV3_g":"ХАЗЯЕВА MOMENTS","UCI4XxMwT2GLMmKMVdlTVM-g":"Milviks_rbx","UCgaJHUXTXGB5heKlKRvu8sg":"ХАЗЯЕВА S7"}
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept-Language':'ru-RU,ru;q=0.9'}
S=requests.Session();S.headers.update(H)

def norm(x):
 for _ in range(4):x=html.unescape(x).replace('\\u0026','&').replace('\\/','/');x=unquote(x)
 return x

def expand(raw):
 raw=norm(raw);out=[]
 for u in re.findall(r'https?://[^"\\\s<>]+',raw,re.I):
  u=u.rstrip('.,;\"\'\])}');out.append(u)
  try:
   q=parse_qs(urlparse(u).query)
   for k in ('q','url','u'):out += [unquote(v) for v in q.get(k,[])]
  except:pass
 for user in re.findall(r'(?i)(?:telegram|телеграм|тг|tg|связь|реклама|сотрудничество)[^@\n]{0,90}@([A-Za-z0-9_]{5,32})',raw):out.append('https://t.me/'+user)
 return list(dict.fromkeys(out))

def direct(u):
 try:p=urlparse(u);h=p.netloc.lower().replace('www.','');x=p.path.strip('/');l=x.lower()
 except:return False
 if h in ('t.me','telegram.me'):return bool(x) and '/' not in x and not l.startswith(('+','joinchat','s/','share','proxy')) and not l.endswith('bot')
 if h=='vk.com':return bool(x) and '/' not in x and not l.startswith(('club','public','event','wall','video','clip','market','im','page-'))
 return False

def tg(u):
 try:r=S.get(u,timeout=22);raw=r.text;low=raw.lower()
 except Exception as e:return {'url':u,'kind':'ERROR','error':repr(e)}
 mt=re.search(r'<meta property="og:title" content="([^"]*)"',raw);md=re.search(r'<meta property="og:description" content="([^"]*)"',raw)
 title=html.unescape(mt.group(1)) if mt else '';desc=html.unescape(md.group(1)) if md else ''
 if re.search(r'\b[0-9][0-9\s,.]*(subscribers|members|подписчик|участник)',title+' '+desc,re.I):k='CHANNEL_OR_GROUP'
 elif 'you can contact @' in low or title.lower().startswith('telegram: contact @') or ('send message' in low and 'tgme_page_action' in raw):k='PERSONAL'
 else:k='UNCLEAR'
 return {'url':u,'kind':k,'title':title,'description':desc}

def one(cid,title):
 texts=[]
 for suf in ('shorts','about',''):
  try:
   r=S.get(f'https://www.youtube.com/channel/{cid}/{suf}?hl=ru&gl=RU',timeout=35)
   if r.ok:texts.append(r.text)
  except:pass
 raw='\n'.join(texts);ids=[]
 for pat in (r'"entityId":"shorts-shelf-item-([A-Za-z0-9_-]{11})"',r'"videoId":"([A-Za-z0-9_-]{11})"'):
  for v in re.findall(pat,raw):
   if v not in ids:ids.append(v)
 urls=[u for u in expand(raw) if direct(u)]
 checked=[]
 for u in urls[:14]:checked.append(tg(u) if 't.me' in u or 'telegram.me' in u else {'url':u,'kind':'VK_CANDIDATE'})
 personal=[x for x in checked if x.get('kind') in ('PERSONAL','VK_CANDIDATE')]
 return {'channel_id':cid,'title':title,'short_ids':ids[:25],'contacts_checked':checked,'personal_contacts':personal}

rows=[]
with ThreadPoolExecutor(max_workers=10) as ex:
 fs={ex.submit(one,c,t):c for c,t in CANDS.items()}
 for i,f in enumerate(as_completed(fs),1):
  c=fs[f]
  try:r=f.result()
  except Exception as e:r={'channel_id':c,'title':CANDS[c],'error':repr(e),'short_ids':[],'personal_contacts':[]}
  rows.append(r);print(i,len(CANDS),r['title'],len(r.get('short_ids') or []),[x['url'] for x in r.get('personal_contacts') or []],flush=True)
open('validated_58.json','w',encoding='utf-8').write(json.dumps(rows,ensure_ascii=False,indent=2))
