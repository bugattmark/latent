import httpx

ALGOLIA_SEARCH="https://hn.algolia.com/api/v1/search"
ALGOLIA_ITEM="https://hn.algolia.com/api/v1/items/"

async def fetch_hn_for_url(url: str):
    params={"query": url, "tags":"story", "hitsPerPage": 1}
    async with httpx.AsyncClient(timeout=15) as client:
        r=await client.get(ALGOLIA_SEARCH, params=params, headers={"User-Agent":"research-brief/1.0"})
        r.raise_for_status()
        data=r.json()
        if not data.get("hits"): return None
        return data["hits"][0]

async def fetch_top_comments(object_id:str, limit:int=2):
    async with httpx.AsyncClient(timeout=15) as client:
        r=await client.get(ALGOLIA_ITEM + object_id, headers={"User-Agent":"research-brief/1.0"})
        r.raise_for_status()
        data=r.json()
        comments=data.get("children",[])
        comments=sorted(comments, key=lambda c: (c.get("points",0), len(c.get("children",[]))), reverse=True)
        out=[]
        for c in comments[:limit]:
            if c.get("author") and c.get("text"):
                out.append({"author":c["author"], "score":c.get("points",0), "text":c["text"], "link":"https://news.ycombinator.com/item?id="+object_id})
        return out
