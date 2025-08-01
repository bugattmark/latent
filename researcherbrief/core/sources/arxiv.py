import feedparser, html, datetime as dt
from urllib.parse import urlencode
CATS = ["cs.AI","cs.LG","cs.CL","cs.CV","stat.ML"]
def fetch(max_results=40):
    q = " OR ".join(f"cat:{c}" for c in CATS)
    params = {"search_query": q, "sortBy": "submittedDate", "sortOrder": "descending", "max_results": max_results}
    url = "http://export.arxiv.org/api/query?" + urlencode(params, safe=":")
    feed = feedparser.parse(url); out = []
    for e in feed.entries:
        out.append({"source":"arXiv","url":e.link,"title":html.unescape(e.title),"section":"AI Research",
                    "meta":{"authors":[a.name for a in getattr(e,"authors",[])],"abstract":getattr(e,"summary","")},
                    "created_at": getattr(e,"published", dt.datetime.utcnow().isoformat())})
    return out
