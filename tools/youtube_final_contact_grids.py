#!/usr/bin/env python3
from __future__ import annotations

import html, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

CANDIDATES = {
    'UCa4-DzRXobidyHig4xlxJrw': 'FlashMovieAI',
    'UCcmUV8J69s0yR2SgkVT98pg': 'SleDak | Нарезки Sleduck',
    'UCiR8IdaaRTEPsL4I4y6B6_g': 'URODSK Shorts',
    'UCii4eZm84XkoHhp99Ptihqw': 'Sleduck shorts',
    'UCTJ6iXgdWdPLcWxCGTaa0Kg': 'SleDuck Shorts',
    'UC30WSEdcbNHcWGjdqNhCYLA': 'Sledovatel Shorts',
    'UCn8B40JbXKz-oZtjOFODP8g': '89_rezki',
    'UCGla_NKMy5_m4J5d4pRmV5g': 'Денис Стоп',
    'UC5UWlmRI0FTIcoBrnLQx8Gw': 'r1kflagttv',
    'UCfMji4nqhjDfVbBAHauiUtw': 'KITTY LIKE',
    'UC5KD_Q_rS3lVfP_hMDZ3HwQ': 'Нарезка Папича',
    'UCbY-Oi636gF_kzAs9HVyKvw': 'Belyashik',
    'UCH3giddBL9GGgculbNTMe5Q': 'Universe of Fame',
    'UCVncLhqp3y1KDhHaJh3Wrrg': 'Shp1onkA',
    'UCTYqDIlPrb-GUWOohsv90nQ': 'Kt0Takoy?',
    'UCGoEPWV00IrmRdnWTYf3HJA': 'Uncommon',
    'UCO9vkOzYyHJYfTwvJwuL56A': 'Рандомный Канал Нарезок',
    'UCsS4z_j7eyt12t1wokJXOqA': 'Король Хикканов',
    'UCAjQd3mUYdaPDSFR01KJEYw': 'Никита Маерс',
    'UCsJfpTdAGDF7n2jISCkpLGg': 'GearPrime',
    'UCtnR2kwp66ytnM9AWt50yIQ': 'Витькин',
    'UCEjBZONzvfiUbG2lfncJKmQ': 'Герман Карпов 25',
    'UCoRoZAlBD3FaCIVAC8CXjLA': 'Никсыч',
    'UCNTCV2AsxALUWAYxTbxiZag': 'Legolasska',
    'UC0YUDNP3sMfSLXVIK1d8EOA': 'Alex Milya',
    'UCwiUh7_nAqwDRMJKIyegKTA': 'Больно. Но Смешно',
    'UCAvnUFQiGERhAqnnPRgBQyw': 'Just Tema',
    'UCQB_eP3LyOAt-PFZZzCQBhw': 'MillerMusic',
    'UChMbbyOAvxmrLi3SExSmG0g': 'HaHa Gamer GG',
    'UCzMmxpbT9MF6N62LSivy2rg': 'MiLlis',
    'UCsUpkk_F9ClS2F0BkHTsnhA': 'Rera seal',
    'UCfPJse-3skARpxs5LaSUiWA': 'TWITCH НАРЕЗКИ T2X2',
    'UC8WrBIrZBZ2gaEBNILijxPQ': 'T2x2 NEWS',
    'UC6kA_7pKR-_kmn8vVVe9xNg': 'T2X2 | CUT',
    'UCx8ZW-3_NAvgpRN18Ajm8Dg': 'T2x2 Live',
    'UCPSvj4dXjnigdx4lZzPiBuA': 'Нарезка Solek',
    'UC_yvQhmimAyunkFvvuTkYFA': 'ХваноРезки',
    'UCmFE8t3HzPArfPCkvWflHGQ': 'FrostoRezka',
    'UCDDbl3iEIpN8jhFRwr7vdaQ': 'EASTERCAKE Highlights',
}

OUT = Path('final_candidate_grids')
OUT.mkdir(exist_ok=True)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.5',
}
PATTERNS = [
    re.compile(r'"entityId":"shorts-shelf-item-([A-Za-z0-9_-]{11})"'),
    re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"'),
]
URL_RE = re.compile(r'https?://[^"\\\s<>]+', re.I)
AT_RE = re.compile(r'(?i)(?:telegram|телеграм|тг|tg|связь|реклама|сотрудничество)[^@\n]{0,80}@([A-Za-z0-9_]{5,32})')


def safe(value: str) -> str:
    return re.sub(r'[^A-Za-zА-Яа-я0-9_-]+', '_', value).strip('_')[:70]


def normalize_raw(raw: str) -> str:
    text = raw
    for _ in range(4):
        text = html.unescape(text).replace('\\u0026', '&').replace('\\/', '/')
        text = unquote(text)
    return text


def expand_url(url: str) -> list[str]:
    results = [url.rstrip('.,;\"\'\'])}')]
    try:
        p = urlparse(url)
        qs = parse_qs(p.query)
        for key in ('q', 'url', 'u'):
            for value in qs.get(key, []):
                results.append(unquote(value))
    except Exception:
        pass
    return results


def is_personal(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    host = p.netloc.lower().replace('www.', '')
    path = p.path.strip('/')
    low = path.lower()
    if not path:
        return False
    if host in ('t.me', 'telegram.me'):
        return '/' not in path and not low.startswith(('+', 'joinchat', 's/', 'share', 'proxy')) and not low.endswith('bot')
    if host == 'vk.com':
        return '/' not in path and not low.startswith(('club', 'public', 'event', 'wall', 'video', 'clip', 'market', 'im'))
    return False


def fetch_channel(cid: str):
    texts = []
    statuses = []
    for suffix in ('shorts', 'about', ''):
        try:
            url = f'https://www.youtube.com/channel/{cid}/{suffix}?hl=ru&gl=RU'
            r = requests.get(url, headers=HEADERS, timeout=35)
            statuses.append([suffix or 'home', r.status_code, len(r.text)])
            if r.ok:
                texts.append(r.text)
        except Exception as exc:
            statuses.append([suffix or 'home', 'ERR', repr(exc)])
    raw = normalize_raw('\n'.join(texts))
    ids = []
    for pat in PATTERNS:
        for vid in pat.findall(raw):
            if vid not in ids:
                ids.append(vid)
    contacts = []
    all_urls = []
    for found in URL_RE.findall(raw):
        all_urls.extend(expand_url(found))
    for user in AT_RE.findall(raw):
        all_urls.append(f'https://t.me/{user}')
    for link in all_urls:
        link = link.rstrip('.,;\"\'\'])}')
        if is_personal(link) and link not in contacts:
            contacts.append(link)
    return ids[:15], contacts, statuses


def image_for(vid: str):
    for name in ('oardefault.jpg', 'oar2.jpg', 'maxresdefault.jpg', 'hq720.jpg', 'hqdefault.jpg'):
        try:
            r = requests.get(f'https://i.ytimg.com/vi/{vid}/{name}', headers=HEADERS, timeout=25)
            if r.ok and len(r.content) > 3000:
                im = Image.open(BytesIO(r.content)).convert('RGB')
                if im.width > 100 and im.height > 100:
                    return im
        except Exception:
            pass
    return None


def build(cid: str, title: str):
    ids, contacts, statuses = fetch_channel(cid)
    cw, ch = 280, 510
    canvas = Image.new('RGB', (cw * 5, ch * 3 + 100), 'white')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((10, 8), f'{title} | {cid}', fill='black', font=font)
    draw.text((10, 28), 'contacts: ' + '; '.join(contacts), fill='black', font=font)
    draw.text((10, 48), f'https://www.youtube.com/channel/{cid}/shorts', fill='black', font=font)
    for i, vid in enumerate(ids):
        x = (i % 5) * cw
        y = 75 + (i // 5) * ch
        im = image_for(vid)
        if im:
            im = ImageOps.fit(im, (cw - 8, ch - 42), method=Image.Resampling.LANCZOS)
            canvas.paste(im, (x + 4, y + 4))
        draw.text((x + 5, y + ch - 31), f'{i + 1}. {vid}', fill='black', font=font)
    path = OUT / f'{safe(title)}_{cid}.jpg'
    canvas.save(path, quality=90)
    return {
        'channel_id': cid,
        'title': title,
        'contacts': contacts,
        'video_ids': ids,
        'statuses': statuses,
        'grid': str(path),
    }


rows = []
with ThreadPoolExecutor(max_workers=8) as ex:
    futures = {ex.submit(build, cid, title): cid for cid, title in CANDIDATES.items()}
    for i, future in enumerate(as_completed(futures), 1):
        cid = futures[future]
        try:
            row = future.result()
        except Exception as exc:
            row = {'channel_id': cid, 'title': CANDIDATES[cid], 'error': repr(exc)}
        rows.append(row)
        print(i, len(CANDIDATES), row.get('title'), len(row.get('video_ids') or []), row.get('contacts'), flush=True)

(OUT / 'final_candidate_info.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
