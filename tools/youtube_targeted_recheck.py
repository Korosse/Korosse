#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import youtube_channel_research_v2 as collector

TARGETS = """
UC9Seuv1mUvolm-KASUppAnw
UC8MpdU0rU2g8QYtOa9KgTPg
UCDDbl3iEIpN8jhFRwr7vdaQ
UC6m3Sqhu-8Bp2pG6ZyzMUwQ
UC_vlxqJH7OD0sTrJJPnJ9fQ
UCOFAauJS0a1Xu2OvEMbjF2g
UCPc6_TH0eOBYSHTiNZFfAug
UC3z13cV53Pk3vrZjY7LHn-w
UCbX_Gc1mRP76B190cleARFg
UC1bXbIOyWaZhxkxzS0PMfEg
UCnQx9xmG_U82uPCj3-vxiVQ
UCnUy7a5Z9D2XBu5VZEAelRw
UCq5cMlXa_G9ipcyidhJkBnw
UCx8ZW-3_NAvgpRN18Ajm8Dg
UC8WrBIrZBZ2gaEBNILijxPQ
UCaclRtm8V-XEOxQHUashj7g
UCtVcvcrR8Ef6MeKPDF21RSw
UC32ab_Mg9y6m6HZxS603jlg
UCV0y4hM0s_MGgRnKdK7iCmA
UCQc0XnhYi9wwSpkoKv70xEw
UCh6hcm8NJigfOMRbshnViCA
UCWuixjKBXLfTqx_DELz58Jw
UCPSvj4dXjnigdx4lZzPiBuA
UCAziG6T1Cj3zuo5mxODXrZQ
UCvITV9WYMlsfWysV7HPGJoA
UCT24rCYSvYpK5vy5msKz0ug
UCh2t-rkdffQchAoGlLU1p0g
UCR6AVYAAA3Dij6-HOVf9SxA
UCZ8LsN8Odr0NeLuAKq0lAqA
UCyB69HC3nr-6XsUXHfsCpnw
UC1oCL_-uYRSfFj_XC1DV3_g
UCfPJse-3skARpxs5LaSUiWA
UCsUpkk_F9ClS2F0BkHTsnhA
UCf5QtXFu7aJfUTob5lyhzMA
UCWFet2M-JDh6XL-8RfPoFDg
UCm1ntxZX0XAEydR70UABOUw
UC_yvQhmimAyunkFvvuTkYFA
UCmFE8t3HzPArfPCkvWflHGQ
""".split()

collector.OUT = Path("targeted_output")
collector.SHEETS = collector.OUT / "sheets"
collector.OUT.mkdir(exist_ok=True)
collector.SHEETS.mkdir(exist_ok=True)

rows = []
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(collector.inspect_channel, channel_id): channel_id for channel_id in TARGETS}
    for index, future in enumerate(as_completed(futures), 1):
        channel_id = futures[future]
        try:
            row = future.result()
        except Exception as error:
            row = {"channel_id": channel_id, "status": "ERROR", "error": repr(error)}
        rows.append(row)
        print(index, len(TARGETS), row.get("status"), row.get("title", channel_id), flush=True)

rows.sort(key=lambda row: (row.get("status") != "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED", -(row.get("median_views") or 0)))
fields = []
for row in rows:
    for key in row:
        if key not in fields: fields.append(key)
with (collector.OUT / "all_checked.csv").open("w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
qualified = [row for row in rows if row.get("status") == "NUMERIC_CONTACT_PASS_VISUAL_REQUIRED"]
with (collector.OUT / "qualified.csv").open("w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader(); writer.writerows(qualified)
counts = {}
for row in rows: counts[row.get("status", "UNKNOWN")] = counts.get(row.get("status", "UNKNOWN"), 0) + 1
summary = {"targets": len(TARGETS), "qualified": len(qualified), "status_counts": counts}
(collector.OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
