# researcherbrief/worker/scheduler.py
import asyncio, argparse, os, json, re, math, collections
import datetime as dt

from researcherbrief.core.logging import logger
from researcherbrief.core.sources import fetch_all
from researcherbrief.core.heuristics import score_item
from researcherbrief.core.db import init_db, upsert_items, top_ids, save_brief, conn, items_since
from researcherbrief.core.llm import summarize_to_struct
from researcherbrief.core.config import get_settings

# ---- time helpers (robust + timezone-aware) ---------------------------------
UTC = dt.timezone.utc
EPOCH = dt.datetime(1970, 1, 1, tzinfo=UTC)

def _safe_dt(val):
    """Parse many shapes into aware UTC dt; return None for garbage."""
    if not val:
        return None
    try:
        s = str(val).strip()
        # epoch seconds
        if s.isdigit():
            return dt.datetime.utcfromtimestamp(int(s)).replace(tzinfo=UTC)
        # tolerate trailing 'Z'
        s = s.replace("Z", "")
        d = dt.datetime.fromisoformat(s)
        # normalize to aware UTC
        if d.tzinfo is None:
            d = d.replace(tzinfo=UTC)
        else:
            d = d.astimezone(UTC)
        return d
    except Exception:
        return None

def _auto_summarize() -> bool:
    return os.getenv("SUMMARY_AUTO", "").lower() in {"1", "true", "yes", "y"}

# ---- lightweight text features ----------------------------------------------
_token_re = re.compile(r"[a-z0-9][a-z0-9\-\+\.]{1,}")
_stop = set(
    """
    a an the and or of for to in on with by from is are was were be as at into about over
    under after before via using new open release model ai llm paper code how why what when
    where this that these those we you they i he she it not vs than more less
    """.split()
)

def _tokens(text: str):
    return [t for t in _token_re.findall((text or "").lower()) if len(t) > 2 and t not in _stop]

def _vec(text: str):
    return collections.Counter(_tokens(text))

def _cos(a: collections.Counter, b: collections.Counter):
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0) for k in a.keys())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

def _label(titles):
    big = collections.Counter()
    uni = collections.Counter()
    for t in titles:
        toks = _tokens(t)
        for i in range(len(toks) - 1):
            big[toks[i] + " " + toks[i + 1]] += 1
        for tok in toks:
            uni[tok] += 1
    cand = [w for w, _ in big.most_common(3)] + [w for w, _ in uni.most_common(5)]
    seen = set()
    out = []
    for c in cand:
        if c not in seen:
            seen.add(c)
            out.append(c)
        if len(out) >= 3:
            break
    return " • ".join(out) if out else (titles[0][:60] if titles else "topic")

def _cluster_items(items, thresh=0.78):
    clusters = []
    for it in items:
        v = _vec(it["title"] + " " + it.get("section", "") + " " + it.get("source", ""))
        best = -1
        best_sim = 0.0
        for idx, c in enumerate(clusters):
            sim = _cos(v, c["centroid"])
            if sim > best_sim:
                best_sim = sim
                best = idx
        if best_sim >= thresh and best != -1:
            c = clusters[best]
            c["members"].append(it)
            for k, val in v.items():
                c["centroid"][k] += val
        else:
            clusters.append({"centroid": v, "members": [it]})
    return clusters

def _compute_features(cluster, now_utc: dt.datetime):
    """Features for a cluster. `now_utc` MUST be aware UTC."""
    members = cluster["members"]
    t_24 = now_utc - dt.timedelta(hours=24)
    t_48 = now_utc - dt.timedelta(hours=48)

    def as_dt(ts):
        return _safe_dt(ts) or now_utc  # fall back to now if garbage

    freq_t = sum(1 for m in members if as_dt(m.get("created_at")) >= t_24)
    freq_prev = sum(1 for m in members if (t_48 <= as_dt(m.get("created_at")) < t_24))
    velocity = (freq_t + 0.5) / (freq_prev + 0.5)

    disc = 0.0
    for m in members:
        meta = m.get("meta") or {}
        if m.get("source") == "HN":
            disc += 0.0004 * int(meta.get("points", 0)) + 0.0002 * int(meta.get("num_comments", 0))
        if m.get("source") == "Reddit":
            disc += 0.0005 * int(meta.get("score", 0)) + 0.0002 * int(meta.get("num_comments", 0))

    cross = len(set(m.get("source") for m in members))

    def decay(ts):
        d = as_dt(ts)
        hours = max(0.0, (now_utc - d).total_seconds() / 3600.0)
        return math.exp(-hours / 18.0)

    rec = sum(decay(m.get("created_at")) for m in members) / max(1, len(members))
    return {
        "velocity": float(velocity),
        "discussion": float(disc),
        "cross_source": int(cross),
        "recency": float(rec),
    }

def _hotness(feat):
    return 1.6 * feat["velocity"] + 1.2 * feat["cross_source"] + 1.0 * feat["discussion"] + 0.6 * feat["recency"]

def _study_score(cluster, all21d):
    label = _label([m["title"] for m in cluster["members"]])
    toks = set(_tokens(label))
    def has_overlap(t): return len(toks.intersection(set(_tokens(t)))) > 0

    now = dt.datetime.now(UTC)

    last3 = [
        it for it in all21d
        if (_safe_dt(it.get("created_at")) or EPOCH) >= (now - dt.timedelta(days=3))
        and has_overlap(it["title"])
    ]
    prev7 = [
        it for it in all21d
        if (now - dt.timedelta(days=10)) <= (_safe_dt(it.get("created_at")) or EPOCH) < (now - dt.timedelta(days=3))
        and has_overlap(it["title"])
    ]

    research_growth = (sum(1 for it in last3 if it["source"] == "arXiv") + 0.5) / (sum(1 for it in prev7 if it["source"] == "arXiv") + 0.5)
    release_cadence = (sum(1 for it in last3 if it["source"] in {"Releases", "Official"}) + 0.5) / 5.0

    adoption_chatter = 0.0
    for it in last3:
        if it["source"] in {"HN", "Reddit"}:
            meta = it.get("meta") or {}
            adoption_chatter += 0.0005 * int(meta.get("num_comments", 0)) + 0.0003 * int(meta.get("score", meta.get("points", 0)))

    breadth = len(set(it["source"] for it in last3)) / 6.0
    return 0.8 * research_growth + 0.8 * release_cadence + 1.0 * adoption_chatter + 0.6 * breadth

def _detect_migrations(rows):
    patt = re.compile(r"(migrat(?:e|ion)|switch(?:ed)?|replac(?:e|ed)|move(?:d)?|ditch(?:ed)?)\s+(from|off)?\s*([^\s]+)\s*(to|->)\s*([^\s]+)", re.I)
    out = []
    for r in rows:
        title = r.get("title", "")
        for m in patt.finditer(title):
            x, y = m.group(3), m.group(5); out.append((x, y, title, r.get("url"), r.get("source"), 0.7))
        cmts = (r.get("meta") or {}).get("comments") or []
        for c in cmts:
            txt = c.get("body", ""); m = patt.search(txt)
            if m:
                x, y = m.group(3), m.group(5); out.append((x, y, txt, r.get("url"), r.get("source"), 0.8))
    if not out:
        return
    with conn() as c:
        for x, y, sent, link, src, conf in out:
            c.execute(
                "INSERT INTO migrations(ts,x,y,sentence,link,source,confidence) VALUES(datetime('now'),?,?,?,?,?,?)",
                (x, y, sent[:400], link, src, conf),
            )
        c.commit()

def _compute_topics():
    s = get_settings()
    now = dt.datetime.now(dt.timezone.utc)

    # windowing
    last3_cut = (now - dt.timedelta(days=s.hot_window_days)).isoformat()
    items3 = items_since(last3_cut)

    # cluster
    clusters = _cluster_items(items3, thresh=0.78)

    # AI/tech gate
    ai_terms = {
        "qwen","llama","gpt","deepseek","mistral","mixtral","moe","agent","agents",
        "rlhf","grpo","reasoning","tool","inference","weights","release","sdk",
        "model","checkpoint","dataset","benchmark","arxiv","open-source","hf",
        "self-play","self-learn","self-improve","optimizer","compiler","vllm",
        "tensor","cuda","flash","kv","search","retrieval","rag"
    }
    def is_ai_topic(label):
        toks = set(_tokens(label))
        return len(toks.intersection(ai_terms)) > 0

    # 21-day window for study score
    last21_cut = (now - dt.timedelta(days=s.study_window_days)).isoformat()
    items21 = items_since(last21_cut)

    rows = []
    for c in clusters:
        titles = [m["title"] for m in c["members"]]
        label = _label(titles)
        feats = _compute_features(c, now)

        # require cross-source >= 2 and pass AI gate
        if feats["cross_source"] < 2: 
            continue
        if not is_ai_topic(label):
            continue

        hot = _hotness(feats)
        study = _study_score(c, items21)
        members = [m.get("id") for m in c["members"] if m.get("id")]
        rows.append((label, hot, study, members, feats))

    # keep the most important few
    rows.sort(key=lambda x: x[1], reverse=True)
    rows = rows[:6]

    with conn() as c:
        c.execute("DELETE FROM topics WHERE created_at < datetime('now','-4 days')")
        for label, hot, study, members, feats in rows:
            c.execute(
                "INSERT INTO topics(label,window_start,window_end,hotness,study_score,members,features) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    label,
                    (now - dt.timedelta(days=s.hot_window_days)).isoformat(),
                    now.isoformat(),
                    float(hot),
                    float(study),
                    json.dumps(members),
                    json.dumps(feats),
                ),
            )
        c.commit()


# ---- public entrypoints ------------------------------------------------------
async def job_once():
    init_db()
    logger.info("Worker cycle starting…")

    rows = fetch_all()
    for r in rows:
        r["score"] = score_item(r)
    upsert_items(rows)
    _detect_migrations(rows)

    ids = top_ids(48)
    save_brief(dt.date.today().isoformat(), ids)

    if _auto_summarize() and ids:
        max_items = int(os.getenv("SUMMARY_MAX_ITEMS", "12"))
        with conn() as c:
            placeholders = ",".join("?" * len(ids))
            top = c.execute(
                f"SELECT id,title,meta FROM items WHERE id IN ({placeholders}) AND source='arXiv' LIMIT ?",
                (*ids, max_items),
            ).fetchall()
            for r in top:
                meta = json.loads(r["meta"])
                abstract = meta.get("abstract", "")
                s = summarize_to_struct(r["title"], abstract)
                c.execute("UPDATE items SET summary=? WHERE id=?", (json.dumps(s), r["id"]))
            c.commit()
        logger.info(f"Stored {len(rows)} items; summarized up to {len(top)}; brief updated with {len(ids)} top picks.")
    else:
        reason = "disabled" if not _auto_summarize() else "no top picks"
        logger.info(f"Stored {len(rows)} items; summaries {reason}; brief updated with {len(ids)} top picks.")

    _compute_topics()
    logger.info("Cycle complete")

async def schedule_loop(interval_s: int = 3600):
    while True:
        await job_once()
        await asyncio.sleep(interval_s)

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=3600)
    args = parser.parse_args()
    logger.info("Worker online")
    if args.once:
        asyncio.run(job_once()); return
    asyncio.run(schedule_loop(args.interval))

if __name__ == "__main__":
    run()
