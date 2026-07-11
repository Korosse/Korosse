from __future__ import annotations
import json, subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'approx_date_output'
OUT.mkdir(parents=True, exist_ok=True)
CHANNELS = {
    'TWITCH_NAREZKI_T2X2': 'UCfPJse-3skARpxs5LaSUiWA',
    'STINT_ROFLS': 'UCf5QtXFu7aJfUTob5lyhzMA',
    'NAREZKA_PAPICHA': 'UC5KD_Q_rS3lVfP_hMDZ3HwQ',
    'FROSTOREZKA': 'UCgaJHUXTXGB5heKlKRvu8sg',
    'T2X2_KRUTOY': 'UCkpDxeWMe-XsVQozoqhFuZw',
    'RERA_SEAL': 'UCsUpkk_F9ClS2F0BkHTsnhA',
}

def collect(cid: str, approximate: bool) -> dict:
    cmd = [
        'yt-dlp', '--dump-single-json', '--flat-playlist', '--playlist-end', '15',
        '--skip-download', '--no-warnings', '--ignore-errors',
    ]
    if approximate:
        cmd += ['--extractor-args', 'youtubetab:approximate_date']
    cmd.append(f'https://www.youtube.com/channel/{cid}/shorts')
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        data = (json.loads(p.stdout) if p.stdout.strip() else {}) or {}
    except Exception as exc:
        return {'error': f'{type(exc).__name__}: {exc}', 'entries': []}
    entries = []
    for e in data.get('entries') or []:
        if not e:
            continue
        entries.append({
            'id': e.get('id'),
            'title': e.get('title'),
            'timestamp': e.get('timestamp'),
            'upload_date': e.get('upload_date'),
            'release_timestamp': e.get('release_timestamp'),
            'view_count': e.get('view_count'),
            'duration': e.get('duration'),
            'availability': e.get('availability'),
            'live_status': e.get('live_status'),
            'keys': sorted(e.keys()),
        })
    return {
        'returncode': p.returncode,
        'channel': data.get('channel') or data.get('uploader') or data.get('title'),
        'subscribers': data.get('channel_follower_count') or data.get('uploader_follower_count'),
        'entries': entries,
        'stderr': p.stderr[-1000:],
    }

result = {}
for name, cid in CHANNELS.items():
    result[name] = {
        'channel_id': cid,
        'without_approximate_date': collect(cid, False),
        'with_approximate_date': collect(cid, True),
    }
    a = result[name]['with_approximate_date']['entries']
    print(name, 'entries', len(a), 'dated', sum(bool(x.get('timestamp') or x.get('upload_date')) for x in a), flush=True)

(OUT / 'probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
