#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import re
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests
import youtube_channel_research_v2 as c

TARGETS = """
UC9Seuv1mUvolm-KASUppAnw UC8MpdU0rU2g8QYtOa9KgTPg UCDDbl3iEIpN8jhFRwr7vdaQ UC6m3Sqhu-8Bp2pG6ZyzMUwQ
UC_vlxqJH7OD0sTrJJPnJ9fQ UCOFAauJS0a1Xu2OvEMbjF2g UCPc6_TH0eOBYSHTiNZFfAug UC3z13cV53Pk3vrZjY7LHn-w
UCbX_Gc1mRP76B190cleARFg UC1bXbIOyWaZhxkxzS0PMfEg UCnQx9xmG_U82uPCj3-vxiVQ UCnUy7a5Z9D2XBu5VZEAelRw
UCq5cMlXa_G9ipcyidhJkBnw UCx8ZW-3_NAvgpRN18Ajm8Dg UC8WrBIrZBZ2gaEBNILijxPQ UCaclRtm8V-XEOxQHUashj7g
UCtVcvcrR8Ef6MeKPDF21RSw UC32ab_Mg9y6m6HZxS603jlg UCV0y4hM0s_MGgRnKdK7iCmA UCQc0XnhYi9wwSpkoKv70xEw
UCh6hcm8NJigfOMRbshnViCA UCWuixjKBXLfTqx_DELz58Jw UCPSvj4dXjnigdx4lZzPiBuA UCAziG6T1Cj3zuo5mxODXrZQ
UCvITV9WYMlsfWysV7HPGJoA UCT24rCYSvYpK5vy5msKz0ug UCh2t-rkdffQchAoGlLU1p0g UCR6AVYAAA3Dij6-HOVf9SxA
UCZ8LsN8Odr0NeLuAKq0lAqA UCyB69HC3nr-6XsUXHfsCpnw UC1oCL_-uYRSfFj_XC1DV3_g UCfPJse-3skARpxs5LaSUiWA
UCsUpkk_F9ClS2F0BkHTsnhA UCf5QtXFu7aJfUTob5lyhzMA UCWFet2M-JDh6XL-8RfPoFDg UCm1ntxZX0XAEydR70UABOUw
UC_yvQhmimAyunkFvvuTkYFA UCmFE8t3HzPArfPCkvWflHGQ
""".split()

c.OUT = Path("targeted_output_v4")
c.SHEETS = c.OUT / "sheets"
c.OUT.mkdir(exist_ok=True)
c.SHEETS.mkdir(exist_ok=True)


def flat_short_ids(channel_id: str) -> tuple[dict[str, Any] | None, list[str]]:
    flat = c.run_json(["--flat-playlist", "--playlist-end", "25", "--dump-single-json",
                       f"https://www.youtube.com/channel/{channel_id}/shorts"], 240)
    ids = []
    if flat:
        for entry in flat.get("entries") or []:
            if not isinstance(entry, dict): continue
            video_id = str(entry.get("id") or "")
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) and video_id not in ids: ids.append(video_id)
    return flat, ids


def json_after(raw: str, marker: str) -> dict[str, Any] | None:
    start = raw.find(marker)
    if start < 0: return None
    pos = start + len(marker)
    while pos < len(raw) and raw[pos] in " \t\r\n:=": pos += 1
    try:
        value, _ = json.JSONDecoder().raw_decode(raw[pos:])
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def watch_metadata(video_id: str, expected_channel: str) -> dict[str, Any] | None:
    try:
        response = requests.get(f"https://www.youtube.com/watch?v={video_id}&hl=ru&gl=RU", headers=c.HEADERS, timeout=30)
        if not response.ok: return None
        raw = response.text
    except Exception:
        return None
    data = None
    for marker in ("var ytInitialPlayerResponse = ", "ytInitialPlayerResponse = "):
        data = json_after(raw, marker)
        if data: break
    if not data:
        match = re.search(r'"videoDetails":\{"videoId":"' + re.escape(video_id) + r'"', raw)
        if not match: return None
        channel_match = re.search(r'"channelId":"(UC[A-Za-z0-9_-]+)"', raw[match.start():match.start()+10000])
        length_match = re.search(r'"lengthSeconds":"(\d+)"', raw[match.start():match.start()+10000])
        views_match = re.search(r'"viewCount":"(\d+)"', raw[match.start():match.start()+15000])
        title_match = re.search(r'"title":"((?:\\.|[^"])*)"', raw[match.start():match.start()+6000])
        date_match = re.search(r'"publishDate":"([0-9-]+)"', raw)
        if not channel_match or channel_match.group(1) != expected_channel: return None
        title = ""
        if title_match:
            try: title = json.loads('"' + title_match.group(1) + '"')
            except Exception: title = html.unescape(title_match.group(1))
        publish = date_match.group(1) if date_match else ""
        dt = None
        if publish:
            try: dt = datetime.strptime(publish[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception: pass
        return {"id": video_id, "title": title, "description": "", "view_count": int(views_match.group(1)) if views_match else 0,
                "duration": int(length_match.group(1)) if length_match else 0,
                "publish_date": dt.isoformat() if dt else "", "timestamp": int(dt.timestamp()) if dt else None}
    details = data.get("videoDetails") or {}
    if details.get("videoId") != video_id or details.get("channelId") != expected_channel: return None
    micro = ((data.get("microformat") or {}).get("playerMicroformatRenderer") or {})
    publish = str(micro.get("publishDate") or micro.get("uploadDate") or "")
    dt = None
    if publish:
        try: dt = datetime.strptime(publish[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception: pass
    return {"id": video_id, "title": str(details.get("title") or ""), "description": str(details.get("shortDescription") or ""),
            "view_count": int(details.get("viewCount") or 0), "duration": int(details.get("lengthSeconds") or 0),
            "publish_date": dt.isoformat() if dt else "", "timestamp": int(dt.timestamp()) if dt else None}


def inspect(channel_id: str) -> dict[str, Any]:
    page = c.fetch_channel(channel_id)
    flat, ids = flat_short_ids(channel_id)
    if not flat: return {"channel_id": channel_id, "status": "NO_FLAT_SHORTS", "contacts": "; ".join(page["contacts"])}
    title = str(flat.get("channel") or flat.get("uploader") or flat.get("title") or page["title"] or channel_id)
    subscribers = c.parse_count(flat.get("channel_follower_count") or flat.get("uploader_follower_count")) or page["subscribers"] or 0
    row = {"channel_id": channel_id, "title": title, "url": f"https://www.youtube.com/channel/{channel_id}/shorts",
           "subscribers": subscribers, "contacts": "; ".join(page["contacts"]), "short_ids_found": len(ids)}
    if not page["contacts"]: row["status"] = "NO_PERSONAL_CONTACT_CANDIDATE"; return row
    if not subscribers or not 5000 <= subscribers <= 50000: row["status"] = "SUBSCRIBERS_FAIL"; return row
    if len(ids) < 8: row["status"] = "TOO_FEW_REAL_SHORT_IDS"; return row
    videos = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(watch_metadata, video_id, channel_id) for video_id in ids[:20]]
        for future in as_completed(futures):
            video = future.result()
            if video: videos.append(video)
    videos.sort(key=lambda video: video.get("timestamp") or 0, reverse=True)
    videos = videos[:15]
    row["metadata_count"] = len(videos)
    if len(videos) < 10: row["status"] = "TOO_FEW_WATCH_METADATA"; return row
    dates = [c.dt_from(video) for video in videos]; views = [video["view_count"] for video in videos]
    row.update({"videos_checked": len(videos),
                "videos_7d": sum(1 for date in dates if date and date >= c.NOW - timedelta(days=7)),
                "videos_14d": sum(1 for date in dates if date and date >= c.NOW - timedelta(days=14)),
                "median_views": int(statistics.median(views)), "above_1500": sum(1 for value in views if value >= 1500),
                "under_60": sum(1 for video in videos if 0 < video["duration"] <= 60),
                "vpn_text_hits": ";".join(video["id"] for video in videos if c.VPN_RE.search(video["title"] + " " + video["description"]))})
    row["activity_pass"] = int(row["videos_7d"] >= 3 or row["videos_14d"] >= 6)
    row["views_pass"] = int(row["median_views"] >= 2000 and row["above_1500"] >= 8)
    row["duration_pass"] = int(row["under_60"] >= 10)
    if row["activity_pass"] and row["views_pass"] and row["duration_pass"] and not row["vpn_text_hits"]:
        row["status"] = "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED"; row["sheet"] = c.make_sheet(row, videos)
        with (c.OUT / "candidate_videos.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps({"channel": row, "videos": videos}, ensure_ascii=False) + "\n")
    else: row["status"] = "METRICS_DURATION_OR_VPN_FAIL"
    return row

rows = []
with ThreadPoolExecutor(max_workers=5) as pool:
    futures = {pool.submit(inspect, channel_id): channel_id for channel_id in TARGETS}
    for index, future in enumerate(as_completed(futures), 1):
        channel_id = futures[future]
        try: row = future.result()
        except Exception as error: row = {"channel_id": channel_id, "status": "ERROR", "error": repr(error)}
        rows.append(row); print(index, len(TARGETS), row.get("status"), row.get("title", channel_id), flush=True)
rows.sort(key=lambda row: (row.get("status") != "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED", -(row.get("median_views") or 0)))
fields = []
for row in rows:
    for key in row:
        if key not in fields: fields.append(key)
for filename, selected in [("all_checked.csv", rows), ("qualified.csv", [r for r in rows if r.get("status") == "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED"])]:
    with (c.OUT / filename).open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader(); writer.writerows(selected)
counts = {}
for row in rows: counts[row.get("status", "UNKNOWN")] = counts.get(row.get("status", "UNKNOWN"), 0) + 1
summary = {"targets": len(TARGETS), "qualified": sum(r.get("status") == "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED" for r in rows), "status_counts": counts}
(c.OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
