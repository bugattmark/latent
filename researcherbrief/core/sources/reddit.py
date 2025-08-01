from researcherbrief.core.config import get_settings
from researcherbrief.core.logging import logger
import datetime as dt
import os, praw

SUBS = ["localLLaMA","MachineLearning","mlops","LanguageTechnology","programming","OpenAI","computervision","technology"]
def fetch(limit=40):
    s = get_settings()
    if not (s.reddit_client_id and s.reddit_client_secret):
        logger.info("reddit: creds missing; skipping"); return []
    try:
        import praw
        reddit = praw.Reddit(client_id=s.reddit_client_id, client_secret=s.reddit_client_secret, user_agent=s.reddit_user_agent)
    except Exception as e:
        logger.info(f"reddit init failed: {e}"); return []
    out = []
    try:
        per = max(1, limit//len(SUBS))
        for sub in SUBS:
            for post in reddit.subreddit(sub).top(time_filter="day", limit=per):
                comments = []
                try:
                    post.comments.replace_more(limit=0)
                    for c in post.comments[:5]:
                        txt = (c.body or "")
                        if len(txt) > 12:
                            comments.append({"author": str(c.author), "score": int(getattr(c,"score",0)), "body": txt, "permalink": f"https://reddit.com{c.permalink}"})
                except Exception: pass
                out.append({"source":"Reddit","url":f"https://reddit.com{post.permalink}","title":post.title,"section":"Threads",
                            "meta":{"kind":"reddit","sub":sub,"score":int(getattr(post,'score',0)),"num_comments":int(getattr(post,'num_comments',0)),"comments":comments},
                            "created_at": dt.datetime.utcfromtimestamp(int(post.created_utc)).isoformat()})
    except Exception as e:
        logger.info(f"reddit fetch failed: {e}")
    return out

def _reddit():
    r = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT") or "researcherbrief/dev",
        check_for_async=False,   # <- stops the spam
    )
    r.read_only = True
    return r