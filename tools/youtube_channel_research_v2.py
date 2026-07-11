#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import re
import statistics
import subprocess
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

OUT = Path("research_output_v2")
SHEETS = OUT / "sheets"
OUT.mkdir(exist_ok=True)
SHEETS.mkdir(exist_ok=True)
NOW = datetime.now(timezone.utc)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.7",
}

SEED_IDS = """
UCUHGwVMOJepO_LpVRS-h2-g UC8WrBIrZBZ2gaEBNILijxPQ UC6kA_7pKR-_kmn8vVVe9xNg UCx8ZW-3_NAvgpRN18Ajm8Dg
UCPQpo19okowp1iEvtZRKtDA UCWAs-6bnfm4lvCphK68m7YQ UCT24rCYSvYpK5vy5msKz0ug UCxT4GMoXibXpN4Osd29y9pA
UCiiqjbw9FKaVSHyE6kOncKQ UC7CcvHwKSdBsWatWf6Bkxaw UCCfCgk2ktkKiHnc3y1ejx1w UCPSvj4dXjnigdx4lZzPiBuA
UCR6AVYAAA3Dij6-HOVf9SxA UCm1ntxZX0XAEydR70UABOUw UC8IWXgUQ_Btgh5D5zqRbi8w UC6m3Sqhu-8Bp2pG6ZyzMUwQ
UCkpDxeWMe-XsVQozoqhFuZw UCVzSjpkPkhayIhYM390C2-A UCZ8LsN8Odr0NeLuAKq0lAqA UCbAZ88oxngstI6uMJujrZjg
UCq5cMlXa_G9ipcyidhJkBnw UCs9rMOxohsWgQgn-GyHaalA UCnoTbl8YnTqU-bD1gPHTJ3g UCdLcpkzuiNmdba6c4UVWKyw
UCNC4w-0Ag7La8KTQ023kJFQ UCDDbl3iEIpN8jhFRwr7vdaQ UCmfoC2xVjuIwdp9agm9RQuA UCmFE8t3HzPArfPCkvWflHGQ
UCKJURvnQLcZJjoCE-lIu1Qw UC9Seuv1mUvolm-KASUppAnw UCkzd_HjQCHmhESZuvdejQfg UCI4XxMwT2GLMmKMVdlTVM-g
UCe12nc0-fOp3cMykwozZqrA UCSSeKGPdKfsj_OadkUSOMvQ UCBwSh2pfL8z5CkzqGOL1lWA UCvITV9WYMlsfWysV7HPGJoA
UCqblvcammV43eW37TQeMxVg UC_yvQhmimAyunkFvvuTkYFA UCPc6_TH0eOBYSHTiNZFfAug UCOGTecb225mPS-9jjhV9Abg
UCshgmSEdzRKhsow1j4dxMnw UCucF5KKaRdhYLBGICA7Jo1Q UC-VtIdT4TcsNDDdkjRTAlyg UCfPJse-3skARpxs5LaSUiWA
UCWFet2M-JDh6XL-8RfPoFDg UCf5QtXFu7aJfUTob5lyhzMA UCh6hcm8NJigfOMRbshnViCA UCnUy7a5Z9D2XBu5VZEAelRw
UCV9SkXB1Ip1NRg_C8P-qzqQ UCRK_vW23nfR0yiYk3LnCQwA UC81EJt9DVCT4Bp8N9ZVGXwg UCRr5Ecr1Jya5nF74tK2tmPA
UCTNv134tW76Kl1yesZ7rLuA UCEdd1TTMh1c5MT-gra__9hA UCnQx9xmG_U82uPCj3-vxiVQ UCsUpkk_F9ClS2F0BkHTsnhA
UC5KD_Q_rS3lVfP_hMDZ3HwQ
""".split()

CREATORS = [
    "t2x2", "стинт", "папич", "бустер", "парадеевич", "кореш", "эвелон", "мазелов", "даня кашин",
    "фрост", "зубарев", "винди", "генсуха", "рей", "сасавот", "плохой парень", "меллстрой", "жожо",
    "хесус", "bratishkinoff", "exile", "shadowkek", "skywhywalker", "rostislav", "drakeoffc", "solek",
    "eastercake", "arthas", "mokrivskyi", "братишкин", "пятерка", "куертов", "лавеллас", "дк",
    "хозяева", "sasavot", "paradeevich", "koreshzy", "buster", "evelone", "mazellov", "stint",
]
QUERIES = [f"{name} нарезки shorts" for name in CREATORS]
QUERIES += [f"{name} лучшие моменты shorts" for name in CREATORS[:25]]
QUERIES += [
    "нарезки стримеров shorts русский", "лучшие моменты стримов shorts русский", "твич нарезки shorts русский",
    "стример сверху игра снизу shorts русский", "говорящий человек сверху minecraft снизу shorts",
    "подкаст сверху gameplay снизу shorts русский", "реакция сверху subway surfers снизу shorts русский",
    "истории minecraft parkour shorts русский", "twitch moments shorts русский нарезки",
    "русские стримеры split screen shorts", "нарезки стримеров minecraft снизу", "стримерские рофлы shorts",
    "нарезки твич моментов shorts", "фан канал стримера shorts русский", "стример реакции shorts русский",
]

TG_RE = re.compile(r"https?://(?:www\.)?(?:t\.me|telegram\.me)/[A-Za-z0-9_+./-]+", re.I)
VK_RE = re.compile(r"https?://(?:www\.)?vk\.com/[A-Za-z0-9_.-]+", re.I)
AT_RE = re.compile(r"(?i)(?:telegram|телеграм|тг|tg|связь|реклама)[^@\n]{0,45}@([A-Za-z0-9_]{5,32})")
VPN_RE = re.compile(r"(?i)\b(vpn|proxy|прокси|впн|outline|amnezia|vless|wireguard)\b")
CHANNEL_RE = re.compile(r"UC[A-Za-z0-9_-]{20,}")
VIDEO_RE = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')


def run_json(args: list[str], timeout: int = 180) -> dict[str, Any] | None:
    cmd = ["yt-dlp", "--skip-download", "--quiet", "--no-warnings", "--ignore-errors",
           "--socket-timeout", "20", "--retries", "2", "--extractor-retries", "2", *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        text = p.stdout.strip()
        return json.loads(text) if text else None
    except Exception:
        return None


def parse_count(value: Any) -> int | None:
    if value is None: return None
    if isinstance(value, (int, float)): return int(value)
    s = str(value).lower().replace("\u00a0", " ").replace(" ", "").replace(",", ".")
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([kmкмтысмил]*)", s)
    if not m: return None
    n = float(m.group(1)); u = m.group(2)
    if u.startswith(("k", "к", "тыс")): n *= 1000
    elif u.startswith(("m", "м", "мил")): n *= 1_000_000
    return int(n)


def clean_url(raw: str) -> str:
    s = html.unescape(raw).replace("\\u0026", "&").replace("\\/", "/")
    for _ in range(4):
        nxt = urllib.parse.unquote(s)
        if nxt == s: break
        s = nxt
    if "youtube.com/redirect" in s:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(s).query).get("q")
        if q: s = q[0]
    return s.rstrip(".,;)'\"]}")


def personalish(link: str) -> bool:
    u = urllib.parse.urlparse(link); path = u.path.strip("/"); low = path.lower()
    if not path: return False
    if "t.me" in u.netloc.lower() or "telegram.me" in u.netloc.lower():
        if low.startswith(("+", "joinchat", "s/", "share", "addstickers", "proxy", "socks")): return False
        if low.endswith("bot") or "/" in path: return False
        return True
    if "vk.com" in u.netloc.lower():
        if low.startswith(("club", "public", "event", "wall", "video", "clip", "market")): return False
        return "/" not in path
    return False


def subscriber_from_html(raw: str) -> int | None:
    patterns = [
        r'"subscriberCountText":\{"simpleText":"([^"]+)"',
        r'"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"',
        r'([0-9.,]+\s*(?:K|M|тыс\.?|млн)?)\s+(?:subscribers|подписчик)',
    ]
    for pat in patterns:
        m = re.search(pat, raw, re.I)
        if m:
            n = parse_count(m.group(1))
            if n is not None: return n
    return None


def fetch_channel(cid: str) -> dict[str, Any]:
    pages = []
    for suffix in ("shorts", "about"):
        try:
            r = requests.get(f"https://www.youtube.com/channel/{cid}/{suffix}?hl=ru&gl=RU", headers=HEADERS, timeout=30)
            if r.ok: pages.append(r.text)
        except Exception:
            pass
    raw = "\n".join(pages); decoded = clean_url(raw)
    links: list[str] = []
    for pattern in (TG_RE, VK_RE):
        for match in pattern.findall(decoded):
            link = clean_url(match)
            if personalish(link) and link not in links: links.append(link)
    for user in AT_RE.findall(decoded):
        link = f"https://t.me/{user}"
        if personalish(link) and link not in links: links.append(link)
    title = ""
    for pat in (r'<meta property="og:title" content="([^"]+)', r'"channelName":"([^"]+)', r'"title":"([^"]+)"'):
        m = re.search(pat, raw)
        if m:
            title = html.unescape(m.group(1)); break
    vids: list[str] = []
    for vid in VIDEO_RE.findall(raw):
        if vid not in vids: vids.append(vid)
    key_m = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', raw)
    ver_m = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', raw)
    return {
        "raw": raw, "title": title, "subscribers": subscriber_from_html(raw), "contacts": links,
        "video_ids": vids[:60], "api_key": key_m.group(1) if key_m else "",
        "client_version": ver_m.group(1) if ver_m else "2.20260709.01.00",
    }


def player_metadata(video_id: str, cid: str, api_key: str, client_version: str) -> dict[str, Any] | None:
    if not api_key: return None
    body = {
        "context": {"client": {"clientName": "WEB", "clientVersion": client_version, "hl": "ru", "gl": "RU"}},
        "videoId": video_id,
        "contentCheckOk": True,
        "racyCheckOk": True,
    }
    try:
        r = requests.post(f"https://www.youtube.com/youtubei/v1/player?key={api_key}", headers={**HEADERS, "Content-Type": "application/json"}, json=body, timeout=30)
        if not r.ok: return None
        data = r.json(); vd = data.get("videoDetails") or {}
        if vd.get("channelId") != cid: return None
        micro = ((data.get("microformat") or {}).get("playerMicroformatRenderer") or {})
        publish = micro.get("publishDate") or micro.get("uploadDate") or ""
        dt = None
        if publish:
            try: dt = datetime.fromisoformat(str(publish).replace("Z", "+00:00"))
            except Exception:
                try: dt = datetime.strptime(str(publish)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception: pass
        return {
            "id": video_id,
            "title": vd.get("title") or "",
            "description": vd.get("shortDescription") or "",
            "view_count": int(vd.get("viewCount") or 0),
            "duration": int(vd.get("lengthSeconds") or 0),
            "publish_date": dt.isoformat() if dt else "",
            "timestamp": int(dt.timestamp()) if dt else None,
        }
    except Exception:
        return None


def discover_query(query: str) -> set[str]:
    data = run_json(["--flat-playlist", "--playlist-end", "30", "--dump-single-json", f"ytsearch30:{query}"], 180)
    out: set[str] = set()
    if not data: return out
    for entry in data.get("entries") or []:
        if not isinstance(entry, dict): continue
        for key in ("channel_id", "uploader_id"):
            value = entry.get(key)
            if isinstance(value, str) and CHANNEL_RE.fullmatch(value): out.add(value)
        for key in ("channel_url", "uploader_url"):
            match = CHANNEL_RE.search(str(entry.get(key) or ""))
            if match: out.add(match.group(0))
    return out


def dt_from(v: dict[str, Any]) -> datetime | None:
    if v.get("timestamp"):
        try: return datetime.fromtimestamp(float(v["timestamp"]), timezone.utc)
        except Exception: pass
    return None


def safe_name(value: str) -> str:
    return (re.sub(r"[^A-Za-zА-Яа-я0-9_-]+", "_", value).strip("_")[:80] or "channel")


def get_thumb(video_id: str) -> Image.Image | None:
    for name in ("oardefault.jpg", "oar2.jpg", "maxresdefault.jpg", "hq720.jpg", "hqdefault.jpg"):
        try:
            r = requests.get(f"https://i.ytimg.com/vi/{video_id}/{name}", headers=HEADERS, timeout=20)
            if r.ok and len(r.content) > 3500:
                image = Image.open(BytesIO(r.content)).convert("RGB")
                if image.width > 100 and image.height > 100: return image
        except Exception:
            pass
    return None


def make_sheet(row: dict[str, Any], videos: list[dict[str, Any]]) -> str:
    cw, ch = 300, 520
    canvas = Image.new("RGB", (cw * 5, ch * 3 + 105), "white")
    draw = ImageDraw.Draw(canvas); font = ImageFont.load_default()
    heading = (f"{row['title']} | subs {row['subscribers']} | 7d {row['videos_7d']} | 14d {row['videos_14d']} | "
               f"median {row['median_views']} | >=1500 {row['above_1500']}/15 | <=60s {row['under_60']}/15")
    draw.text((10, 10), heading[:210], fill="black", font=font)
    draw.text((10, 32), f"contacts: {row['contacts']}", fill="black", font=font)
    draw.text((10, 52), row["url"], fill="black", font=font)
    for i, video in enumerate(videos[:15]):
        x, y = (i % 5) * cw, 80 + (i // 5) * ch
        image = get_thumb(video["id"])
        if image:
            image = ImageOps.fit(image, (cw - 8, ch - 72), method=Image.Resampling.LANCZOS)
            canvas.paste(image, (x + 4, y + 4))
        date = dt_from(video)
        label = f"{i+1}. {date.date().isoformat() if date else '?'} | {video['view_count']} | {video['duration']}s\n{video['title'][:46]}"
        draw.multiline_text((x + 5, y + ch - 65), label, fill="black", font=font, spacing=2)
    path = SHEETS / f"{safe_name(row['title'])}_{row['channel_id']}.jpg"
    canvas.save(path, quality=90)
    return str(path)


def inspect_channel(cid: str) -> dict[str, Any]:
    channel = fetch_channel(cid)
    row: dict[str, Any] = {
        "channel_id": cid,
        "title": channel["title"] or cid,
        "url": f"https://www.youtube.com/channel/{cid}/shorts",
        "subscribers": channel["subscribers"] or 0,
        "contacts": "; ".join(channel["contacts"]),
        "short_ids_found": len(channel["video_ids"]),
    }
    if not channel["contacts"]:
        row["status"] = "NO_PERSONAL_CONTACT_CANDIDATE"; return row
    if not row["subscribers"] or not 5000 <= row["subscribers"] <= 50000:
        row["status"] = "SUBSCRIBERS_FAIL"; return row
    if len(channel["video_ids"]) < 8 or not channel["api_key"]:
        row["status"] = "TOO_FEW_SHORT_IDS"; return row
    videos: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(player_metadata, vid, cid, channel["api_key"], channel["client_version"]) for vid in channel["video_ids"][:35]]
        for future in as_completed(futures):
            value = future.result()
            if value: videos.append(value)
    videos.sort(key=lambda v: v.get("timestamp") or 0, reverse=True)
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for video in videos:
        if video["id"] not in seen:
            unique.append(video); seen.add(video["id"])
    videos = unique[:15]
    if len(videos) < 10:
        row["status"] = "TOO_FEW_PLAYER_METADATA"; row["metadata_count"] = len(videos); return row
    d7, d14 = NOW - timedelta(days=7), NOW - timedelta(days=14)
    dates = [dt_from(v) for v in videos]
    views = [v["view_count"] for v in videos]
    row.update({
        "videos_checked": len(videos),
        "videos_7d": sum(1 for d in dates if d and d >= d7),
        "videos_14d": sum(1 for d in dates if d and d >= d14),
        "median_views": int(statistics.median(views)),
        "above_1500": sum(1 for value in views if value >= 1500),
        "under_60": sum(1 for v in videos if 0 < v["duration"] <= 60),
        "vpn_text_hits": ";".join(v["id"] for v in videos if VPN_RE.search(v["title"] + " " + v["description"])),
    })
    row["activity_pass"] = int(row["videos_7d"] >= 3 or row["videos_14d"] >= 6)
    row["views_pass"] = int(row["median_views"] >= 2000 and row["above_1500"] >= 8)
    row["duration_pass"] = int(row["under_60"] >= 10)
    if row["activity_pass"] and row["views_pass"] and row["duration_pass"] and not row["vpn_text_hits"]:
        row["status"] = "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED"
        row["sheet"] = make_sheet(row, videos)
        with (OUT / "candidate_videos.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps({"channel": row, "videos": videos}, ensure_ascii=False) + "\n")
    else:
        row["status"] = "METRICS_DURATION_OR_VPN_FAIL"
    return row


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def main() -> None:
    discovered = set(SEED_IDS)
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(discover_query, query): query for query in QUERIES}
        for future in as_completed(futures):
            try: discovered.update(future.result())
            except Exception: pass
    discovered = set(sorted(discovered)[:650])
    (OUT / "discovered_ids.txt").write_text("\n".join(sorted(discovered)), encoding="utf-8")
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(inspect_channel, cid): cid for cid in sorted(discovered)}
        for index, future in enumerate(as_completed(futures), 1):
            cid = futures[future]
            try: row = future.result()
            except Exception as error: row = {"channel_id": cid, "status": "ERROR", "error": repr(error)}
            rows.append(row)
            print(index, len(discovered), row.get("status"), row.get("title", cid), flush=True)
    rows.sort(key=lambda row: (row.get("status") != "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED", -(row.get("median_views") or 0), row.get("title") or ""))
    qualified = [row for row in rows if row.get("status") == "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED"]
    write_csv(OUT / "all_checked.csv", rows); write_csv(OUT / "qualified_numeric_contact.csv", qualified)
    counts: dict[str, int] = {}
    for row in rows: counts[row.get("status", "UNKNOWN")] = counts.get(row.get("status", "UNKNOWN"), 0) + 1
    summary = {"generated_at": NOW.isoformat(), "queries": len(QUERIES), "channels_discovered": len(discovered),
               "channels_checked": len(rows), "numeric_contact_pass": len(qualified), "status_counts": counts}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
