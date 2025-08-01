from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from researcherbrief.core.config import get_settings
from researcherbrief.core.db import init_db, get_brief, record_event, get_item, set_item_summary, hot_topics, conn
from researcherbrief.core.llm import summarize_to_struct
import json, datetime as dt

def create_app():
    s=get_settings(); app=FastAPI(title="Researcher Brief API")
    origins=[o.strip() for o in s.cors_origins.split(',') if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health(): return {"status":"ok"}

    @app.get("/brief/today")
    def brief_today():
        b=get_brief(dt.date.today().isoformat())
        if not b: return {"date": dt.date.today().isoformat(), "top_picks": []}
        return b

    @app.post("/events")
    def events(payload: dict):
        record_event(payload.get("type",""), int(payload.get("item_id") or 0), payload.get("meta") or {})
        return {"ok": True}

    @app.get("/items/{item_id}")
    def get_item_by_id(item_id:int):
        it=get_item(item_id); 
        if not it: raise HTTPException(404,"item not found")
        return it

    @app.post("/items/{item_id}/summarize")
    def summarize_item(item_id:int):
        it=get_item(item_id)
        if not it: raise HTTPException(404, "item not found")
        meta=it.get("meta") or {}; abstract=meta.get("abstract","");
        s=summarize_to_struct(it.get("title",""), abstract)
        set_item_summary(item_id, s); return get_item(item_id)

    @app.get("/migrations/today")
    def migrations_today():
        with conn() as c:
            rows=c.execute("SELECT * FROM migrations WHERE ts>=date('now')").fetchall()
            return [dict(r) for r in rows]

    @app.get("/hot") 
    def hot_simple(): return {"topics": hot_topics(days=3, k=10)}

    @app.get("/trends/hot")
    def trends_hot(days:int=Query(3,ge=1,le=7), limit:int=Query(8,ge=3,le=20)):
        with conn() as c:
            rows=c.execute("SELECT * FROM topics WHERE created_at>=datetime('now', ? ) ORDER BY hotness DESC LIMIT ?",(f'-{days} days', limit)).fetchall()
            out=[]
            for r in rows:
                d=dict(r); d["features"]=json.loads(d.get("features") or "{}")
                mem=json.loads(d.get("members") or "[]")[:3]; examples=[]
                if mem:
                    qmarks=",".join("?"*len(mem))
                    its=c.execute(f"SELECT id,title,url,source,section FROM items WHERE id IN ({qmarks})", (*mem,)).fetchall()
                    examples=[dict(x) for x in its]
                d["examples"]=examples; out.append(d)
            return {"topics": out}

    @app.get("/study/next")
    def study_next(limit:int=Query(6,ge=1,le=12)):
        with conn() as c:
            rows=c.execute("SELECT * FROM topics WHERE created_at>=datetime('now','-21 days') ORDER BY study_score DESC LIMIT ?", (limit,)).fetchall()
            out=[]
            for r in rows:
                d=dict(r); d["features"]=json.loads(d.get("features") or "{}")
                mem=json.loads(d.get("members") or "[]"); examples=[]
                if mem:
                    qmarks=",".join("?"*len(mem))
                    its=[dict(x) for x in c.execute(f"SELECT id,title,url,source,section FROM items WHERE id IN ({qmarks})", (*mem,)).fetchall()]
                    def score_src(s): 
                        order={"Official":4,"Releases":3,"Threads":2,"AI Research":1,"News":0}
                        return order.get(s,0)
                    its=sorted(its, key=lambda x:(-score_src(x.get("source") or x.get("section")), -len(x.get("title") or "")))
                    examples=its[:3]
                d["examples"]=examples; out.append(d)
            return {"topics": out}

    @app.get("/feed/{section}")
    def feed(section:str):
        section_map={"news":["News","AI News","Global","Tech News"],"releases":["Releases"],"threads":["Threads"],"research":["AI Research"],"global":["Global","News"]}
        allowed=section_map.get(section.lower())
        if not allowed: raise HTTPException(404, "section not found")
        with conn() as c:
            qmarks=",".join("?"*len(allowed))
            rows=c.execute(f"SELECT * FROM items WHERE section IN ({qmarks}) ORDER BY score DESC, id DESC LIMIT 60", (*allowed,)).fetchall()
            out=[]; 
            for r in rows:
                d=dict(r)
                try: d["meta"]=json.loads(d["meta"])
                except: d["meta"]={}
                out.append(d)
            return {"items": out}

    return app

app=create_app()

def run():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
