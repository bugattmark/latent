import asyncio, json
import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize

from .db import init_db, engine
from .sources import reddit, wires, uk_th, arxiv, hn
from .heuristics import badges_for, section_for, parse_domain, importance_base
from .config import settings
from .llm import summarize_items

ICT=timezone(timedelta(hours=7))

def now_iso(): return datetime.now(timezone.utc).astimezone(ICT).isoformat(timespec="seconds")

vec = HashingVectorizer(n_features=256, alternate_sign=False, norm='l2')

async def collect_all():
    results=[]
    try:
        for n in await wires.collect():
            results.append({"title":n["title"],"urls":[n["link"]],"evidence":[n["link"]],"published_at":n.get("pubDate")})
    except Exception: pass
    try:
        for n in await uk_th.collect():
            results.append({"title":f"{n['source']}: {n['title']}", "urls":[n["link"]],"evidence":[n["link"]],"published_at":n.get("pubDate")})
    except Exception: pass
    try:
        for r in await reddit.collect():
            ext=r.get("url") or r.get("permalink")
            results.append({"title":r["title"],"urls":[ext, r["permalink"]] if ext else [r["permalink"]],
                            "evidence":[r["permalink"]],
                            "published_at": datetime.fromtimestamp(r["created_utc"], timezone.utc).astimezone(ICT).isoformat(timespec="seconds"),
                            "comments": r.get("comments", [])})
    except Exception: pass
    try:
        for a in await arxiv.collect():
            results.append({"title":f"{a['source']}: {a['title']}", "urls":[a["link"]],"evidence":[a["link"]],"published_at":a.get("pubDate")})
    except Exception: pass
    try:
        for i in range(len(results)):
            urls = results[i].get("urls") or []
            if not urls: continue
            hit = await hn.fetch_hn_for_url(urls[0])
            if hit:
                comments = await hn.fetch_top_comments(hit["objectID"], limit=2)
                if comments:
                    prev = results[i].get("comments") or []
                    results[i]["comments"] = prev + [{"source":"HN", **c} for c in comments]
    except Exception: pass
    return results

def section_priority(sec:str)->int:
    order=["ai_research","product_releases","companies","repos","policy","security","global_headlines","macro","markets","funding","calendar","watchlist_btc"]
    return order.index(sec) if sec in order else 999

async def run_cycle():
    init_db(); ts=now_iso()
    items_raw=await collect_all()
    titles=[it["title"] for it in items_raw]
    X = vec.transform(titles) if titles else None

    with engine.begin() as conn:
        prev_titles = [r[0] for r in conn.execute(text("SELECT title FROM items WHERE datetime(collected_at) >= datetime('now','-7 days')")).fetchall()]
        Xp = vec.transform(prev_titles) if prev_titles else None
        centroid = None
        if Xp is not None and Xp.shape[0] > 0:
            c = np.asarray(Xp.sum(axis=0)).ravel()           # no np.matrix
            n = np.linalg.norm(c)
            centroid = c / n if n > 0 else c                 # unit vector or zeros

        title_counts={}
        for it in items_raw:
            t=it["title"].lower().strip()
            title_counts[t]=title_counts.get(t,0)+1

        enriched=[]
        for idx,it in enumerate(items_raw):
            urls=[u for u in (it.get("urls") or []) if u]
            if not urls: continue
            sec=section_for(it["title"], urls)
            host=parse_domain(urls[0])
            nov = 0.5
            if X is not None and centroid is not None:
                v = X[idx]
                if centroid is not None:
                    vr = v.toarray().ravel()
                    denom = (np.linalg.norm(vr) * (np.linalg.norm(centroid) + 1e-12))
                    sim = float(vr.dot(centroid) / denom) if denom > 0 else 0.0
                else:
                    sim = 0.0
                nov = max(0.0, 1.0 - sim)
            cross = title_counts[it["title"].lower().strip()]
            reddit_hit = any("reddit.com" in u for u in urls)
            hn_hit = any("news.ycombinator.com" in u for u in urls)
            rec = 0.7
            score = importance_base(it["title"], urls, cross, reddit_hit, hn_hit, recency_factor=rec, novelty=nov)

            badges=badges_for(urls)
            item_id=f"{sec}_{abs(hash(urls[0]))%100000000}_{idx}"
            comments = it.get("comments")
            conn.execute(text("""
            INSERT OR REPLACE INTO items
            (id, section, title, summary, urls, evidence, why, actionables, published_at, collected_at, badges, domain, base_score, embed, ai_take, ai_cost, comments)
            VALUES (:id,:section,:title,:summary,:urls,:evidence,:why,:actionables,:published_at,:collected_at,:badges,:domain,:base_score,:embed,:ai_take,:ai_cost,:comments)
            """), {
                "id": item_id,
                "section": sec,
                "title": it["title"],
                "summary": it["title"],
                "urls": json.dumps(urls),
                "evidence": json.dumps(it.get("evidence") or urls),
                "why": None,
                "actionables": json.dumps([]),
                "published_at": it.get("published_at") or ts,
                "collected_at": ts,
                "badges": json.dumps(badges),
                "domain": host,
                "base_score": score,
                "embed": None,
                "ai_take": None,
                "ai_cost": 0.0,
                "comments": json.dumps(comments) if comments else None
            })
            enriched.append({"id":item_id,"title":it["title"],"urls":urls,"score":score,"section":sec})

        enriched.sort(key=lambda x: (-x["score"], section_priority(x["section"])))
        top_picks=[e["id"] for e in enriched[:48]]

        rows=conn.execute(text("""
            SELECT id, section, base_score FROM items
            WHERE datetime(collected_at) >= datetime('now','-36 hours')
        """)).mappings().all()
        sections={}
        for r in rows:
            sections.setdefault(r["section"], []).append((r["id"], r["base_score"]))
        for k in sections:
            sections[k]=[i for i,_ in sorted(sections[k], key=lambda t: t[1], reverse=True)]

        meta={"items_considered": len(items_raw), "items_included": sum(len(v) for v in sections.values()), "model_cost_usd": 0.0}
        date_ict=datetime.now(timezone.utc).astimezone(ICT).date().isoformat()
        conn.execute(text("""
            INSERT OR REPLACE INTO briefs (date_ict, generated_at, sections, meta, top_picks)
            VALUES (:date_ict,:generated_at,:sections,:meta,:top_picks)
        """), {"date_ict":date_ict,"generated_at":ts,"sections":json.dumps(sections),"meta":json.dumps(meta),"top_picks":json.dumps(top_picks)})

        if top_picks and settings.OPENAI_API_KEY and settings.DAILY_BUDGET_USD>0:
            placeholders=",".join([f":i{n}" for n,_ in enumerate(top_picks)])
            params={f"i{n}":tid for n,tid in enumerate(top_picks)}
            sel=conn.execute(text(f"SELECT id, title, urls FROM items WHERE id IN ({placeholders})"), params).mappings().all()
            items_for_llm=[{"id":r["id"], "title":r["title"], "urls":json.loads(r["urls"])} for r in sel]
            summaries=summarize_items(items_for_llm, budget_usd=settings.DAILY_BUDGET_USD)
            total_cost=sum(s.get("cost",0.0) for s in summaries)
            meta["model_cost_usd"]=round(total_cost, 4)
            for s in summaries:
                if not s.get("id"): continue
                bullets_text="\n".join(s.get("bullets") or [])
                conn.execute(text("""UPDATE items SET ai_take=:ai_take, ai_cost=:ai_cost, summary=CASE WHEN :bul != '' THEN :bul ELSE summary END WHERE id=:id"""),
                             {"ai_take": s.get("ai_take",""), "ai_cost": s.get("cost",0.0), "bul": bullets_text, "id": s["id"]})
            conn.execute(text("""UPDATE briefs SET meta=:meta WHERE date_ict=:d"""), {"meta": json.dumps(meta), "d": date_ict})


import argparse, asyncio, time, random, sys

async def scheduler_loop():
    # Run immediately on boot, then approximately hourly with jitter.
    while True:
        start = time.time()
        try:
            await run_cycle()
        except Exception as e:
            print("worker: run_cycle failed:", e, file=sys.stderr)
        # sleep ~1h minus time spent, min 5 min, plus small jitter
        spent = time.time() - start
        sleep_for = max(300, 3600 - spent) + random.uniform(-30, 30)
        await asyncio.sleep(sleep_for)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="run a single cycle and exit")
    args = parser.parse_args()
    if args.once:
        asyncio.run(run_cycle())
    else:
        asyncio.run(scheduler_loop())
