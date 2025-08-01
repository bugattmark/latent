import httpx, time

SUBS=["MachineLearning","LocalLLaMA","ArtificialIntelligence","DeepLearning","StableDiffusion","PromptEngineering","ChatGPT","OpenAI","technology","programming"]

def headers(): return {"User-Agent":"research-brief/1.0 by yourusername"}

async def fetch_top(client, sub):
    url=f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=25"
    r=await client.get(url, headers=headers()); r.raise_for_status()
    data=r.json(); items=[]
    for c in data.get("data",{}).get("children",[]):
        d=c["data"]
        items.append({
            "title": d.get("title"),
            "permalink": "https://www.reddit.com"+d.get("permalink",""),
            "url": d.get("url_overridden_by_dest") or d.get("url"),
            "created_utc": d.get("created_utc"),
            "subreddit": sub,
            "score": d.get("score",0)
        })
    return items

async def fetch_comments(permalink:str, client: httpx.AsyncClient):
    try:
        r=await client.get(permalink+'.json?limit=5', headers=headers())
        r.raise_for_status()
        j=r.json()
        if not isinstance(j,list) or len(j)<2: return []
        comments=j[1].get("data",{}).get("children",[])
        out=[]
        for c in comments:
            d=c.get("data",{})
            if d.get("author") and not d.get("is_submitter"):
                body=d.get("body")
                if body: out.append({"author":d["author"],"score":d.get("score",0),"text":body,"link":permalink})
            if len(out)>=2: break
        return out
    except Exception:
        return []

async def collect():
    out=[]
    async with httpx.AsyncClient(timeout=20) as client:
        for s in SUBS:
            try:
                posts = await fetch_top(client,s)
                for p in posts:
                    p["comments"]=await fetch_comments(p["permalink"], client)
                out.extend(posts); time.sleep(0.5)
            except Exception: continue
    return out
