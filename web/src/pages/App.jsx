import React, { useEffect, useMemo, useState } from 'react'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const Chip = ({ children }) => (
  <span style={{
    display: 'inline-block', fontSize: 12, padding: '2px 8px',
    borderRadius: 999, background: '#eef2ff', color: '#334155',
    border: '1px solid #e2e8f0', marginRight: 6
  }}>{children}</span>
)

function ItemBullets({ id }){
  const [item, setItem] = useState(null)
  const [preview, setPreview] = useState(null)
  useEffect(()=>{
    let alive=true
    fetch(`${API}/items/${id}`).then(r=>r.json()).then(d=>{ if(alive) setItem(d) }).catch(()=>{})
    return ()=>{ alive=false }
  },[id])
  useEffect(()=>{
    let alive=true
    const c=(item?.urls||[]).slice(0,3)
    if(!c.length) return
    const params=c.map(u=>`url=${encodeURIComponent(u)}`).join('&')
    fetch(`${API}/preview/best?${params}`).then(r=>r.json()).then(d=>{ if(alive && d?.image) setPreview(d.image) }).catch(()=>{})
    return ()=>{ alive=false }
  },[item?.urls])
  if(!item) return null

  const bullets = (item.summary && item.summary !== item.title) ? item.summary.split('\n').slice(0,3) : null
  const aiTake = item.ai_take

  return (
    <div style={{background:'#fff', border:'1px solid #e5e7eb', borderRadius:12, padding:12, marginBottom:12}}>
      <div style={{display:'flex', gap:12}}>
        <div style={{flex:1}}>
          <div style={{ fontWeight: 700, fontSize: 16, lineHeight: 1.3, marginBottom: 8 }}>{item.title}</div>
          {aiTake && <div className="muted" style={{fontSize:13, marginBottom:8}}>AI Take: {aiTake}</div>}
          {bullets && bullets.length>0 && (
            <ul style={{margin:'6px 0 8px 18px', padding:0}}>
              {bullets.map((b,i)=>(<li key={i}>{b}</li>))}
            </ul>
          )}
          <div style={{ marginBottom: 6 }}>
            {item.urls?.[0] && <a href={item.urls[0]} target="_blank" rel="noreferrer">Open source</a>}
          </div>
          <div style={{ fontSize: 12, opacity:.8 }}>
            {item.urls?.slice(1).map(u=><div key={u}><a href={u} target="_blank" rel="noreferrer">{u}</a></div>)}
          </div>
          <div style={{ marginTop: 8 }}>
            {item.badges?.map(b => <Chip key={b}>{b}</Chip>)}
          </div>
        </div>
        <div style={{width:220}}>
          <div style={{ borderRadius:10, overflow:'hidden', width:'100%', height:120, background:'#eef2f7', display:'flex', alignItems:'center', justifyContent:'center' }}>
            {preview ? <img src={preview} alt="" loading="lazy" style={{width:'100%',height:'100%',objectFit:'cover'}}/> : <span style={{fontSize:12, color:'#788'}}>No preview</span>}
          </div>
          {item.comments?.length>0 && (
            <div style={{ marginTop: 10, fontSize: 12 }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>People say</div>
              {item.comments.slice(0,2).map((c,idx)=>(
                <div key={idx} style={{ marginBottom: 6 }}>
                  <div style={{opacity:.8}}>@{c.author} · {c.score ?? 0}</div>
                  <div dangerouslySetInnerHTML={{__html: c.text}} />
                  {c.link && <div><a href={c.link} target="_blank" rel="noreferrer">Thread</a></div>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function SectionList({ title, ids, cap=999 }){
  if(!ids?.length) return null
  const shown = ids.slice(0, cap)
  const more = ids.length - shown.length
  return (
    <section style={{ marginTop: 24 }}>
      <h3 style={{ fontSize: 20 }}>{title}</h3>
      <div>
        {shown.map(id => <ItemBullets key={id} id={id} />)}
      </div>
      {more>0 && <div className="muted" style={{fontSize:13, marginTop:6}}>{more} more…</div>}
    </section>
  )
}

export default function App(){
  const [brief,setBrief]=useState(null); const [error,setError]=useState(null)
  useEffect(()=>{
    fetch(`${API}/brief/today?view=bullets&limit=48&personalized=true`)
      .then(async r=>{ if(!r.ok) throw new Error(await r.text()); return r.json() })
      .then(setBrief).catch(e=>setError(e.message))
  },[])

  const localGen = brief ? new Date(brief.generated_at) : null
  const localGenStr = localGen ? localGen.toLocaleString([], { hour12: false, timeZoneName: 'short' }) : ''

  const sectionsOrder = useMemo(()=>[
    ["Top Picks", brief?.top_picks || []],
    ["AI Research & Breakthroughs", brief?.sections?.ai_research || []],
    ["AI Product/SDK & Agent Releases", brief?.sections?.product_releases || []],
    ["Companies & Startups", brief?.sections?.companies || []],
    ["Notable Repos", brief?.sections?.repos || []],
    ["Policy & Officials", brief?.sections?.policy || []],
    ["Security/Abuse", brief?.sections?.security || []],
    ["Global Headlines", brief?.sections?.global_headlines || []],
    ["Markets/Macro/Funding/Calendar", [
      ...(brief?.sections?.markets||[]),
      ...(brief?.sections?.macro||[]),
      ...(brief?.sections?.funding||[]),
      ...(brief?.sections?.calendar||[])
    ]],
  ],[brief])

  return (
    <div style={{ padding: 20, maxWidth: 1180, margin: '0 auto' }}>
      <h2 style={{ fontSize: 28, marginBottom: 4 }}>Daily Brief</h2>
      {error && <p style={{ color: '#b00020' }}>{error}</p>}
      {brief && (
        <>
          <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
            {brief.date_ict} · Generated {localGenStr} (your time) · Items {brief.meta?.items_included ?? 0}/{brief.meta?.items_considered ?? 0} · Spend ${brief.meta?.model_cost_usd ?? 0}
          </div>
          {sectionsOrder.map(([title, ids]) => <SectionList key={title} title={title} ids={ids} cap={title==="Top Picks"?48:999} />)}
        </>
      )}
      {!brief && !error && <p>Loading… (the worker runs hourly; you can also force a run)</p>}
    </div>
  )
}
