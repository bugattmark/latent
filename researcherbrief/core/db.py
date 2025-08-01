import sqlite3, json, pathlib, datetime as dt
from typing import Any, Dict, List
from .config import get_settings

def _path():
    p = pathlib.Path(get_settings().db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)

def conn():
    c = sqlite3.connect(_path())
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, url TEXT UNIQUE, title TEXT,
            section TEXT, score REAL DEFAULT 0,
            meta TEXT DEFAULT '{}',
            summary TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )""" )
        c.execute("""CREATE TABLE IF NOT EXISTS briefs(
            date TEXT PRIMARY KEY, top_ids TEXT
        )""" )
        c.execute("""CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT (datetime('now')),
            type TEXT, item_id INTEGER, meta TEXT
        )""" )
        c.execute("""CREATE TABLE IF NOT EXISTS migrations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, x TEXT, y TEXT, sentence TEXT, link TEXT, source TEXT, confidence REAL
        )""" )
        c.execute("""CREATE TABLE IF NOT EXISTS topics(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT, window_start TEXT, window_end TEXT,
            hotness REAL, study_score REAL, members TEXT, features TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )""" )
        c.execute("CREATE INDEX IF NOT EXISTS ix_topics_created ON topics(created_at)")
        c.commit()

def upsert_items(rows: List[Dict[str, Any]]):
    if not rows: return
    with conn() as c:
        for r in rows:
            meta = json.dumps(r.get("meta") or {})
            c.execute("""INSERT INTO items(source,url,title,section,score,meta,created_at)
                         VALUES(?,?,?,?,?,?,?)
                         ON CONFLICT(url) DO UPDATE SET
                           title=excluded.title, section=excluded.section,
                           score=excluded.score, meta=excluded.meta""" ,
                      (r["source"], r["url"], r["title"], r["section"], float(r.get("score",0)), meta, r.get("created_at")))
        c.commit()

def top_ids(n:int=48) -> list[int]:
    with conn() as c:
        rows = c.execute("SELECT id FROM items ORDER BY score DESC, id DESC LIMIT ?", (n,)).fetchall()
        return [r["id"] for r in rows]

def save_brief(date: str, ids: List[int]):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO briefs(date, top_ids) VALUES(?, ?)", (date, json.dumps(ids)))
        c.commit()

def get_brief(date: str | None = None):
    if not date:
        date = dt.date.today().isoformat()
    with conn() as c:
        row = c.execute("SELECT top_ids FROM briefs WHERE date=?", (date,)).fetchone()
        if not row: return None
        ids = json.loads(row["top_ids"])
        if not ids: return {"date": date, "top_picks": []}
        placeholders = ",".join("?"*len(ids))
        items = c.execute(f"SELECT * FROM items WHERE id IN ({placeholders})", (*ids,)).fetchall()
        def row2(r):
            d = dict(r)
            try: d["meta"]=json.loads(d["meta"])
            except: d["meta"]={}
            return d
        id_index = {v:i for i,v in enumerate(ids)}
        ordered = sorted(items, key=lambda r: id_index.get(r["id"], 99999))
        return {"date": date, "top_picks": [row2(r) for r in ordered]}

def record_event(t: str, item_id: int | None, meta: Dict[str, Any] | None):
    with conn() as c:
        c.execute("INSERT INTO events(type,item_id,meta) VALUES(?,?,?)", (t, item_id, json.dumps(meta or {})))
        c.commit()

def get_item(item_id: int):
    with conn() as c:
        r = c.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if not r: return None
        d = dict(r)
        try: d["meta"] = json.loads(d["meta"])
        except: d["meta"] = {}
        return d

def set_item_summary(item_id: int, summary):
    with conn() as c:
        c.execute("UPDATE items SET summary=? WHERE id=?", (json.dumps(summary), item_id))
        c.commit()

def items_since(iso_ts: str):
    with conn() as c:
        rows = c.execute("SELECT * FROM items WHERE created_at>=? ORDER BY id DESC", (iso_ts,)).fetchall()
        out=[]
        for r in rows:
            d=dict(r)
            try: d["meta"]=json.loads(d["meta"])
            except: d["meta"]={}
            out.append(d)
        return out

def hot_topics(days:int=3, k:int=8) -> list[str]:
    import re, collections
    cutoff = (dt.datetime.utcnow() - dt.timedelta(days=days)).isoformat()
    with conn() as c:
        rows = c.execute("SELECT title FROM items WHERE created_at>=?", (cutoff,)).fetchall()
    stop = set("""a an the and or of for to in on with by from is are was were be as at into about over under after before via using new open release model ai llm paper code how why what when where this that these those we you they i he she it not vs than more less""".split())
    words = []
    bigrams = collections.Counter()
    for r in rows:
        t = (r["title"] or "").lower()
        tokens = re.findall(r"[a-z0-9][a-z0-9\-\+\.]{1,}", t)
        tokens = [x for x in tokens if x not in stop and len(x)>2]
        words.extend(tokens)
        for i in range(len(tokens)-1):
            bigrams[tokens[i] + " " + tokens[i+1]] += 1
    uni = collections.Counter(words)
    hot = [w for w,_ in bigrams.most_common(k//2)] + [w for w,_ in uni.most_common(k)]
    seen=set(); out=[]
    for h in hot:
        if h not in seen:
            seen.add(h); out.append(h)
    return out[:k]
