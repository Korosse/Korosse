#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import os
import re
import statistics
import subprocess
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO

OUT = Path("research_output")
SHEETS = OUT / "sheets"
OUT.mkdir(exist_ok=True)
SHEETS.mkdir(exist_ok=True)
NOW = datetime.now(timezone.utc)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.7"}

SEED_IDS = """
UCUHGwVMOJepO_LpVRS-h2-g
UC8WrBIrZBZ2gaEBNILijxPQ
UC6kA_7pKR-_kmn8vVVe9xNg
UCx8ZW-3_NAvgpRN18Ajm8Dg
UCPQpo19okowp1iEvtZRKtDA
UCWAs-6bnfm4lvCphK68m7YQ
UCT24rCYSvYpK5vy5msKz0ug
UCxT4GMoXibXpN4Osd29y9pA
UCiiqjbw9FKaVSHyE6kOncKQ
UC7CcvHwKSdBsWatWf6Bkxaw
UCCfCgk2ktkKiHnc3y1ejx1w
UCPSvj4dXjnigdx4lZzPiBuA
UCR6AVYAAA3Dij6-HOVf9SxA
UCm1ntxZX0XAEydR70UABOUw
UC8IWXgUQ_Btgh5D5zqRbi8w
UC6m3Sqhu-8Bp2pG6ZyzMUwQ
UCkpDxeWMe-XsVQozoqhFuZw
UCVzSjpkPkhayIhYM390C2-A
UCZ8LsN8Odr0NeLuAKq0lAqA
UCbAZ88oxngstI6uMJujrZjg
UCq5cMlXa_G9ipcyidhJkBnw
UCs9rMOxohsWgQgn-GyHaalA
UCnoTbl8YnTqU-bD1gPHTJ3g
UCdLcpkzuiNmdba6c4UVWKyw
UCNC4w-0Ag7La8KTQ023kJFQ
UCDDbl3iEIpN8jhFRwr7vdaQ
UCmfoC2xVjuIwdp9agm9RQuA
UCmFE8t3HzPArfPCkvWflHGQ
UCKJURvnQLcZJjoCE-lIu1Qw
UC9Seuv1mUvolm-KASUppAnw
UCkzd_HjQCHmhESZuvdejQfg
UCI4XxMwT2GLMmKMVdlTVM-g
UCe12nc0-fOp3cMykwozZqrA
UCSSeKGPdKfsj_OadkUSOMvQ
UCBwSh2pfL8z5CkzqGOL1lWA
UCvITV9WYMlsfWysV7HPGJoA
UCqblvcammV43eW37TQeMxVg
UC_yvQhmimAyunkFvvuTkYFA
UCPc6_TH0eOBYSHTiNZFfAug
UCOGTecb225mPS-9jjhV9Abg
UCshgmSEdzRKhsow1j4dxMnw
UCucF5KKaRdhYLBGICA7Jo1Q
UC-VtIdT4TcsNDDdkjRTAlyg
UCfPJse-3skARpxs5LaSUiWA
UCWFet2M-JDh6XL-8RfPoFDg
UCf5QtXFu7aJfUTob5lyhzMA
UCh6hcm8NJigfOMRbshnViCA
UCnUy7a5Z9D2XBu5VZEAelRw
UCV9SkXB1Ip1NRg_C8P-qzqQ
UCRK_vW23nfR0yiYk3LnCQwA
UC81EJt9DVCT4Bp8N9ZVGXwg
UCRr5Ecr1Jya5nF74tK2tmPA
UCTNv134tW76Kl1yesZ7rLuA
UCEdd1TTMh1c5MT-gra__9hA
UCnQx9xmG_U82uPCj3-vxiVQ
UCsUpkk_F9ClS2F0BkHTsnhA
UC5KD_Q_rS3lVfP_hMDZ3HwQ
""".split()

CREATORS = [
    "t2x2", "стинт", "папич", "бустер", "парадеевич", "кореш", "эвелон",
    "мазелов", "даня кашин", "фрост", "зубарев", "винди", "генсуха", "рей",
    "сасавот", "плохой парень", "дота стример", "твич стример", "меллстрой",
    "жожо", "хесус", "bratishkinoff", "exile", "shadowkek", "skywhywalker",
]
QUERIES = [f"{x} нарезки shorts" for x in CREATORS] + [
    "нарезки стримеров shorts русский",
    "лучшие моменты стримов shorts русский",
    "стример сверху игра снизу shorts русский",
    "говорящий человек сверху minecraft снизу shorts",
    "подкаст сверху gameplay снизу shorts русский",
    "реакция сверху subway surfers снизу shorts русский",
    "истории minecraft parkour shorts русский",
    "twitch moments shorts русский нарезки",
    "русские стримеры split screen shorts",
    "нарезки стримеров minecraft снизу",
]

TG_RE = re.compile(r"https?://(?:www\.)?(?:t\.me|telegram\.me)/[A-Za-z0-9_+./-]+", re.I)
VK_RE = re.compile(r"https?://(?:www\.)?vk\.com/[A-Za-z0-9_.-]+", re.I)
AT_RE = re.compile(r"(?i)(?:telegram|телеграм|тг|tg)[^@\n]{0,35}@([A-Za-z0-9_]{5,32})")
VPN_RE = re.compile(r"(?i)\b(vpn|proxy|прокси|впн|outline|amnezia|vless|wireguard)\b")


def run_json(args: list[str], timeout: int = 150) -> dict[str, Any] | None:
    cmd = [
        "yt-dlp", "--skip-download", "--quiet", "--no-warnings", "--ignore-errors",
        "--socket-timeout", "20", "--retries", "2", "--extractor-retries", "2",
        "--extractor-args", "youtube:player_client=web,mweb", *args,
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        text = p.stdout.strip()
        if not text:
            return None
        return json.loads(text)
    except Exception:
        return None


def run_json_lines(args: list[str], timeout: int = 300) -> list[dict[str, Any]]:
    cmd = [
        "yt-dlp", "--skip-download", "--quiet", "--no-warnings", "--ignore-errors",
        "--socket-timeout", "20", "--retries", "2", "--extractor-retries", "2",
        "--extractor-args", "youtube:player_client=web,mweb", *args,
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = []
        for line in p.stdout.splitlines():
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    out.append(obj)
            except Exception:
                pass
        return out
    except Exception:
        return []


def parse_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).lower().replace("\u00a0", " ").replace(" ", "").replace(",", ".")
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([kmкмтысмил]*)", s)
    if not m:
        return None
    n = float(m.group(1)); u = m.group(2)
    if u.startswith(("k", "к", "тыс")): n *= 1000
    elif u.startswith(("m", "м", "мил")): n *= 1_000_000
    return int(n)


def clean_url(raw: str) -> str:
    s = html.unescape(raw).replace("\\u0026", "&").replace("\\/", "/")
    for _ in range(3):
        s2 = urllib.parse.unquote(s)
        if s2 == s: break
        s = s2
    if "youtube.com/redirect" in s:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(s).query).get("q")
        if q: s = q[0]
    return s.rstrip(".,;)'\"]}")


def personalish(link: str) -> bool:
    u = urllib.parse.urlparse(link)
    path = u.path.strip("/")
    if not path: return False
    low = path.lower()
    if "t.me" in u.netloc.lower() or "telegram.me" in u.netloc.lower():
        if low.startswith(("+", "joinchat", "s/", "share", "addstickers", "proxy", "socks")): return False
        if low.endswith("bot"): return False
        return "/" not in path
    if "vk.com" in u.netloc.lower():
        if low.startswith(("club", "public", "event", "wall", "video", "clip")): return False
        return "/" not in path
    return False


def fetch_about(cid: str) -> tuple[str, list[str], str]:
    urls = [
        f"https://www.youtube.com/channel/{cid}/about?hl=ru&gl=RU",
        f"https://www.youtube.com/channel/{cid}/shorts?hl=ru&gl=RU",
    ]
    combined = ""
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.ok: combined += "\n" + r.text
        except Exception:
            pass
    decoded = clean_url(combined)
    links = []
    for pattern in (TG_RE, VK_RE):
        for m in pattern.findall(decoded):
            link = clean_url(m)
            if link not in links and personalish(link): links.append(link)
    for user in AT_RE.findall(decoded):
        link = f"https://t.me/{user}"
        if personalish(link) and link not in links: links.append(link)
    title = ""
    for pat in [r'<meta property="og:title" content="([^"]+)', r'"channelName":"([^"]+)']:
        m = re.search(pat, combined)
        if m:
            title = html.unescape(m.group(1)); break
    return combined, links, title


def subscriber_from_html(raw: str) -> int | None:
    pats = [
        r'"subscriberCountText":\{"simpleText":"([^"]+)"',
        r'"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"',
        r'([0-9.,]+\s*(?:K|M|тыс\.?|млн)?)\s+(?:subscribers|подписчик)',
    ]
    for pat in pats:
        m = re.search(pat, raw, re.I)
        if m:
            n = parse_count(m.group(1))
            if n is not None: return n
    return None


def discover_query(query: str) -> set[str]:
    data = run_json(["--flat-playlist", "--playlist-end", "25", "--dump-single-json", f"ytsearch25:{query}"], 180)
    out: set[str] = set()
    if not data: return out
    for e in data.get("entries") or []:
        if not isinstance(e, dict): continue
        for key in ("channel_id", "uploader_id"):
            v = e.get(key)
            if isinstance(v, str) and v.startswith("UC"): out.add(v)
        url = str(e.get("channel_url") or e.get("uploader_url") or "")
        m = re.search(r"/channel/(UC[\w-]+)", url)
        if m: out.add(m.group(1))
    return out


def get_flat(cid: str) -> dict[str, Any] | None:
    return run_json([
        "--flat-playlist", "--playlist-end", "20", "--dump-single-json",
        f"https://www.youtube.com/channel/{cid}/shorts"
    ], 180)


def date_from_video(v: dict[str, Any]) -> datetime | None:
    ts = v.get("timestamp") or v.get("release_timestamp")
    if ts:
        try: return datetime.fromtimestamp(float(ts), timezone.utc)
        except Exception: pass
    d = str(v.get("upload_date") or "")
    if len(d) == 8 and d.isdigit():
        try: return datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
        except Exception: pass
    return None


def safe_name(s: str) -> str:
    s = re.sub(r"[^A-Za-zА-Яа-я0-9_-]+", "_", s).strip("_")
    return s[:80] or "channel"


def thumbnail(video_id: str) -> Image.Image | None:
    for name in ("oardefault.jpg", "oar2.jpg", "maxresdefault.jpg", "hq720.jpg", "hqdefault.jpg"):
        try:
            r = requests.get(f"https://i.ytimg.com/vi/{video_id}/{name}", headers=HEADERS, timeout=20)
            if r.ok and len(r.content) > 4000:
                im = Image.open(BytesIO(r.content)).convert("RGB")
                if im.width > 100 and im.height > 100: return im
        except Exception:
            pass
    return None


def make_sheet(title: str, cid: str, videos: list[dict[str, Any]], row: dict[str, Any]) -> str:
    cell_w, cell_h = 300, 520
    canvas = Image.new("RGB", (cell_w * 5, cell_h * 3 + 110), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    heading = f"{title} | subs {row.get('subscribers')} | 7d {row.get('videos_7d')} | 14d {row.get('videos_14d')} | median {row.get('median_views')} | >=1500 {row.get('above_1500')}"
    draw.text((12, 10), heading[:190], fill="black", font=font)
    draw.text((12, 32), f"contacts: {row.get('contacts','')} | {cid}", fill="black", font=font)
    for i, v in enumerate(videos[:15]):
        x = (i % 5) * cell_w; y = 80 + (i // 5) * cell_h
        im = thumbnail(str(v.get("id") or ""))
        if im:
            im = ImageOps.fit(im, (cell_w - 8, cell_h - 70), method=Image.Resampling.LANCZOS)
            canvas.paste(im, (x + 4, y + 4))
        views = v.get("view_count") or 0
        dt = date_from_video(v)
        label = f"{i+1}. {dt.date().isoformat() if dt else '?'} | {views} views\n{str(v.get('title') or '')[:46]}"
        draw.multiline_text((x + 5, y + cell_h - 62), label, fill="black", font=font, spacing=2)
    path = SHEETS / f"{safe_name(title)}_{cid}.jpg"
    canvas.save(path, quality=88)
    return str(path)


def inspect_channel(cid: str) -> dict[str, Any]:
    raw, contacts, html_title = fetch_about(cid)
    flat = get_flat(cid)
    if not flat:
        return {"channel_id": cid, "status": "NO_SHORTS_DATA", "contacts": "; ".join(contacts)}
    title = str(flat.get("channel") or flat.get("uploader") or flat.get("title") or html_title or cid)
    subs = parse_count(flat.get("channel_follower_count") or flat.get("uploader_follower_count")) or subscriber_from_html(raw)
    entries = [e for e in (flat.get("entries") or []) if isinstance(e, dict) and e.get("id")]
    base = {
        "channel_id": cid,
        "title": title,
        "url": f"https://www.youtube.com/channel/{cid}/shorts",
        "subscribers": subs or 0,
        "contacts": "; ".join(contacts),
        "shorts_flat": len(entries),
    }
    if not contacts:
        base["status"] = "NO_PERSONAL_CONTACT_CANDIDATE"; return base
    if not subs or not (5000 <= subs <= 50000):
        base["status"] = "SUBSCRIBERS_FAIL"; return base
    videos = run_json_lines([
        "--playlist-end", "15", "--dump-json",
        f"https://www.youtube.com/channel/{cid}/shorts"
    ], 480)
    videos = [v for v in videos if v.get("id")][:15]
    if len(videos) < 8:
        base["status"] = "TOO_FEW_VIDEO_METADATA"; return base
    d7 = NOW - timedelta(days=7); d14 = NOW - timedelta(days=14)
    dates = [date_from_video(v) for v in videos]
    v7 = sum(1 for d in dates if d and d >= d7)
    v14 = sum(1 for d in dates if d and d >= d14)
    views = [int(v.get("view_count") or 0) for v in videos]
    median_views = int(statistics.median(views)) if views else 0
    above = sum(1 for x in views if x >= 1500)
    vpn_text = []
    for v in videos:
        text = f"{v.get('title','')} {v.get('description','')}"
        if VPN_RE.search(text): vpn_text.append(str(v.get("id")))
    base.update({
        "videos_7d": v7,
        "videos_14d": v14,
        "median_views": median_views,
        "above_1500": above,
        "videos_checked": len(videos),
        "vpn_text_hits": ";".join(vpn_text),
        "activity_pass": int(v7 >= 3 or v14 >= 6),
        "views_pass": int(median_views >= 2000 and above >= 8),
    })
    if base["activity_pass"] and base["views_pass"] and not vpn_text:
        base["status"] = "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED"
        base["sheet"] = make_sheet(title, cid, videos, base)
        with open(OUT / "video_metadata.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"channel": base, "videos": videos}, ensure_ascii=False) + "\n")
    else:
        base["status"] = "METRICS_OR_VPN_TEXT_FAIL"
    return base


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = []
    for row in rows:
        for k in row:
            if k not in keys: keys.append(k)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)


def main() -> None:
    discovered = set(SEED_IDS)
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(discover_query, q): q for q in QUERIES}
        for fut in as_completed(futs):
            try: discovered.update(fut.result())
            except Exception: pass
    discovered = set(list(discovered)[:260])
    (OUT / "discovered_ids.txt").write_text("\n".join(sorted(discovered)), encoding="utf-8")
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(inspect_channel, cid): cid for cid in sorted(discovered)}
        for i, fut in enumerate(as_completed(futs), 1):
            cid = futs[fut]
            try: row = fut.result()
            except Exception as e: row = {"channel_id": cid, "status": "ERROR", "error": repr(e)}
            rows.append(row)
            print(i, len(discovered), row.get("status"), row.get("title", cid), flush=True)
    rows.sort(key=lambda r: (
        r.get("status") != "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED",
        -(r.get("median_views") or 0),
        r.get("title") or "",
    ))
    write_csv(OUT / "all_checked.csv", rows)
    qualified = [r for r in rows if r.get("status") == "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED"]
    write_csv(OUT / "qualified_numeric_contact.csv", qualified)
    summary = {
        "generated_at": NOW.isoformat(),
        "queries": len(QUERIES),
        "channels_discovered": len(discovered),
        "channels_checked": len(rows),
        "numeric_contact_pass": len(qualified),
        "status_counts": {},
    }
    for r in rows:
        summary["status_counts"][r.get("status", "UNKNOWN")] = summary["status_counts"].get(r.get("status", "UNKNOWN"), 0) + 1
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
