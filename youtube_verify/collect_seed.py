from __future__ import annotations
import csv, json, re, statistics, subprocess, time, html
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
import requests
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"; GRIDS=OUT/"grids"; THUMBS=OUT/"thumbs"; RAW=OUT/"raw"
for p in (OUT,GRIDS,THUMBS,RAW): p.mkdir(parents=True,exist_ok=True)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
VPN=("vpn","впн","proxy","прокси","vless","xray","outline","amnezia","warp","nordvpn","expressvpn","proton vpn","surfshark")
session=requests.Session(); session.headers.update({"User-Agent":UA,"Accept-Language":"ru,en;q=0.8"})

def run_json(url, flat=False, end=None):
    cmd=["yt-dlp","--dump-single-json","--skip-download","--no-warnings","--ignore-errors","--extractor-args","youtube:player_client=android_vr,web_safari"]
    if flat: cmd += ["--flat-playlist"]
    if end: cmd += ["--playlist-end",str(end)]
    cmd.append(url)
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
        if r.returncode and not r.stdout.strip(): return {"_error":r.stderr[-1000:]}
        return json.loads(r.stdout)
    except Exception as e:
        return {"_error":type(e).__name__+":"+str(e)}

def video_full(entry):
    vid=str(entry.get("id") or "")
    if not vid: return entry
    info=run_json("https://www.youtube.com/watch?v="+vid)
    if not info: return entry
    keys=("id","title","view_count","timestamp","upload_date","duration","description","thumbnail","thumbnails","webpage_url")
    out=dict(entry)
    for k in keys:
        if info.get(k) is not None: out[k]=info.get(k)
    return out

def age_days(v):
    ts=v.get("timestamp")
    if ts:
        return max(0,(datetime.now(timezone.utc)-datetime.fromtimestamp(float(ts),timezone.utc)).total_seconds()/86400)
    d=str(v.get("upload_date") or "")
    if len(d)>=8:
        try:
            dt=datetime.strptime(d[:8],"%Y%m%d").replace(tzinfo=timezone.utc)
            return max(0,(datetime.now(timezone.utc)-dt).total_seconds()/86400)
        except Exception: pass
    return None

def contact_links(text):
    text=html.unescape(unquote(text or "")).replace("\\u0026","&")
    pats=re.findall(r"https?://(?:t\.me|telegram\.me|vk\.com)/[A-Za-z0-9_.-]+|(?:t\.me|telegram\.me|vk\.com)/[A-Za-z0-9_.-]+|@[A-Za-z0-9_]{4,}",text,re.I)
    out=[]
    for x in pats:
        if x.startswith("@"): x="https://t.me/"+x[1:]
        elif not x.startswith("http"): x="https://"+x
        x=x.rstrip(".,);]}>")
        low=x.lower()
        if any(z in low for z in ("/club","/public","/event","/wall","/topic","t.me/+","joinchat","/bot")): continue
        if low not in [y.lower() for y in out]: out.append(x)
    return out

def fetch_about(url):
    base=url.split("/shorts")[0].rstrip("/")
    chunks=[]
    for u in (base,base+"/about"):
        try: chunks.append(session.get(u,timeout=25).text)
        except Exception: pass
    return " ".join(chunks)

def choose_thumb(v):
    arr=v.get("thumbnails") or []
    if arr:
        arr=[x for x in arr if x.get("url")]
        if arr: return sorted(arr,key=lambda x:(x.get("width") or 0)*(x.get("height") or 0))[-1]["url"]
    return v.get("thumbnail") or (f"https://i.ytimg.com/vi/{v.get('id')}/hqdefault.jpg" if v.get("id") else "")

def download_thumb(v):
    vid=str(v.get("id") or "")
    path=THUMBS/f"{vid}.jpg"
    if path.exists() and path.stat().st_size>1000: return path
    for url in (choose_thumb(v),f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg",f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"):
        if not url: continue
        try:
            b=session.get(url,timeout=25).content
            if len(b)>1000:
                path.write_bytes(b); Image.open(path).verify(); return path
        except Exception:
            try: path.unlink()
            except Exception: pass
    return None

def grid(title,cid,videos):
    ims=[]
    for v in videos[:15]:
        p=download_thumb(v)
        if not p: continue
        try: ims.append((v,Image.open(p).convert("RGB")))
        except Exception: pass
    if not ims: return ""
    cw,ch=300,260; canvas=Image.new("RGB",(cw*5,60+ch*3),"white"); d=ImageDraw.Draw(canvas)
    d.text((10,10),f"{title} | {cid}",fill="black")
    for i,(v,im) in enumerate(ims):
        x=(i%5)*cw; y=60+(i//5)*ch
        im.thumbnail((cw-8,ch-55)); canvas.paste(im,(x+(cw-im.width)//2,y))
        age=age_days(v); vv=int(v.get("view_count") or 0)
        d.text((x+5,y+ch-48),f"{i+1:02d} | {vv:,} | {age:.1f}d" if age is not None else f"{i+1:02d} | {vv:,}",fill="black")
        d.text((x+5,y+ch-28),str(v.get("title") or "")[:42],fill="black")
    safe=re.sub(r"[^A-Za-z0-9А-Яа-я_-]+","_",title)[:55]
    p=GRIDS/f"{safe}_{cid}.jpg"; canvas.save(p,quality=90); return str(p.relative_to(ROOT))

def process(url):
    match=re.search(r"UC[\w-]{20,}",url); cid=match.group(0) if match else url
    info=run_json(url,flat=True,end=15)
    entries=[x for x in (info.get("entries") or []) if x and x.get("id")][:15]
    if entries:
        with ThreadPoolExecutor(max_workers=5) as ex: entries=list(ex.map(video_full,entries))
    title=info.get("channel") or info.get("uploader") or info.get("title") or cid
    subs=info.get("channel_follower_count") or info.get("uploader_follower_count") or 0
    desc=(info.get("description") or "")+" "+fetch_about(url)
    contacts=contact_links(desc)
    ages=[age_days(v) for v in entries]; views=[int(v.get("view_count") or 0) for v in entries]
    known=[x for x in ages if x is not None]
    row={"channel_id":cid,"title":title,"url":url,"subscribers":int(subs or 0),"videos_count":len(entries),"videos_7d":sum(x is not None and x<=7 for x in ages),"videos_14d":sum(x is not None and x<=14 for x in ages),"days_since_last":round(min(known),2) if known else None,"median_views":int(statistics.median(views)) if views else 0,"above_1500":sum(x>=1500 for x in views),"contacts":" | ".join(contacts),"vpn_text":" | ".join(sorted({t for t in VPN if t in desc.lower()})),"grid":"","error":info.get("_error",""),"videos":entries}
    row["grid"]=grid(title,cid,entries)
    (RAW/f"{cid}.json").write_text(json.dumps({"info":info,"row":row},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:row[k] for k in row if k!="videos"},ensure_ascii=False),flush=True)
    return row

def main():
    seeds=[x.strip() for x in (ROOT/"seeds.txt").read_text().splitlines() if x.strip()]
    rows=[]
    for i,u in enumerate(seeds,1):
        print(f"CHANNEL {i}/{len(seeds)} {u}",flush=True)
        try: rows.append(process(u))
        except Exception as e: rows.append({"channel_id":u,"title":u,"url":u,"error":type(e).__name__+":"+str(e)})
        time.sleep(.2)
    fields=["channel_id","title","url","subscribers","videos_count","videos_7d","videos_14d","days_since_last","median_views","above_1500","contacts","vpn_text","grid","error"]
    with (OUT/"summary.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fields); w.writeheader(); w.writerows([{k:r.get(k,"") for k in fields} for r in rows])
    (OUT/"all.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    ok=[r for r in rows if 5000<=int(r.get("subscribers") or 0)<=50000 and r.get("videos_count",0)>=10 and (r.get("videos_7d",0)>=3 or r.get("videos_14d",0)>=6) and r.get("median_views",0)>=2000 and r.get("above_1500",0)>=8 and r.get("contacts") and not r.get("vpn_text")]
    (OUT/"metric_contact_pass.json").write_text(json.dumps(ok,ensure_ascii=False,indent=2),encoding="utf-8")
    print("DONE",len(rows),"metric_contact_pass",len(ok),flush=True)
if __name__=="__main__": main()
