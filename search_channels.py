from __future__ import annotations

import csv
import json
import re
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

OUT = Path("research_output")
OUT.mkdir(exist_ok=True)
SHEETS = OUT / "sheets"
SHEETS.mkdir(exist_ok=True)

QUERIES = [
    # Exact/near-exact hooks seen in the customer's reference channel
    "проблема российского образования тиньков shorts",
    "сколько хованский зарабатывает shorts",
    "просто шел домой арестовали shorts",
    "разогрев смешнее выступления романов shorts",
    "странный хлеб в америке shorts",
    "фреймтаймер попал в тюрьму shorts",
    "полина смачно ударилась в дверь shorts",
    "стинт смотрит фанаты сошли shorts",
    "шоу голос калечит детскую shorts",
    "россии лучшие рестораны поперечный shorts",
    "твое какое дело дружок shorts",
    "роботы рекламы следят за тобой shorts",
    # Format wording
    "нарезка подкаста minecraft parkour shorts русский",
    "подкаст minecraft parkour shorts русский",
    "подкаст gta parkour shorts русский",
    "интервью subway surfers shorts русский",
    "подкаст с геймплеем shorts русский",
    "фрагмент подкаста с геймплеем shorts",
    "субтитры подкаст геймплей shorts",
    "подкаст сверху геймплей снизу shorts",
    "интервью сверху майнкрафт снизу shorts",
    "нарезка интервью minecraft shorts русский",
    "цитаты из подкаста subway surfers shorts",
    "истории с геймплеем minecraft shorts русский",
    "говорящая голова minecraft parkour shorts",
    # Real speakers/shows and youth ecosystem
    "тиньков интервью shorts minecraft",
    "хованский интервью shorts gta",
    "поперечный интервью shorts minecraft",
    "мазеллов подкаст shorts gameplay",
    "парадеевич подкаст shorts gameplay",
    "меллстрой интервью shorts minecraft",
    "дк подкаст shorts minecraft",
    "стинт интервью shorts gameplay",
    "бустер интервью shorts minecraft",
    "эдвард бил подкаст shorts gameplay",
    "вписка нарезки shorts minecraft",
    "50 вопросов shorts minecraft parkour",
    "без души подкаст shorts gameplay",
    # Slang hooks, only as small exploration
    "он реально это сказал shorts русский",
    "последняя фраза убила shorts русский",
    "бро выдал базу shorts русский",
    "это жиза shorts подкаст",
    "мужики поймут shorts интервью",
]

DIRECT_MARKERS = ("minecraft", "gta", "subway", "геймп", "parkour", "паркур")
CONTACT_RE = re.compile(r"(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{4,})|(?:https?://)?vk\.com/([A-Za-z0-9_.-]+)|(?<![\w@])@([A-Za-z][A-Za-z0-9_]{4,})")
VPN_RE = re.compile(r"\b(vpn|впн|proxy|прокси|vless|xray|outline|amnezia|warp|обход блокиров)\b", re.I)
CYR_RE = re.compile(r"[А-Яа-яЁё]")


def ydl_opts(flat=False, playlistend=None):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
        "retries": 2,
        "socket_timeout": 20,
        "extractor_retries": 2,
        "noplaylist": False,
        "http_headers": {"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5"},
    }
    if flat:
        opts["extract_flat"] = "in_playlist"
    if playlistend:
        opts["playlistend"] = playlistend
    return opts


def search_query(query: str, n: int = 25):
    with YoutubeDL(ydl_opts(flat=True)) as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{query}", download=False) or {}
    out = []
    for e in info.get("entries") or []:
        if not e:
            continue
        cid = e.get("channel_id") or e.get("uploader_id")
        vid = e.get("id")
        if not cid or not vid:
            continue
        out.append({
            "channel_id": cid,
            "video_id": vid,
            "channel": e.get("channel") or e.get("uploader") or "",
            "title": e.get("title") or "",
            "duration": e.get("duration"),
            "view_count": e.get("view_count"),
            "query": query,
        })
    return out


def get_video(vid: str):
    try:
        with YoutubeDL(ydl_opts(flat=False)) as ydl:
            return ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False) or {}
    except Exception:
        return {}


def get_channel(cid: str, source_videos: list[str]):
    url = f"https://www.youtube.com/channel/{cid}/shorts"
    try:
        with YoutubeDL(ydl_opts(flat=True, playlistend=20)) as ydl:
            page = ydl.extract_info(url, download=False) or {}
    except Exception as exc:
        return {"channel_id": cid, "error": type(exc).__name__}

    entries = [e for e in (page.get("entries") or []) if e and e.get("id")]
    # Fetch up to 12 individual recent Shorts, plus source hits, to get reliable views/dates/descriptions.
    ids = []
    for v in source_videos + [e.get("id") for e in entries]:
        if v and v not in ids:
            ids.append(v)
    details = []
    for vid in ids[:12]:
        item = get_video(vid)
        if item:
            details.append(item)
        time.sleep(0.12)

    title = page.get("channel") or page.get("uploader") or (details[0].get("channel") if details else "") or ""
    desc = page.get("description") or page.get("channel_description") or ""
    subs = page.get("channel_follower_count") or page.get("uploader_follower_count")
    if not subs and details:
        subs = details[0].get("channel_follower_count") or details[0].get("uploader_follower_count")
    subs = int(subs or 0)

    now = datetime.now(timezone.utc).timestamp()
    recent14 = 0
    views = []
    short_ids = []
    all_text = [title, desc]
    for d in details:
        duration = d.get("duration")
        if duration and duration <= 65:
            short_ids.append(d.get("id"))
            vc = d.get("view_count")
            if isinstance(vc, (int, float)):
                views.append(int(vc))
            ts = d.get("timestamp") or d.get("release_timestamp")
            if ts and now - ts <= 14 * 86400:
                recent14 += 1
        all_text.extend([d.get("title") or "", d.get("description") or ""])

    text = "\n".join(all_text)
    cyr = len(CYR_RE.findall(text))
    letters = len(re.findall(r"[A-Za-zА-Яа-яЁё]", text))
    ru_score = cyr / max(1, letters)
    contacts = []
    for m in CONTACT_RE.finditer(text):
        if m.group(1):
            contacts.append("https://t.me/" + m.group(1))
        elif m.group(2):
            contacts.append("https://vk.com/" + m.group(2))
        elif m.group(3):
            handle = m.group(3)
            if handle.lower() not in {"youtube", "shorts", "instagram", "telegram"}:
                contacts.append("@" + handle)
    contacts = list(dict.fromkeys(contacts))[:10]

    median_views = int(statistics.median(views)) if views else 0
    return {
        "channel_id": cid,
        "channel": title,
        "channel_url": f"https://www.youtube.com/channel/{cid}/shorts",
        "subscribers": subs,
        "ru_score": round(ru_score, 3),
        "recent14": recent14,
        "shorts_checked": len(short_ids),
        "median_views": median_views,
        "views": views,
        "video_ids": short_ids,
        "source_video_ids": source_videos,
        "contacts": contacts,
        "text_vpn": bool(VPN_RE.search(text)),
        "description": desc[:1500],
        "titles": [d.get("title") or "" for d in details],
    }


def download_thumb(vid: str, path: Path):
    for name in ("maxresdefault.jpg", "oardefault.jpg", "hqdefault.jpg"):
        try:
            r = requests.get(f"https://i.ytimg.com/vi/{vid}/{name}", timeout=15)
            if r.status_code == 200 and len(r.content) > 5000:
                path.write_bytes(r.content)
                return True
        except Exception:
            pass
    return False


def make_sheet(record: dict, index: int):
    vids = record.get("video_ids") or record.get("source_video_ids") or []
    imgs = []
    for j, vid in enumerate(vids[:12]):
        p = OUT / f"tmp_{index}_{j}.jpg"
        if download_thumb(vid, p):
            try:
                im = Image.open(p).convert("RGB")
                imgs.append((vid, im))
            except Exception:
                pass
    if not imgs:
        return None
    cell_w, cell_h = 320, 260
    sheet = Image.new("RGB", (cell_w * 4, cell_h * 3 + 90), "white")
    draw = ImageDraw.Draw(sheet)
    header = f"{record.get('channel','')} | {record.get('subscribers',0)} subs | 14d:{record.get('recent14',0)} | med:{record.get('median_views',0)} | VPNtext:{record.get('text_vpn')}"
    draw.text((10, 10), header[:170], fill="black")
    draw.text((10, 36), record.get("channel_url", ""), fill="black")
    draw.text((10, 62), "contacts: " + ", ".join(record.get("contacts") or []), fill="black")
    for k, (vid, im) in enumerate(imgs):
        x = (k % 4) * cell_w
        y = 90 + (k // 4) * cell_h
        im.thumbnail((cell_w, cell_h - 25))
        sheet.paste(im, (x + (cell_w - im.width)//2, y))
        draw.text((x + 5, y + cell_h - 22), vid, fill="black")
    name = re.sub(r"[^A-Za-z0-9А-Яа-я_-]+", "_", record.get("channel") or record["channel_id"])[:70]
    out = SHEETS / f"{index:03d}_{name}.jpg"
    sheet.save(out, quality=88)
    for p in OUT.glob(f"tmp_{index}_*.jpg"):
        p.unlink(missing_ok=True)
    return str(out)


def main():
    hits = defaultdict(list)
    channel_names = {}
    errors = []
    for i, q in enumerate(QUERIES, 1):
        try:
            rows = search_query(q, 30)
        except Exception as exc:
            errors.append({"query": q, "error": repr(exc)})
            rows = []
        for row in rows:
            cid = row["channel_id"]
            hits[cid].append(row)
            if row.get("channel"):
                channel_names[cid] = row["channel"]
        print(f"SEARCH {i}/{len(QUERIES)}: {q} -> {len(rows)}", flush=True)
        time.sleep(0.2)

    def score(cid):
        rows = hits[cid]
        query_hits = len({r["query"] for r in rows})
        direct = sum(any(m in r["query"].lower() for m in DIRECT_MARKERS) for r in rows)
        exact = sum(r["query"].startswith(("проблема", "сколько", "просто", "разогрев", "странный", "фрейм", "полина", "стинт", "шоу", "россии")) for r in rows)
        return query_hits * 10 + direct * 4 + exact * 5

    ranked = sorted(hits, key=score, reverse=True)
    selected = ranked[:180]
    print(f"UNIQUE CHANNELS {len(ranked)}; ENRICH {len(selected)}", flush=True)

    records = []
    for i, cid in enumerate(selected, 1):
        source_ids = list(dict.fromkeys(r["video_id"] for r in hits[cid]))[:8]
        rec = get_channel(cid, source_ids)
        rec["search_score"] = score(cid)
        rec["query_hits"] = len({r["query"] for r in hits[cid]})
        rec["queries"] = list(dict.fromkeys(r["query"] for r in hits[cid]))[:12]
        rec["source_titles"] = list(dict.fromkeys(r["title"] for r in hits[cid]))[:12]
        records.append(rec)
        print(f"CHANNEL {i}/{len(selected)} {rec.get('channel') or channel_names.get(cid,'')} subs={rec.get('subscribers')} recent14={rec.get('recent14')} med={rec.get('median_views')}", flush=True)

    # Keep broad enough for manual review; target rows first.
    candidates = [r for r in records if 4000 <= int(r.get("subscribers") or 0) <= 60000 and r.get("ru_score", 0) >= 0.2]
    candidates.sort(key=lambda r: (
        int(r.get("recent14") or 0) >= 4,
        int(r.get("median_views") or 0) >= 1500,
        r.get("query_hits", 0),
        r.get("search_score", 0),
    ), reverse=True)

    for idx, rec in enumerate(candidates[:80], 1):
        rec["sheet"] = make_sheet(rec, idx)

    (OUT / "records.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "candidates.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")

    fields = ["channel", "channel_url", "subscribers", "recent14", "shorts_checked", "median_views", "ru_score", "text_vpn", "contacts", "query_hits", "queries", "source_titles", "sheet"]
    with (OUT / "candidates.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in candidates:
            row = dict(r)
            for k in ("contacts", "queries", "source_titles"):
                row[k] = " | ".join(row.get(k) or [])
            w.writerow(row)

    print("TOP CANDIDATES", flush=True)
    for r in candidates[:30]:
        print(json.dumps({k:r.get(k) for k in ("channel","channel_url","subscribers","recent14","median_views","contacts","text_vpn","queries")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
