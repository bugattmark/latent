import re
KEY_BOOSTS = [
  (r"\bagent(s)?\b", 1.0),
  (r"\b(model|weights|checkpoint|llama|qwen|mixtral|moe)\b", 0.8),
  (r"\bstartups?\b", 0.4),
  (r"\brelease|v\d+\.\d+|sdk|model card\b", 0.6),
  (r"\bbenchmark|eval|throughput|latency|kv cache|speculative\b", 0.5),
]
SRC_WEIGHTS = {"arXiv":1.2,"Official":1.0,"Wires":0.9,"Releases":1.0,"HN":0.7,"Reddit":0.8}
def score_item(r: dict) -> float:
    t = (r.get("title") or "").lower()
    base = SRC_WEIGHTS.get(r.get("source"), 0.5)
    for pat, w in KEY_BOOSTS:
        if re.search(pat, t): base += w
    meta = r.get("meta") or {}
    if r.get("source")=="Reddit":
        base += 0.0005 * int(meta.get("score",0)) + 0.0002 * int(meta.get("num_comments",0))
    if r.get("source")=="HN":
        base += 0.0004 * int(meta.get("points",0)) + 0.0002 * int(meta.get("num_comments",0))
    return round(base, 4)
