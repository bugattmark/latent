import React from "react";
const API = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/* helpers */
function fmtDomain(u){ try{ return new URL(u).hostname.replace(/^www\./,""); }catch{ return ""; } }
function topicLine(t){
  const f=t.features||{}; const ex=(t.examples&&t.examples[0])||null;
  const why=`v=${(+(f.velocity||0)).toFixed(1)}, xsrc=${f.cross_source||0}, disc=${(+(f.discussion||0)).toFixed(1)}`;
  return ex ? `${t.label} — ${ex.title} (${fmtDomain(ex.url)}) · ${why}` : `${t.label} · ${why}`;
}
function studyLine(t){
  const f=t.features||{}; const ex=(t.examples&&t.examples[0])||null;
  const why=`study ${(+(t.study_score||0)).toFixed(2)} · v=${(+(f.velocity||0)).toFixed(1)}`;
  return ex ? `${t.label} — ${ex.title} (${fmtDomain(ex.url)}) · ${why}` : `${t.label} · ${why}`;
}
function useBrief(){
  const [data,setData]=React.useState(null), [err,setErr]=React.useState("");
  const load=React.useCallback(()=>{ fetch(`${API}/brief/today`).then(r=>r.ok?r.json():Promise.reject()).then(setData).catch(()=>setErr("Brief not ready. Run the worker once.")); },[]);
  React.useEffect(()=>{ load(); },[load]); return {data,err,setData,reload:load};
}

/* sections */
function HotNow(){
  const [items,setItems]=React.useState([]);
  React.useEffect(()=>{ fetch(`${API}/trends/hot`).then(r=>r.json()).then(d=>setItems((d.topics||[]).slice(0,6))).catch(()=>setItems([])); },[]);
  if(!items.length) return null;
  return (<><h2>Hot now</h2><ul className="bullets">{items.map((t,i)=><li key={i}>{topicLine(t)}</li>)}</ul></>);
}
function StudyNext(){
  const [items,setItems]=React.useState([]);
  React.useEffect(()=>{ fetch(`${API}/study/next`).then(r=>r.json()).then(d=>setItems((d.topics||[]).slice(0,5))).catch(()=>setItems([])); },[]);
  if(!items.length) return null;
  return (<><h2>Study next</h2><ul className="bullets">{items.map((t,i)=><li key={i}>{studyLine(t)}</li>)}</ul></>);
}

const Tabs=["Top Picks","News","Releases","Threads","Research","Global"];

export default function App(){
  const {data,err,setData}=useBrief();
  const [tab,setTab]=React.useState("Top Picks");

  React.useEffect(()=>{
    if(tab==="Top Picks") return;
    const map={News:"news",Releases:"releases",Threads:"threads",Research:"research",Global:"global"};
    fetch(`${API}/feed/${map[tab]}`).then(r=>r.json()).then(j =>
      setData(prev=>prev?{...prev,top_picks:j.items}:{date:"",top_picks:j.items})
    );
  },[tab]);

  const send=(type,item)=>fetch(`${API}/events`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({type,item_id:item.id,meta:{url:item.url}})});
  const summarize=async(item)=>{
    const btn=document.getElementById(`btn-${item.id}`); if(btn){btn.disabled=true;btn.textContent="Summarizing…";}
    try{
      const res=await fetch(`${API}/items/${item.id}/summarize`,{method:"POST"});
      if(!res.ok) throw new Error(await res.text());
      const updated=await res.json();
      setData(prev=>({...prev, top_picks:(prev.top_picks||[]).map(i=>i.id===updated.id?updated:i)}));
    }catch(e){ console.error(e); alert("Summarize failed (check API key/budget)."); }
    finally{ if(btn){btn.disabled=false;btn.textContent="Summarize";} }
  };

  if(err) return <div className="wrap"><h1>Researcher Brief</h1><div style={{color:"red"}}>{err}</div></div>;
  if(!data) return <div className="wrap"><h1>Researcher Brief</h1><div>Loading…</div></div>;

  const Card=({item})=>{
    const renderSummary=()=>{
      const s=item.summary; if(!s) return null;
      try{
        const j=typeof s==="string"?JSON.parse(s):s;
        const bullets=Array.isArray(j.bullets)?j.bullets:[];
        const take=j.take?String(j.take):"";
        return (<>{bullets.length?<ul className="bullets">{bullets.map((b,i)=><li key={i}>{b}</li>)}</ul>:null}{take?<div className="take">AI Take: {take}</div>:null}</>);
      }catch{ return <div className="muted">{String(s)}</div>; }
    };
    return (
      <div className="card">
        <div className="section">{item.section}</div>
        <a className="title" href={item.url} target="_blank" rel="noreferrer" onClick={()=>send("click",item)}>{item.title}</a>
        {renderSummary()}
        <div className="row">
          <button id={`btn-${item.id}`} onClick={()=>summarize(item)}>Summarize</button>
          <button onClick={()=>send("like",item)}>Like</button>
          <button onClick={()=>send("skip",item)}>Skip</button>
          <button onClick={()=>send("open_long_read",item)}>Long read</button>
        </div>
      </div>
    );
  };

  return (
    <div className="wrap">
      <h1>Researcher Brief</h1>
      <HotNow />
      <StudyNext />
      <div className="tabs">{Tabs.map(t=><div key={t} className={"tab"+(tab===t?" active":"")} onClick={()=>setTab(t)}>{t}</div>)}</div>
      <div className="grid">{(data.top_picks||[]).map(i=><Card key={i.id} item={i} />)}</div>
    </div>
  );
}
