from .config import settings
from openai import OpenAI

def estimated_cost_usd(model:str, prompt_tokens:int, completion_tokens:int)->float:
    in_rate = 0.00015 / 1000.0
    out_rate = 0.00060 / 1000.0
    return prompt_tokens*in_rate + completion_tokens*out_rate

_client=None
def client():
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not set")
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client

SYSTEM = "You are a concise, blunt analyst. Write exactly 3 bullets: (1) what happened, (2) why it matters for AI/tech, (3) actionables (or 'none'). Then a ONE-line 'AI Take'—direct, no hedging. If rumor, say so explicitly."

def summarize_items(items, budget_usd: float):
    if not items: return []
    cli = client()
    out=[]
    remaining=budget_usd
    for it in items:
        try:
            user_content = "TITLE: " + it.get("title","") + "\n" +                            "URLS: " + ", ".join(it.get("urls", [])) + "\n" +                            "Return 3 bullets and a one-line 'AI Take:'"
            messages=[
                {"role":"system","content":SYSTEM},
                {"role":"user","content": user_content}
            ]
            resp=cli.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=240
            )
            txt=resp.choices[0].message.content.strip()
            lines=[l.strip(" -•\t") for l in txt.splitlines() if l.strip()]
            bullets=[]; ai_take=""
            for l in lines:
                if l.lower().startswith("ai take"):
                    ai_take = l.split(":",1)[-1].strip() if ":" in l else l
                else:
                    bullets.append(l)
            bullets=bullets[:3]
            usage=resp.usage
            pt=getattr(usage,"prompt_tokens",500); ct=getattr(usage,"completion_tokens",200)
            cost=estimated_cost_usd(settings.OPENAI_MODEL, pt, ct)
            remaining -= cost
            out.append({"id":it.get("id"), "bullets":bullets, "ai_take":ai_take, "cost":cost})
            if remaining <= 0:
                break
        except Exception:
            out.append({"id":it.get("id"), "bullets": [], "ai_take": "", "cost": 0.0})
    return out
