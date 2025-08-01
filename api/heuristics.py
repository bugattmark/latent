from urllib.parse import urlparse

OFFICIAL_DOMAINS = ["gov.uk","bankofengland.co.uk","ons.gov.uk","thaipbsworld.com","khaosodenglish.com","nationthailand.com",
                    "sec.or.th","nbtc.go.th","pdpc.go.th"]
COUNTRY_BOOST = {"uk":0.3,"th":0.3,"us":0.3,"cn":0.3}

def country_flags(host:str):
    h=host.lower()
    return {
        "uk": any(x in h for x in ["gov.uk","bankofengland","ons.gov.uk","ico.org.uk","ofcom.org.uk","fca.org.uk","cma","hmtreasury"]),
        "th": any(x in h for x in ["thaipbsworld.com","khaosodenglish.com","nationthailand.com","bangkokpost.com","sec.or.th","nbtc.go.th","pdpc.go.th"]),
        "us": any(x in h for x in ["apnews.com","reuters.com","bbc.co.uk","bbc.com","whitehouse.gov","commerce.gov"]),
        "cn": any(x in h for x in ["scmp.com","xinhuanet.com","csdn.net","baidu.com","alibabacloud.com"])
    }

def badges_for(urls):
    b=set()
    for u in urls:
        try:d=urlparse(u).netloc.lower()
        except:continue
        if any(dom in d for dom in OFFICIAL_DOMAINS): b.add("Official")
        if "github.com" in d: b.add("Repo")
        if "cve.mitre.org" in d or "nvd.nist.gov" in d: b.add("Security")
    return sorted(b)

def parse_domain(u:str)->str:
    try:
        return urlparse(u).netloc.lower()
    except: return ""

AGENT_KEYWORDS = ["agent","agents","coding agent","tool-use","tools","langgraph","autogen","executor","browsergym","webarena","gaia","code-as-policies"]
MODEL_TECH = ["model","weights","checkpoint","qwen","gpt","claude","gemini","llama","mistral","transformer","aime","mmlu","sota","benchmark","leaderboard","distill","fine-tune","instruct"]
COMPANY_NEWS = ["acquire","funding","seed","series","partnership","launch","release","sdk","api","cloud","gpu","data center","supercomputer","cluster"]

def keyword_hit(text:str, kws:list[str])->int:
    t=text.lower()
    return int(any(k in t for k in kws))

def importance_base(title:str, urls:list[str], cross_mentions:int=0, reddit_hit:bool=False, hn_hit:bool=False, recency_factor:float=0.5, novelty:float=0.5)->float:
    host = parse_domain(urls[0]) if urls else ""
    rep=0.5
    if any(x in host for x in ["reuters.com","apnews.com","bbc.co"]): rep=1.0
    if any(x in host for x in ["gov.uk","bankofengland","ons.gov.uk","nbtc.go.th","sec.or.th","pdpc.go.th"]): rep=1.0
    if "github.com" in host or "arxiv.org" in host or "huggingface.co" in host: rep=0.9

    flags=country_flags(host)
    cboost=sum(COUNTRY_BOOST[k] for k,v in flags.items() if v)
    cboost=min(cboost,0.5)

    k_agents = 1.5 if keyword_hit(title, AGENT_KEYWORDS) else 0.0
    k_models = 1.3 if keyword_hit(title, MODEL_TECH) else 0.0
    k_company = 1.2 if keyword_hit(title, COMPANY_NEWS) else 0.0
    repo_bonus = 1.0 if "github.com" in " ".join(urls).lower() else 0.0
    discuss = 0.7 if (reddit_hit or hn_hit) else 0.0
    cross = min(cross_mentions,3) * 0.4
    rec = max(0.0, min(recency_factor,1.0)) * 0.6
    nov = max(0.0, min(novelty,1.0)) * 0.6

    return 2.0*rep + cboost + k_agents + k_models + k_company + repo_bonus + discuss + cross + rec + nov

def section_for(title, urls):
    t=title.lower(); u=" ".join(urls).lower()
    if "github.com" in u: return "repos"
    if any(k in t for k in ["company","startup","funding","acquire","series","partner","launch"]) or any(d in u for d in ["techcrunch.com","crunchbase.com"]):
        return "companies"
    if any(k in t for k in ["arxiv","paper","benchmark","aime","mmlu","leaderboard","distill"]):
        return "ai_research"
    if any(k in t for k in ["release","sdk","api","framework","agent","tool"]):
        return "product_releases"
    if any(k in t for k in ["cve","vulnerability","prompt injection","jailbreak","leak"]):
        return "security"
    if any(k in t for k in ["treasury","central bank","inflation","rates"]):
        return "macro"
    return "global_headlines"
