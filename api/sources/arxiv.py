from .common import fetch_rss
ARXIV={
    "cs.AI":"http://export.arxiv.org/rss/cs.AI",
    "cs.LG":"http://export.arxiv.org/rss/cs.LG",
    "cs.CL":"http://export.arxiv.org/rss/cs.CL",
    "cs.CV":"http://export.arxiv.org/rss/cs.CV",
    "stat.ML":"http://export.arxiv.org/rss/stat.ML",
}
async def collect():
    out=[]
    for name,url in ARXIV.items():
        try:
            for it in await fetch_rss(url):
                it["source"]=f"arXiv {name}"; out.append(it)
        except Exception: continue
    return out
