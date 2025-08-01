from .arxiv import fetch as arxiv_fetch
from .hn import fetch as hn_fetch
from .wires import fetch as wires_fetch
from .official import fetch as official_fetch
from .releases import fetch as releases_fetch
from .reddit import fetch as reddit_fetch
def fetch_all():
    rows = []
    for f in [arxiv_fetch, hn_fetch, reddit_fetch, official_fetch, wires_fetch, releases_fetch]:
        try: rows += f()
        except Exception: pass
    return rows
