import os, praw
cid = os.getenv('REDDIT_CLIENT_ID'); sec = os.getenv('REDDIT_CLIENT_SECRET'); ua = os.getenv('REDDIT_USER_AGENT')
print('CID len:', len(cid), 'SECRET len:', len(sec), 'UA ok:', bool(ua))
r = praw.Reddit(client_id=cid, client_secret=sec, user_agent=ua, check_for_async=False)
r.read_only = True
print('Title:', next(iter(r.subreddit('machinelearning').hot(limit=1))).title)
