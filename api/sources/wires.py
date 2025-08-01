from .common import fetch_rss
WIRES={
    "Reuters":"https://feeds.reuters.com/reuters/topNews",
    "AP":"https://apnews.com/hub/ap-top-news?utm_source=apnews.com&utm_medium=referral&utm_campaign=ap-rss&utm_id=ap-rss",
    "BBCWorld":"http://feeds.bbci.co.uk/news/world/rss.xml",
    "BBCTech":"http://feeds.bbci.co.uk/news/technology/rss.xml"
}
async def collect():
    out=[]
    for name,url in WIRES.items():
        try:
            for it in await fetch_rss(url):
                it["source"]=name; out.append(it)
        except Exception: continue
    return out
