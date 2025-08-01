import os, json, time, pathlib
from .logging import logger
_client = None
def _client_ok():
    global _client
    if _client is not None: return _client
    key = os.getenv("OPENAI_API_KEY")
    if not key: return None
    try:
        from openai import OpenAI
    except Exception as e:
        logger.error(f"OpenAI SDK not available: {e}")
        return None
    _client = OpenAI(api_key=key)
    return _client
SPEND_FILE = pathlib.Path("data/spend.json")
def _load_spend():
    if SPEND_FILE.exists():
        try: return json.loads(SPEND_FILE.read_text())
        except Exception: pass
    return {"day": time.strftime("%Y-%m-%d"), "usd": 0.0}
def _save_spend(obj): SPEND_FILE.parent.mkdir(parents=True, exist_ok=True); SPEND_FILE.write_text(json.dumps(obj))
def under_budget():
    cap = float(os.getenv("SUMMARY_DAILY_CAP_USD", "1.0"))
    s = _load_spend()
    if s["day"] != time.strftime("%Y-%m-%d"):
        s = {"day": time.strftime("%Y-%m-%d"), "usd": 0.0}; _save_spend(s)
    return s["usd"] < cap
def _charge(usd):
    s = _load_spend()
    if s["day"] != time.strftime("%Y-%m-%d"):
        s = {"day": time.strftime("%Y-%m-%d"), "usd": 0.0}
    s["usd"] += float(usd); _save_spend(s)
def summarize_to_struct(title: str, text: str) -> dict:
    cli = _client_ok()
    if not cli or not under_budget():
        txt = (text or title or "").replace("\n", " ")
        parts = [p.strip() for p in txt.split(".") if p.strip()][:3]
        return {"bullets": parts[:3], "take": (title or "")[:140]}
    prompt = f"""You are a terse analyst. Summarize for an expert daily brief.
Title: {title}
Context:
{text}
Return EXACTLY JSON with keys "bullets" (array of 3 strings, each <=20 words) and "take" (<=18 words). No extra text.
"""
    try:
        msg = _client_ok().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
            response_format={"type":"json_object"}
        )
        import json as _json
        j = _json.loads(msg.choices[0].message.content)
        _charge(0.01)
        return {"bullets": j.get("bullets", [])[:3], "take": j.get("take","")}
    except Exception as e:
        logger.error(f"summarize failed: {e}")
        return {"bullets": [], "take": ""}
