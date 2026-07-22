#!/usr/bin/env python3
"""Build data/raw/funnel.explorer.html — a single self-contained, navigable browser
over everything fetch_portal_data.py pulled. Embeds real data, so the output is
gitignored (data/raw/ + *.explorer.html); this script is the committed artifact.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def load(name, default):
    p = RAW / name
    return json.loads(p.read_text()) if p.exists() else default


data = {
    "manifest": load("fetch_manifest.json", {}),
    "projects": load("projects.json", []),
    "positions": load("positions.json", []),
    "supply": load("supply_requests.json", []),
    "board": load("pipeline_board.json", {"columns": [], "total": 0}),
    "experts_index": load("experts_index.json", {"data": []}),
    "experts_full": load("experts_full.json", {}),
    "deals_full": load("deals_full.json", {}),
    "submissions": load("test_submissions.json", {}),
}

payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taste Labs — raw funnel data explorer</title>
<style>
:root{--bg:#fafaf8;--fg:#1a1a1a;--mut:#6b6b6b;--line:#e4e2dc;--card:#fff;--acc:#0f62fe;--red:#c0392b}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 -apple-system,'Segoe UI',sans-serif;background:var(--bg);color:var(--fg)}
header{padding:14px 20px;border-bottom:1px solid var(--line);background:var(--card);position:sticky;top:0;z-index:5}
header h1{margin:0;font-size:16px}header .sub{color:var(--mut);font-size:12px}
nav{display:flex;gap:4px;margin-top:10px;flex-wrap:wrap}
nav a{padding:5px 12px;border-radius:6px;text-decoration:none;color:var(--fg);border:1px solid transparent}
nav a.on{background:var(--fg);color:#fff}nav a:not(.on):hover{border-color:var(--line)}
main{padding:16px 20px;max-width:1400px;margin:0 auto}
input[type=search]{width:320px;max-width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:6px;font:inherit;margin:0 8px 12px 0}
select{padding:6px;border:1px solid var(--line);border-radius:6px;font:inherit;margin-bottom:12px}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);font-size:13px}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{cursor:pointer;user-select:none;position:sticky;top:96px;background:#f1efe9;white-space:nowrap}
tr:hover td{background:#f6f5f1}a.id{color:var(--acc);text-decoration:none}a.id:hover{text-decoration:underline}
.cols{display:flex;gap:10px;overflow-x:auto;align-items:flex-start;padding-bottom:10px}
.col{min-width:230px;background:var(--card);border:1px solid var(--line);border-radius:8px}
.col h3{margin:0;padding:8px 10px;border-bottom:1px solid var(--line);font-size:13px}
.col h3 .n{color:var(--mut);font-weight:400}
.card{padding:7px 10px;border-bottom:1px solid var(--line);font-size:12.5px}
.card .m{color:var(--mut)}
.kv{display:grid;grid-template-columns:220px 1fr;gap:2px 14px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin-bottom:14px;font-size:13px}
.kv b{color:var(--mut);font-weight:500;word-break:break-word}.kv span{word-break:break-word;white-space:pre-wrap}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;margin-bottom:10px}
details>summary{padding:9px 12px;cursor:pointer;font-weight:600}
details>div{padding:0 12px 12px}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;background:#eceae4;font-size:11.5px}
.pill.red{background:#fbe9e7;color:var(--red)}.pill.grn{background:#e8f5e9;color:#1b5e20}
.count{color:var(--mut);font-size:12px;margin-bottom:8px}
.back{display:inline-block;margin-bottom:12px;color:var(--acc);text-decoration:none}
h2{font-size:15px;margin:4px 0 10px}pre{white-space:pre-wrap;word-break:break-word;font-size:12px;background:#f6f5f1;padding:8px;border-radius:6px}
.warn{background:#fff8e1;border:1px solid #f0e6c0;border-radius:8px;padding:10px 12px;margin-bottom:14px;font-size:13px}
</style></head><body>
<header><h1>Taste Labs — raw funnel data explorer</h1>
<div class="sub" id="sub"></div>
<nav id="nav"></nav></header><main id="main"></main>
<script id="data" type="application/json">__PAYLOAD__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const asList=x=>Array.isArray(x)?x:(x&&x.data)||[];
const projects=asList(D.projects),positions=asList(D.positions),supply=asList(D.supply);
const experts=asList(D.experts_index);
const deals=Object.entries(D.deals_full||{}).map(([id,d])=>Object.assign({id},d||{}));
const boardDeals=(D.board.columns||[]).flatMap(c=>c.deals.map(d=>Object.assign({},d,{stage:c.stage})));
const dealById=Object.fromEntries(deals.map(d=>[d.id,d]));
const bd=Object.fromEntries(boardDeals.map(d=>[d.id,d]));
const pName=Object.fromEntries(projects.map(p=>[p.id,p.name+(p.client?' — '+p.client:'')]));
const eName=e=>((e.first_name||'')+' '+(e.last_name||'')).trim()||e.email||e.id;
const expById=Object.fromEntries(experts.map(e=>[e.id,e]));
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt=v=>v==null?'<span class="pill">null</span>':typeof v==='object'?'<pre>'+esc(JSON.stringify(v,null,1))+'</pre>':esc(v);
const kv=o=>'<div class="kv">'+Object.entries(o).map(([k,v])=>'<b>'+esc(k)+'</b><span>'+fmt(v)+'</span>').join('')+'</div>';
const sect=(t,inner,open)=>'<details'+(open?' open':'')+'><summary>'+esc(t)+'</summary><div>'+inner+'</div></details>';
const link=(h,t)=>'<a class="id" href="#'+h+'">'+esc(t)+'</a>';
function table(rows,cols,rowLink){
 if(!rows.length)return'<p class="count">No rows. (Empty state: nothing matching, or this dataset has not been fetched yet.)</p>';
 let sortK=null,asc=true;
 const render=rs=>'<table><thead><tr>'+cols.map(c=>'<th data-k="'+c.k+'">'+esc(c.t)+'</th>').join('')+'</tr></thead><tbody>'+
  rs.map(r=>'<tr>'+cols.map((c,i)=>'<td>'+(i===0&&rowLink?link(rowLink(r),(c.f?c.f(r):r[c.k])??'—'):(c.f?c.f(r):fmt(r[c.k]))) +'</td>').join('')+'</tr>').join('')+'</tbody></table>';
 setTimeout(()=>{document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{
  const k=th.dataset.k;asc=sortK===k?!asc:true;sortK=k;
  rows.sort((a,b)=>((a[k]??'')<(b[k]??'')?-1:1)*(asc?1:-1));
  document.getElementById('tblwrap').innerHTML=render(rows);})},0);
 return '<div id="tblwrap">'+render(rows)+'</div>';}
function searchBox(ph){return '<input type="search" id="q" placeholder="'+ph+'" oninput="route()">'}
const q=()=> (document.getElementById('q')?.value||'').toLowerCase();
let lastQ='';
const hit=(o,s)=>JSON.stringify(o).toLowerCase().includes(s);

const TABS={
 overview(){
  const m=D.manifest||{};
  const errs=m.errors?Object.entries(m.errors).filter(([,v])=>Object.keys(v).length):[];
  return '<h2>Fetch manifest</h2>'+kv({fetched_at_utc:m.fetched_at_utc,source:m.source,...(m.counts||{})})+
   (errs.length?'<div class="warn">Per-id fetch errors recorded: '+errs.map(([k,v])=>k+': '+Object.keys(v).length).join(', ')+' — see manifest below.</div>':'<p class="count">No per-id fetch errors.</p>')+
   sect('Raw manifest JSON','<pre>'+esc(JSON.stringify(m,null,1))+'</pre>');},
 pipeline(){
  const sel=document.getElementById('pf')?.value||'';
  const opts='<option value="">All projects</option>'+projects.map(p=>'<option value="'+p.id+'"'+(sel===p.id?' selected':'')+'>'+esc(pName[p.id])+'</option>').join('');
  const cols=(D.board.columns||[]).map(c=>{
   const ds=c.deals.filter(d=>(!sel||d.project_id===sel)&&(!q()||hit(d,q())));
   return '<div class="col"><h3>'+esc(c.stage)+' <span class="n">'+ds.length+'</span></h3>'+
    ds.slice(0,400).map(d=>'<div class="card">'+link('deal/'+d.id,d.expert_name||d.expert_id)+'<br><span class="m">'+esc(d.project_name||'')+(d.rate?' · $'+d.rate:'')+(d.invite_status?' · '+esc(d.invite_status):'')+'</span></div>').join('')+
    (ds.length>400?'<div class="card m">…'+(ds.length-400)+' more (narrow with search)</div>':'')+'</div>';}).join('');
  return searchBox('search deals…')+' <select id="pf" onchange="route()">'+opts+'</select>'+
   '<div class="count">'+D.board.total+' deals on board</div><div class="cols">'+cols+'</div>';},
 experts(){
  const rs=experts.filter(e=>!q()||hit(e,q()));
  return searchBox('search '+experts.length+' experts…')+'<div class="count">'+rs.length+' shown — click a name for the full profile (deals, ratings, comm log, messages)</div>'+
   table(rs,[{k:'first_name',t:'Name',f:eName},{k:'email',t:'Email'},{k:'community_stage',t:'Stage'},{k:'primary_specialization',t:'Specialization'},{k:'country',t:'Country'},{k:'source',t:'Source'},{k:'avg_rating',t:'Rating'},{k:'lifetime_hours',t:'Hours'},{k:'project_count',t:'Projects'},{k:'rate_min',t:'Rate min'},{k:'rate_max',t:'Rate max'}],r=>'expert/'+r.id);},
 deals(){
  const rs=deals.filter(d=>!q()||hit(d,q()));
  return searchBox('search '+deals.length+' deals…')+'<div class="count">'+rs.length+' shown — full deal records (test + compliance)</div>'+
   table(rs,[{k:'id',t:'Deal',f:r=>(expById[r.expert_id]?eName(expById[r.expert_id]):(bd[r.id]?.expert_name||r.id.slice(0,8)))},{k:'project_id',t:'Project',f:r=>esc(pName[r.project_id]||bd[r.id]?.project_name||'—')},{k:'stage',t:'Stage',f:r=>'<span class="pill">'+esc(r.stage??bd[r.id]?.stage??'—')+'</span>'},{k:'test_score',t:'Test score'},{k:'test_submitted_at',t:'Test submitted'},{k:'msa_status',t:'MSA'},{k:'sow_status',t:'SOW'},{k:'bg_check_status',t:'BG check'},{k:'payment_setup_status',t:'Payment'},{k:'cleared_to_work',t:'Cleared'},{k:'rate',t:'Rate'},{k:'updated_at',t:'Updated'}],r=>'deal/'+r.id);},
 projects(){
  return '<h2>Projects ('+projects.length+')</h2>'+table(projects,[{k:'name',t:'Name'},{k:'client',t:'Client'},{k:'status',t:'Status'},{k:'goal_volume',t:'Goal vol'},{k:'start_date',t:'Start'},{k:'end_date',t:'End'},{k:'created_at',t:'Created'}],r=>'project/'+r.id)+
   '<h2 style="margin-top:20px">Positions ('+positions.length+')</h2>'+table(positions,[{k:'title',t:'Title'},{k:'project_id',t:'Project',f:r=>esc(pName[r.project_id]||'—')},{k:'status',t:'Status'},{k:'headcount',t:'Headcount'},{k:'applicant_count',t:'Applicants'},{k:'primary_specialization',t:'Specialization'},{k:'rate_min',t:'Rate min'},{k:'rate_max',t:'Rate max'}],r=>'position/'+r.id);},
 supply(){
  return '<h2>Open supply requests ('+supply.length+')</h2>'+table(supply,[{k:'position_title',t:'Position'},{k:'project_name',t:'Project'},{k:'headcount_needed',t:'Needed'},{k:'headcount_available_in_community',t:'Available'},{k:'status',t:'Status'},{k:'created_at',t:'Created'}]);}
};

function detail(kind,id){
 let h='<a class="back" href="#'+({expert:'experts',deal:'deals',project:'projects',position:'projects'}[kind])+'">&larr; back</a>';
 if(kind==='expert'){
  const f=D.experts_full[id],ix=expById[id];
  if(!f&&!ix)return h+'<p>Unknown expert id.</p>';
  const e=(f&&f.expert)||ix;
  h+='<h2>'+esc(eName(e))+' <span class="pill">'+esc(f?.availability_status||'')+'</span></h2>';
  h+=sect('Profile',kv(e),true);
  if(f){h+=sect('Rollups & performance',kv(Object.assign({},f.rollups,{last_contact_at:f.last_contact_at}))+(f.performance?kv(f.performance):''));
   h+=sect('Deals ('+(f.deals||[]).length+')',(f.deals||[]).map(d=>kv(Object.assign({open_full_record:d.id&&dealById[d.id]?link('deal/'+d.id,'deal '+d.id.slice(0,8)+'…'):'—'},d))).join('')||'<p class="count">none</p>');
   h+=sect('Ratings',fmt(f.ratings));h+=sect('Comm log',fmt(f.comm_log));h+=sect('Messages',fmt(f.messages));}
  else h+='<div class="warn">No full profile fetched for this id (see manifest errors).</div>';
 }else if(kind==='deal'){
  const d=dealById[id],b=bd[id],sub=(D.submissions||{})[id];
  if(!d&&!b)return h+'<p>Unknown deal id.</p>';
  const ex=d&&expById[d.expert_id];
  h+='<h2>Deal — '+esc(ex?eName(ex):(b?.expert_name||id))+' × '+esc(pName[(d||b).project_id]||b?.project_name||'?')+'</h2>';
  if(ex)h+='<p>'+link('expert/'+ex.id,'→ expert profile')+'</p>';
  h+=sect('Full deal record (get_deal)',d?kv(d):'<p class="count">not fetched</p>',true);
  h+=sect('Board row',b?kv(b):'<p class="count">not on board</p>');
  h+=sect('Test submission',sub?fmt(sub):'<p class="count">none fetched (no test_status on this deal)</p>');
 }else{
  const src=kind==='project'?projects:positions;const o=src.find(x=>x.id===id);
  h+=o?('<h2>'+esc(o.name||o.title)+'</h2>'+kv(o)):'<p>Not found.</p>';
  if(kind==='project'&&o)h+=sect('Positions in this project',fmt(positions.filter(p=>p.project_id===id)))+
   sect('Deals in this project ('+boardDeals.filter(d=>d.project_id===id).length+')',boardDeals.filter(d=>d.project_id===id).map(d=>'<div class="card">'+link('deal/'+d.id,(d.expert_name||d.id))+' <span class="pill">'+esc(d.stage)+'</span></div>').join(''));
 }
 return h;}

const NAMES={overview:'Overview',pipeline:'Pipeline board',experts:'Experts',deals:'Deals',projects:'Projects & positions',supply:'Supply requests'};
function route(){
 const hash=location.hash.slice(1)||'overview';
 const[first,id]=hash.split('/');
 const tab=id?null:first;
 document.getElementById('nav').innerHTML=Object.entries(NAMES).map(([k,v])=>'<a href="#'+k+'" class="'+(k===first?'on':'')+'">'+v+'</a>').join('');
 const focus=document.activeElement&&document.activeElement.id==='q';
 const qv=q();
 document.getElementById('main').innerHTML=id?detail(first,id):(TABS[tab]||TABS.overview)();
 const box=document.getElementById('q');
 if(box){box.value=qv;if(focus){box.focus();box.setSelectionRange(qv.length,qv.length);}}
 window.scrollTo(0,0);
 document.getElementById('sub').textContent='fetched '+(D.manifest.fetched_at_utc||'?')+' · '+experts.length+' experts · '+D.board.total+' deals · '+projects.length+' projects · PRIVATE: contains real personal data — do not share or commit';
}
addEventListener('hashchange',route);route();
</script></body></html>"""

out = RAW / "funnel.explorer.html"
out.write_text(TEMPLATE.replace("__PAYLOAD__", payload))
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
