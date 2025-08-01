import httpx
from xml.etree import ElementTree as ET

async def fetch_rss(url: str) -> list[dict]:
    items=[]
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(url, headers={"User-Agent":"research-brief/1.0"})
        r.raise_for_status()
        try: root=ET.fromstring(r.content)
        except Exception: return items
        for it in root.findall(".//item"):
            title=(it.findtext("title") or "").strip()
            link=(it.findtext("link") or "").strip()
            pub=(it.findtext("pubDate") or "").strip()
            if title and link: items.append({"title":title,"link":link,"pubDate":pub})
    return items
