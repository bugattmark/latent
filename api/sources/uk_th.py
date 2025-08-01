from .common import fetch_rss
UK_TH={
    "GOV.UK DSIT":"https://www.gov.uk/government/organisations/department-for-science-innovation-and-technology.atom",
    "ICO":"https://ico.org.uk/rss/feed/",
    "Ofcom":"https://www.ofcom.org.uk/about-ofcom/latest/media/rss",
    "FCA":"https://www.fca.org.uk/news/rss.xml",
    "CMA":"https://www.gov.uk/government/organisations/competition-and-markets-authority.atom",
    "HM Treasury":"https://www.gov.uk/government/organisations/hm-treasury.atom",
    "Bank of England":"https://www.bankofengland.co.uk/boeapps/rss/BOEBaseIndex.aspx?WhichIndex=News",
    "ONS":"https://www.ons.gov.uk/news/rss",
    "Thai PBS World":"https://www.thaipbsworld.com/feed/",
    "Khaosod English":"https://www.khaosodenglish.com/feed/",
    "The Nation Thailand":"https://www.nationthailand.com/rss"
}
async def collect():
    out=[]
    for name,url in UK_TH.items():
        try:
            for it in await fetch_rss(url):
                it["source"]=name; out.append(it)
        except Exception: continue
    return out
