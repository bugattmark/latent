import feedparser, datetime as dt
FEEDS = ["https://ai.googleblog.com/atom.xml","https://deepmind.google/discover/feeds/rss.xml",
         "https://openai.com/blog/rss.xml","https://www.anthropic.com/news/rss.xml",
         "https://www.meta.ai/blog/rss/","https://huggingface.co/blog/feed.xml","https://developer.nvidia.com/blog/feed/"]
def fetch(max_per_feed=10):
    out = []
    for url in FEEDS:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:max_per_feed]:
                out.append({"source":"Official","url":e.link,"title":e.title,"section":"AI News","meta":{"feed":url},
                            "created_at": getattr(e,"published", dt.datetime.utcnow().isoformat())})
        except Exception: continue
    return out
