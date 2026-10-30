// ---------------------------------------------------------------------------
// Localities tab: search, per-locality comparison and largest shifts.
// ---------------------------------------------------------------------------
const settlementState = { code: null, metric: 'netanyahu' };
const LOCALITIES = DATA.settlements.filter(s => s.code !== 9999);
const normalise = s => s.toLowerCase().replace(/["'״׳\-–\s]/g, '');

function openSettlement(code) {
  settlementState.code = code;
  location.hash = 'settlements';
  showTab('settlements');
  renderSettlement();
  $('settlement-detail').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderSearchResults() {
  const q = normalise($('settlement-search').value);
  const list = $('settlement-results');
  if (!q) { list.innerHTML = ''; list.hidden = true; return; }
  const hits = LOCALITIES.filter(s => normalise(s.name).includes(q))
    .sort((a, b) => normalise(a.name).indexOf(q) - normalise(b.name).indexOf(q) || (b.years[LATEST]?.[2] ?? 0) - (a.years[LATEST]?.[2] ?? 0))
    .slice(0, 12);
  list.hidden = false;
  list.innerHTML = hits.length
    ? hits.map(s => `<li><button type="button" data-code="${s.code}">${esc(s.name)}<small>${s.cluster ? T.cluster(s.cluster) : T.settlements.noCluster}</small></button></li>`).join('')
    : `<li class="empty">${T.settlements.none}</li>`;
  list.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
    $('settlement-search').value = '';
    list.hidden = true;
    openSettlement(+b.dataset.code);
  }));
}

function bars(rows, max) {
  return rows.map(r => `<div class="hbar"><span class="hbar-name"><i class="swatch" style="background:${r.color}"></i>${esc(r.label)}</span>` +
    `<span class="hbar-track"><i style="width:${(r.value / max) * 100}%;background:${r.color}"></i></span><b>${pct(r.value)}</b></div>`).join('');
}

function renderSettlement() {
  const s = LOCALITIES.find(x => x.code === settlementState.code);
  const box = $('settlement-detail');
  if (!s) { box.hidden = true; return; }
  box.hidden = false;
  const yearCard = year => {
    const row = s.years[year];
    if (!row) return `<div class="year-card"><h4>${year}</h4><p class="muted">${T.settlements.missingYear(year)}</p></div>`;
    const [eligible, voters, valid, ...votes] = row;
    const parties = YEAR[year].parties;
    const listRows = votes.map((v, i) => ({ label: name(parties[i]), color: parties[i].color, value: v / valid }))
      .filter(r => r.value >= 0.005).sort((a, b) => b.value - a.value);
    return `<div class="year-card"><h4>${year}</h4><p class="meta"><b>${fmt(valid)}</b> ${T.validVotes} · ${T.turnout} <b>${pct(voters / eligible)}</b></p>` +
      bars(listRows, Math.max(...listRows.map(r => r.value))) + '</div>';
  };
  const blocRows = BLOCS.map(b => ({
    label: name(b), color: b.color,
    a: s.years[Y0] ? metricValue(Y0, b.id, s.years[Y0]) : null,
    b: s.years[Y1] ? metricValue(Y1, b.id, s.years[Y1]) : null,
  }));
  const blocTable = `<table class="bloc-compare"><thead><tr><th></th><th>${Y0}</th><th>${Y1}</th><th>${T.trends.change}</th></tr></thead><tbody>` +
    blocRows.map(r => `<tr><th><i class="swatch" style="background:${r.color}"></i>${esc(r.label)}</th>` +
      `<td>${r.a === null ? '—' : pct(r.a)}</td><td>${r.b === null ? '—' : pct(r.b)}</td>` +
      `<td>${r.a === null || r.b === null ? '' : `<span class="delta ${r.b > r.a ? 'up' : 'down'}">${pts(r.b - r.a)}</span>`}</td></tr>`).join('') +
    '</tbody></table>';
  box.innerHTML = `<header><h3>${esc(s.name)}</h3><span class="tag">${s.cluster ? T.cluster(s.cluster) : T.settlements.noCluster}</span></header>` +
    `<h4 class="sub">${T.settlements.blocs}</h4>${blocTable}<h4 class="sub">${T.settlements.lists}</h4>` +
    `<div class="year-cards">${yearCard(Y0)}${yearCard(Y1)}</div><p class="note">${T.settlements.turnoutNote}</p>`;
}

function renderSwings() {
  const m = settlementState.metric;
  const rows = LOCALITIES.filter(s => s.years[Y0] && s.years[Y1] && s.years[Y0][2] >= 1000 && s.years[Y1][2] >= 1000)
    .map(s => ({ s, d: metricValue(Y1, m, s.years[Y1]) - metricValue(Y0, m, s.years[Y0]) }))
    .sort((a, b) => b.d - a.d);
  const list = items => items.map(({ s, d }) =>
    `<li><button type="button" data-code="${s.code}"><span>${esc(s.name)}</span><small>${s.cluster ? T.clusterShort(s.cluster) : '—'}</small>` +
    `<span class="delta ${d > 0 ? 'up' : 'down'}">${pts(d)}</span></button></li>`).join('');
  $('swings').innerHTML = `<div><h4>${T.settlements.gains}</h4><ol>${list(rows.slice(0, 10))}</ol></div>` +
    `<div><h4>${T.settlements.losses}</h4><ol>${list(rows.slice(-10).reverse())}</ol></div>`;
  $('swings').querySelectorAll('button').forEach(b => b.addEventListener('click', () => openSettlement(+b.dataset.code)));
}

function initSettlements() {
  $('settlement-search').placeholder = T.settlements.search;
  $('settlement-search').addEventListener('input', renderSearchResults);
  $('settlement-search').addEventListener('keydown', e => {
    if (e.key === 'Enter') $('settlement-results').querySelector('button')?.click();
  });
  segmented($('swing-metric'), METRICS.map(m => ({ value: m.id, label: m.label() })), settlementState.metric,
    v => { settlementState.metric = v; renderSwings(); });
  // Start with the largest locality so the panel is never empty.
  settlementState.code = LOCALITIES.slice().sort((a, b) => (b.years[LATEST]?.[2] ?? 0) - (a.years[LATEST]?.[2] ?? 0))[0].code;
  renderSettlement();
  renderSwings();
}
