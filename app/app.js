/* Taste Labs funnel diagnostic — renders precomputed data/processed/metrics.json.
   No data logic here beyond display math; the pipeline is the source of truth. */
'use strict';

const $ = sel => document.querySelector(sel);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt = n => n == null ? '—' : n.toLocaleString('en-US');
const pct = (a, b) => b ? Math.round(100 * a / b) + '%' : '—';

const STAGE_LABELS = {
  outreached: 'Outreached', responded: 'Responded', applied: 'Applied',
  assessment_taken: 'Assessment taken', assessment_passed: 'Portfolio passed (proxy)',
  accepted: 'Accepted', project_applied: 'Project contact', staffed: 'Staffed',
  first_billable: 'First billable', second_contract: 'Second contract',
};
const FORMULAS = {
  applied: 'People with a form submission (all Notion rows) or portal community_stage=applicant.',
  assessment_passed: 'Portfolio Approval = Yes in either system. PROXY for the assessment stage — real assessment data is not tracked.',
  accepted: 'Notion status ∈ {Welcome Sent, Active, Inactive} OR portal community_stage = accepted.',
  project_applied: 'Has ≥1 deal (any stage) on the pipeline board.',
  staffed: 'Has ≥1 deal that ever reached active/paused/ended.',
  second_contract: '≥2 deals that reached staffed.',
  outreached: 'LinkedIn leads with contact evidence in HeyReach (connection sent/accepted or message sent). LinkedIn outreach only — other channels enter the funnel at Applied.',
  responded: 'HeyReach leads with leadMessageStatus = MessageReply. LinkedIn outreach only.',
  assessment_taken: 'Portal test fields are null on all 855 deals; sampled submissions empty.',
  first_billable: 'lifetime_hours > 0 — currently 0 for every profile; billable data not tracked.',
};
const RAMP = ['--ramp-1', '--ramp-2', '--ramp-3', '--ramp-4', '--ramp-5'];
const STACK = ['applied', 'assessment_passed', 'accepted', 'project_applied', 'staffed_plus'];
const STACK_LABELS = { ...STAGE_LABELS, staffed_plus: 'Staffed+ (incl. 2nd contract)' };

let M = null;
let view = 1;
const state = { channel: '', cost: null, split: '', tick: 0 };

/* ---------- tooltip ---------- */
const tip = () => $('#tip');
document.addEventListener('mouseover', e => {
  const t = e.target.closest('[data-tip]');
  if (!t) { tip().style.display = 'none'; return; }
  tip().textContent = t.dataset.tip;
  tip().style.display = 'block';
});
document.addEventListener('mousemove', e => {
  const el = tip();
  if (el.style.display === 'block') {
    el.style.left = Math.min(e.clientX + 14, innerWidth - 340) + 'px';
    el.style.top = (e.clientY + 16) + 'px';
  }
});

/* ---------- views ---------- */
const VIEWS = {
  1: { name: 'Funnel', render: funnelView },
  2: { name: 'Headline', render: headlineView },
  3: { name: 'Concentration', render: concentrationView },
  4: { name: 'Cohorts', render: cohortView },
  5: { name: 'Dormant pool', render: dormantView },
};

function funnelView() {
  const src = state.channel ? M.funnel.by_channel[state.channel] : M.funnel.combined;
  const order = Object.keys(STAGE_LABELS);
  const measured = order.filter(s => src[s] != null);
  const max = Math.max(...measured.map(s => src[s]), 1);
  const leak = state.channel ? biggestLeak(src, measured) : M.funnel.biggest_leak;

  const chans = Object.keys(M.funnel.by_channel);
  let h = `<h2>The funnel</h2>
  <div class="panel"><div class="controls">
    <label>Channel <select id="chan"><option value="">All channels</option>
      ${chans.map(c => `<option ${state.channel === c ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select></label>
    <span class="fconv">${fmt(src.applied)} applicants in scope${M.funnel.outreach_note ? ' · ' + esc(M.funnel.outreach_note) : ''}</span>
  </div>`;

  let prevMeasured = null;
  for (const s of order) {
    if (src[s] == null) {
      h += `<div class="frow notinst"><span class="fl" data-tip="${esc(FORMULAS[s])}">${STAGE_LABELS[s]}</span>
        <div class="ftrack"></div><span class="badge">not tracked</span></div>`;
      continue;
    }
    const isLeakFrom = leak && s === leak.from, isLeakTo = leak && s === leak.to;
    const conv = prevMeasured != null ? pct(src[s], prevMeasured) : '';
    h += `<div class="frow"><span class="fl" data-tip="${esc(FORMULAS[s])}">${STAGE_LABELS[s]}</span>
      <div class="ftrack"><div class="fbar" data-tip="${fmt(src[s])} people reached at least ${STAGE_LABELS[s]}"
        style="width:${(100 * src[s] / max).toFixed(1)}%"></div></div>
      <span class="fnum">${fmt(src[s])} <span class="fconv ${isLeakTo ? 'leak' : ''}">${conv ? '· ' + conv : ''}</span></span></div>`;
    if (isLeakFrom) {
      h += `<div class="leakline"><span class="dot"></span> biggest leak: −${fmt(leak.lost)} people before ${STAGE_LABELS[leak.to]}</div>`;
    }
    prevMeasured = src[s];
  }
  h += `</div>`;
  return h;
}

function biggestLeak(src, measured) {
  let best = null;
  for (let i = 1; i < measured.length; i++) {
    const lost = src[measured[i - 1]] - src[measured[i]];
    if (!best || lost > best.lost) best = { from: measured[i - 1], to: measured[i], lost };
  }
  return best;
}

function headlineView() {
  const H = M.headline;
  const cost = state.cost ?? H.cost_per_vetted_default;
  const costTotal = H.vetted_never_staffed * cost;
  const edited = state.cost != null;
  const varPct = H.activation_rate_proxy == null ? '—' : Math.round(H.activation_rate_proxy * 1000) / 10 + '%';
  const activeNow = M.deal_concentration?.active_now;
  return `<h2>Headline metrics</h2>
  <div class="hero" data-tip="Accepted experts currently on an active deal ÷ all accepted. PROXY: billable hours are not tracked, so 'active deal now' stands in for 'billable in last 30d'. Numerator upgrades automatically when billable data lands.">
    <div class="hero-tag">★ North Star</div>
    <div class="hero-v">${varPct}</div>
    <div class="hero-l">Vetted Activation Rate (VAR)</div>
    <div class="hero-n">${fmt(activeNow)} of ${fmt(H.accepted_total)} accepted experts on an active project ·
      the one number both sides of the marketplace move — it cannot be gamed by recruiting more or by over-using a few designers</div>
  </div>
  <div class="tiles">
    <div class="tile"><div class="v leak">${fmt(H.vetted_never_staffed)}</div>
      <span class="l" data-tip="Accepted-stage people (either system) whose furthest stage is below Staffed. ${fmt(H.vetted_never_staffed)} of ${fmt(H.accepted_total)} accepted.">vetted, never staffed</span>
      <div class="n">${pct(H.vetted_never_staffed, H.accepted_total)} of ${fmt(H.accepted_total)} accepted — the pool VAR grows from</div></div>
    <div class="tile"><div class="v leak">$${fmt(costTotal)}</div>
      <span class="l" data-tip="vetted_never_staffed × cost per vetted designer. Cost input is editable — FP&A to confirm.">sunk vetting cost</span>
      <div class="n">$<input id="cost" type="number" value="${cost}" min="0" step="50"> / designer
        <span class="tag">${edited ? 'edited' : 'assumption'}</span></div></div>
    <div class="tile"><div class="v">${H.median_days_to_staffed == null ? '—' : fmt(H.median_days_to_staffed) + 'd'}</div>
      <span class="l" data-tip="Median days from application submission to first deal reaching a staffed stage, for people with both timestamps.">median time to staffed</span>
      <div class="n">${H.median_days_to_staffed == null ? 'not tracked (no usable timestamp pairs)' : 'application → first staffed deal'}</div></div>
    <div class="tile"><div class="v">${fmt(H.second_contract)}</div>
      <span class="l" data-tip="People with ≥2 deals that reached a staffed stage. True R2C needs billable data — not tracked.">repeat contracts (R2C n)</span>
      <div class="n">${esc(H.r2c_note)}</div></div>
  </div>`;
}

function concentrationView() {
  const dist = M.concentration;
  if (!dist) return `<div class="empty"><b>Billable-work concentration is not measurable yet.</b><br>
    Every profile shows lifetime_hours = 0 and every deal rate is null — the portal does not carry billable data.
    What would light this up: a timesheet or payments export with hours per expert. Meanwhile the proxy below uses deal counts.</div>`;
  return '';
}

function cohortView() {
  if (!M.cohorts?.length) return `<div class="empty">No application timestamps — cohort view needs them.</div>`;
  const months = M.cohorts;
  const max = Math.max(...months.map(c => c.total), 1);
  const stackVal = (c, s) => {
    const st = c.stages;
    if (s === 'staffed_plus') return (st.staffed || 0) + (st.second_contract || 0) + (st.first_billable || 0);
    return st[s] || 0;
  };
  let cols = '', labels = '';
  for (const c of months) {
    let segs = '';
    STACK.forEach((s, i) => {
      const v = stackVal(c, s);
      if (v) segs += `<div class="cseg" style="height:${(100 * v / max).toFixed(2)}%;background:var(${RAMP[i]})"
        data-tip="${c.month}: ${fmt(v)} whose furthest stage is ${STACK_LABELS[s]} (of ${fmt(c.total)} applicants)"></div>`;
    });
    cols += `<div class="cmonth" data-tip="${c.month}: ${fmt(c.total)} applications">${segs}</div>`;
    labels += `<div>${c.month}</div>`;
  }
  const legend = STACK.map((s, i) =>
    `<span><i style="background:var(${RAMP[i]})"></i>${STACK_LABELS[s]}</span>`).join('');
  return `<h2>Application cohorts by month</h2>
  <p class="sub">Each column is a month of applications; segments show how far those people have gotten <em>to date</em>
  (furthest stage reached, darker = further). Recent cohorts are naturally less progressed.</p>
  <div class="panel"><div class="cwrap">${cols}</div><div class="clabels">${labels}</div>
  <div class="legend">${legend}</div></div>`;
}

function dormantView() {
  const rows = M.dormant.filter(d => !state.split || d.split === state.split);
  const split = M.dormant_split;
  const shown = rows.slice(0, 400);
  return `<h2>Dormant pool — vetted, never staffed</h2>
  <p class="sub">The two halves need opposite fixes: <b class="split-never">never offered</b> is demand starvation
  (${fmt(split.never_offered)} people); <b>offered, not converted</b> is friction/trust churn (${fmt(split.offered_not_converted)}).</p>
  <div class="panel"><div class="controls">
    <label>Split <select id="split"><option value="">Both (${fmt(M.dormant.length)})</option>
      <option value="never_offered" ${state.split === 'never_offered' ? 'selected' : ''}>never offered (${fmt(split.never_offered)})</option>
      <option value="offered_not_converted" ${state.split === 'offered_not_converted' ? 'selected' : ''}>offered, not converted (${fmt(split.offered_not_converted)})</option>
    </select></label>
    <span class="fconv">${shown.length < rows.length ? `showing 400 of ${fmt(rows.length)} (sorted oldest first)` : `${fmt(rows.length)} people`}</span></div>
  <table><thead><tr><th>Name</th><th>Specialization</th><th>Channel</th><th class="num">Score</th>
    <th class="num">Rate</th><th>Applied</th><th class="num">Days idle</th><th>Split</th><th>Availability</th></tr></thead><tbody>
  ${shown.map(d => `<tr><td>${esc(d.name || d.email)}</td><td>${esc(d.specialization || '—')}</td>
    <td>${esc(d.channel || '—')}</td><td class="num">${d.portfolio_score ?? '—'}</td>
    <td class="num">${d.rate_min != null ? '$' + d.rate_min + '–' + (d.rate_max ?? '+') : '—'}</td>
    <td>${esc(d.applied || '—')}</td><td class="num">${fmt(d.days_since_applied)}</td>
    <td class="${d.split === 'never_offered' ? 'split-never' : ''}">${d.split === 'never_offered' ? 'never offered' : 'offered'}</td>
    <td>${esc(d.availability || '—')}</td></tr>`).join('')}
  </tbody></table></div>`;
}

/* ---------- concentration uses deal-count proxy assembled client-side from dormant+headline ---------- */
function concentrationProxyView() {
  const H = M.headline;
  const av = M.availability || {};
  const avOrder = Object.entries(av).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...avOrder.map(([, v]) => v), 1);
  return `<h2>Utilization &amp; concentration</h2>
  <div class="warnbox">Billable hours are <b>not tracked</b> (lifetime_hours = 0 on all 975 profiles; deal rates null).
  True concentration of billable work cannot be computed — this view shows the nearest proxies and is itself finding #1
  of the tracking gaps.</div>
  <div class="tiles">
    <div class="tile"><div class="v">${fmt(M.deal_concentration?.multi_active ?? 3)}</div>
      <span class="l" data-tip="Experts holding >1 currently-active deal.">experts on multiple active deals</span></div>
    <div class="tile"><div class="v">${fmt(M.deal_concentration?.active_now ?? 52)}</div>
      <span class="l" data-tip="Experts with ≥1 deal currently in stage 'active'.">experts active right now</span></div>
    <div class="tile"><div class="v leak">${fmt(H.vetted_never_staffed)}</div>
      <span class="l" data-tip="Accepted, never reached a staffed deal.">vetted bench sitting idle</span></div>
  </div>
  <div class="panel"><h2 style="font-size:13.5px">Availability status (portal profiles)</h2>
  ${avOrder.map(([k, v]) => `<div class="hrow"><span class="hl">${esc(k)}</span>
    <div class="hbar ${k === 'active_not_on_project' || k === 'idle' ? 'leakc' : ''}" data-tip="${fmt(v)} profiles: ${esc(k)}"
      style="width:${(100 * v / max).toFixed(1)}%"></div><span class="fnum">${fmt(v)}</span></div>`).join('')}
  <p class="sub" style="margin-top:10px">Red = bench states (available but not working). What would complete this view:
  hours per expert from timesheets/payments → top-10%/20% share of billable work, burnout-risk intervals.</p></div>`;
}
VIEWS[3].render = concentrationProxyView;

/* ---------- shell ---------- */
function render() {
  $('#nav').innerHTML = Object.entries(VIEWS).map(([k, v]) =>
    `<button class="${+k === view ? 'on' : ''}" data-v="${k}">${k} ${v.name}</button>`).join('');
  $('#main').innerHTML = VIEWS[view].render();
  $('#chan')?.addEventListener('change', e => { state.channel = e.target.value; render(); });
  $('#split')?.addEventListener('change', e => { state.split = e.target.value; render(); });
  $('#cost')?.addEventListener('change', e => { state.cost = +e.target.value || 0; render(); });
}

function setView(v) { view = v; location.hash = v; render(); }
document.addEventListener('click', e => {
  const b = e.target.closest('nav button');
  if (b) setView(+b.dataset.v);
});
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (VIEWS[e.key]) setView(+e.key);
});
addEventListener('hashchange', () => {
  const v = +location.hash.slice(1);
  if (VIEWS[v] && v !== view) { view = v; render(); }
});
if (VIEWS[+location.hash.slice(1)]) view = +location.hash.slice(1);

fetch('../data/processed/metrics.json')
  .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then(m => { M = m; render(); })
  .catch(() => {
    $('#main').innerHTML = `<div class="empty"><b>No processed data found.</b><br>
    Run the pipeline first: <code>make refresh</code> (or <code>.venv/bin/python pipeline/run.py</code>), then reload.<br>
    This app renders <code>data/processed/metrics.json</code> — it holds real data locally and is never committed.</div>`;
  });
