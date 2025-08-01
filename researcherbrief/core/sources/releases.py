import httpx, datetime as dt
def fetch(limit=30):
    out = []
    try:
        r = httpx.get("https://huggingface.co/api/models?sort=modified&direction=-1&limit=20", timeout=15)
        for m in r.json():
            name = m.get("modelId",""); last = m.get("lastModified") or dt.datetime.utcnow().isoformat()
            out.append({"source":"Releases","url":f"https://huggingface.co/{name}","title":f"Model updated: {name}","section":"Releases","meta":{"provider":"hf"},"created_at":last})
    except Exception: pass
    for pkg in ["transformers","vllm","tensorrt-llm","exllamav2","ollama"]:
        try:
            r = httpx.get(f"https://pypi.org/pypi/{pkg}/json", timeout=15)
            info = r.json().get("info", {}); ver = info.get("version")
            out.append({"source":"Releases","url":f"https://pypi.org/project/{pkg}/{ver}/","title":f"{pkg} {ver} released","section":"Releases","meta":{"provider":"pypi"},"created_at": info.get("release_url","") or dt.datetime.utcnow().isoformat()})
        except Exception: continue
    return out
