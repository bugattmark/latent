import feedparser, datetime as dt
FEEDS = ["https://feeds.reuters.com/reuters/technologyNews","https://feeds.reuters.com/reuters/worldNews",
         "https://apnews.com/hub/apf-technology?output=rss","https://feeds.bbci.co.uk/news/technology/rss.xml"]
def fetch(max_per_feed=15):
    out = []
    for url in FEEDS:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:max_per_feed]:
                out.append({"source":"Wires","url":e.link,"title":e.title,"section":"News","meta":{"feed":url},
                            "created_at": getattr(e,"published", dt.datetime.utcnow().isoformat())})
        except Exception: continue
    return out
