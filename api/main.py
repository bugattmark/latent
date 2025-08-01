from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .db import init_db, engine
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
import json, re
from urllib.parse import urlparse, parse_qs
import httpx

app=FastAPI(title="Researcher Brief API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init_db()

@app.get("/health")
def health(): return {"ok": True}

@app.get("/brief/today")
def brief_today(limit:int=48, personalized:bool=True, view:str="bullets"):
    ICT=timezone(timedelta(hours=7)); date_ict=datetime.now(timezone.utc).astimezone(ICT).date().isoformat()
    with engine.begin() as conn:
        row=conn.execute(text("SELECT date_ict, generated_at, sections, meta, top_picks FROM briefs WHERE date_ict=:d"),{"d":date_ict}).mappings().first()
        if not row: raise HTTPException(404,"No brief for today yet. The worker runs hourly; you can force a run with '--once'.")
        sections=json.loads(row["sections"]); meta=json.loads(row["meta"]); top=json.loads(row["top_picks"] or "[]")
        return {"date_ict":row["date_ict"],"generated_at":row["generated_at"],"sections":sections, "meta":meta, "top_picks": top[:limit]}

@app.get("/items/{item_id}")
def get_item(item_id: str):
    with engine.begin() as conn:
        row=conn.execute(text("SELECT * FROM items WHERE id=:i"),{"i":item_id}).mappings().first()
        if not row: raise HTTPException(404,"not found")
        row=dict(row)
        import json as _j
        row["urls"]=_j.loads(row["urls"]) if row.get("urls") else []
        row["evidence"]=_j.loads(row["evidence"]) if row.get("evidence") else []
        row["actionables"]=_j.loads(row["actionables"]) if row.get("actionables") else []
        row["badges"]=[b for b in _j.loads(row["badges"]) if b]
        row["comments"]=_j.loads(row["comments"]) if row.get("comments") else []
        return row

# --- Image preview extraction (og:image) ---
def _extract_og_image(html: str) -> str | None:
    m = re.search(r'<meta[^>]*(?:property|name)=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
    if m: return m.group(1)
    m = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']og:image["\']', html, re.I)
    if m: return m.group(1)
    return None

def _youtube_thumb(u: str) -> str | None:
    try:
        p = urlparse(u)
        if "youtube.com" in p.netloc.lower():
            from urllib.parse import parse_qs
            vid = parse_qs(p.query).get("v", [None])[0]
            if vid: return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
        if "youtu.be" in p.netloc.lower():
            vid = p.path.strip("/").split("/")[0] or None
            if vid: return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
    except Exception:
        pass
    return None

async def _preview_single(u: str) -> str | None:
    u = (u or "").strip()
    if not u: return None
    host = urlparse(u).netloc.lower()
    if any(u.lower().endswith(ext) for ext in (".jpg",".jpeg",".png",".gif",".webp",".avif",".bmp",".svg")):
        return u
    if any(h in host for h in ("i.redd.it", "i.imgur.com", "pbs.twimg.com", "images.unsplash.com")):
        return u
    yt = _youtube_thumb(u)
    if yt: return yt
    headers = {"User-Agent": "research-brief/1.0"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(u, headers=headers, follow_redirects=True)
        ct = r.headers.get("content-type","").lower()
        if ct.startswith("image/"): return u
        if "text/html" in ct or "application/xhtml" in ct:
            img = _extract_og_image(r.text)
            return img
    return None

@app.get("/preview")
async def preview(url: str):
    try:
        img = await _preview_single(url)
        return {"image": img}
    except Exception:
        return {"image": None}

@app.get("/preview/best")
async def preview_best(url: list[str] = Query([])):
    for u in url:
        try:
            img = await _preview_single(u)
            if img: return {"image": img}
        except Exception: continue
    return {"image": None}
