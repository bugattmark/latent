import httpx, datetime as dt
ALG = "https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=points>50&hitsPerPage=50"
def fetch():
    try: hits = httpx.get(ALG, timeout=15).json().get("hits", [])
    except Exception: return []
    out = []
    for h in hits:
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        out.append({"source":"HN","url":url,"title":h.get("title",""),"section":"Threads",
                    "meta":{"points":h.get("points",0),"num_comments":h.get("num_comments",0),"hn_id":h.get("objectID")},
                    "created_at":h.get("created_at") or dt.datetime.utcnow().isoformat()})
    return out
