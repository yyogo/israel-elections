// ---------------------------------------------------------------------------
// Clusters tab: proportional-width stacked columns (Marimekko) per cluster,
// plus a side panel for the selected group and a bloc/list legend.
// ---------------------------------------------------------------------------
const clusterState = {
  year: LATEST,
  merge: false,
  selectedGroup: '7',
  hoverGroup: null,
  locked: null, // {kind: 'party'|'bloc', index}
  hover: null,
  groups: [],
  panelKey: null,
  coords: [],
  geometry: null,
};
let donut = null;

const cs = clusterState;
const parties = () => YEAR[cs.year].parties;
const selection = () => cs.hover || cs.locked;
const sameSel = (a, b) => a && b && a.kind === b.kind && a.index === b.index;

function selectedIds(sel = selection()) {
  if (!sel) return parties().map((_, i) => i);
  return sel.kind === 'party' ? [sel.index] : YEAR[cs.year].blocMembers[sel.index];
}
const countIn = (g, sel = selection()) => sum(selectedIds(sel).map(i => g.votes[i]));
const selectionName = (sel = selection()) =>
  !sel ? T.clusters.allLists : sel.kind === 'party' ? name(parties()[sel.index]) : name(BLOCS[sel.index]);
const currentGroup = () =>
  cs.groups.find(g => g.id === (cs.hoverGroup ?? cs.selectedGroup)) || cs.groups[0];

function buildGroups() {
  const y = YEAR[cs.year];
  const byId = id => y.groups.find(g => g.id === id);
  const numbered = y.groups.filter(g => /^\d+$/.test(g.id));
  let lead;
  if (cs.merge) {
    const e = byId('external'), u = byId('unassigned');
    lead = [{ id: 'other', eligible: e.eligible + u.eligible, voters: e.voters + u.voters, valid: e.valid + u.valid,
              votes: e.votes.map((v, i) => v + u.votes[i]) }];
  } else {
    lead = [byId('external'), byId('unassigned')];
  }
  cs.groups = [...lead, ...numbered, y.national];
  if (!cs.groups.some(g => g.id === cs.selectedGroup)) cs.selectedGroup = cs.groups[0].id;
}

function chooseGroup(id) {
  cs.selectedGroup = id;
  cs.hoverGroup = null;
  cs.hover = null;
  updateClusters();
}

function choose(sel) {
  cs.locked = sameSel(cs.locked, sel) ? null : sel;
  cs.hover = null;
  updateClusters();
}

function setHover(sel, event) {
  if (event?.pointerType === 'touch') return;
  cs.hover = sel;
  updateClusters();
}

// --- Main chart ------------------------------------------------------------

function renderClusterChart() {
  const svg = $('cluster-chart');
  const W = svg.parentElement.clientWidth;
  if (!W) return;
  const mobile = W < 620;
  const axisM = mobile ? 92 : 44, farM = mobile ? 10 : 14;
  // Start edge is where reading begins: right in Hebrew, left in English.
  const L = RTL ? farM : axisM, R = RTL ? axisM : farM;
  const T0 = 28, B = mobile ? 26 : 66;
  const pw = W - L - R;
  const GAP = 12;
  const national = cs.groups.at(-1);
  const data = cs.groups.slice(0, -1);
  const gapBefore = g => (g.id === '1' || g.id === '10' || g.id === 'national') ? GAP : 0;
  const gaps = sum(cs.groups.map(gapBefore));
  const total = national.valid;

  // Extent of each group along the "size" axis (width on desktop, thickness on phones).
  const natSize = mobile ? 26 : Math.max(38, pw * 0.07);
  const weighted = mobile ? 300 : pw - gaps - natSize;
  const H = mobile ? T0 + weighted + gaps + natSize + B : 410;
  const ph = H - T0 - B;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.style.height = H + 'px';
  $('cluster-encoding').innerHTML = mobile ? T.clusters.encodingMobile : T.clusters.encodingDesktop;

  // Position along the start->end direction, mapped to x for desktop / y for phones.
  const startX = (offset, size) => (RTL ? W - R - offset - size : L + offset);
  let out = '', offset = 0;
  cs.coords = [];
  cs.groups.forEach((g, gi) => {
    offset += gapBefore(g);
    const size = g.id === 'national' ? natSize : weighted * g.valid / total;
    const box = mobile
      ? { x: L, y: T0 + offset, w: pw, h: size }
      : { x: startX(offset, size), y: T0, w: size, h: ph };
    cs.coords.push({ ...box, g, gi });
    let acc = 0;
    g.votes.forEach((v, pi) => {
      const share = g.valid ? v / g.valid : 0;
      if (!share) return;
      let rect;
      if (mobile) {
        const len = share * box.w;
        rect = { x: RTL ? box.x + box.w - acc - len : box.x + acc, y: box.y, w: len, h: box.h };
        acc += len;
      } else {
        const len = share * box.h;
        rect = { x: box.x, y: box.y + box.h - acc - len, w: box.w, h: len };
        acc += len;
      }
      out += `<rect class="segment" data-p="${pi}" data-g="${gi}" x="${rect.x}" y="${rect.y}" width="${rect.w}" height="${rect.h}" fill="${parties()[pi].color}"/>`;
    });
    if (!mobile) out += `<line x1="${box.x}" y1="${box.y}" x2="${box.x}" y2="${box.y + box.h}" class="column-edge"/>`;
    offset += size;
  });

  out += mobile ? mobileAxes({ W, H, L, R, T0, pw }) : desktopAxes({ W, L, R, T0, ph });
  cs.geometry = { W, H, L, R, T0, B, pw, ph, mobile };
  svg.innerHTML = out + '<g id="cluster-values" pointer-events="none"></g><g id="cluster-outline"></g><g id="national-reference" pointer-events="none"></g>';

  svg.querySelectorAll('.segment').forEach(el => {
    el.addEventListener('pointerenter', e => {
      if (e.pointerType === 'touch') return;
      cs.hover = { kind: 'party', index: +el.dataset.p };
      cs.hoverGroup = cs.groups[+el.dataset.g].id;
      updateClusters();
    });
    el.addEventListener('click', () => {
      cs.selectedGroup = cs.groups[+el.dataset.g].id;
      cs.hoverGroup = null;
      choose({ kind: 'party', index: +el.dataset.p });
    });
  });
  svg.querySelectorAll('[data-axis-group]').forEach(el => {
    const go = () => chooseGroup(cs.groups[+el.dataset.axisGroup].id);
    el.addEventListener('click', go);
    el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
  });
  applyClusterHighlight();
}

function axisLabel(gi, x, y, grow, hitW) {
  const g = cs.groups[gi];
  return `<g class="cluster-focus" data-axis-group="${gi}" role="button" tabindex="0" aria-label="${esc(groupName(g.id))}">` +
    `<rect class="cluster-hit" x="${grow === 'middle' ? x - hitW / 2 : grow === 'left' ? x - hitW : x}" y="${y - 14}" width="${hitW}" height="20"/>` +
    `<text class="bar-label${g.id === 'national' ? ' national' : ''}" x="${x}" y="${y}" text-anchor="${anchor(grow)}">${esc(groupName(g.id, true))}</text></g>`;
}

function desktopAxes({ W, L, R, T0, ph }) {
  let out = '';
  const base = T0 + ph;
  // Cluster numbers sit under their column; narrow neighbours are nudged apart.
  const minGap = 18;
  const sorted = cs.coords.slice().sort((a, b) => (RTL ? b.x - a.x : a.x - b.x));
  let last = null;
  let stagger = 0;
  sorted.forEach(c => {
    const cx = c.x + c.w / 2;
    const numeric = /^\d+$/.test(c.g.id);
    let lx = cx, ly = base + 19;
    if (numeric || c.g.id === 'national') {
      if (last !== null) lx = RTL ? Math.min(cx, last - minGap) : Math.max(cx, last + minGap);
      last = lx;
    } else {
      // Unranked groups: staggered labels so wide words never collide.
      ly = base + 38 + 18 * stagger++;
      lx = RTL ? Math.min(W - R - 34, cx + 0) : Math.max(L + 34, cx);
    }
    if (Math.abs(lx - cx) > 1 || !numeric && c.g.id !== 'national') {
      out += `<path d="M${cx},${base}L${cx},${ly - 14}L${lx},${ly - 10}" class="leader"/>`;
    }
    const wide = !numeric;
    out += axisLabel(c.gi, lx, ly, 'middle', wide ? 76 : 20);
  });
  // Value axis on the start side.
  const ax = RTL ? W - R + 8 : L - 8;
  for (let t = 0; t <= 100; t += 20) {
    const y = T0 + ph * (1 - t / 100);
    out += `<line class="gridline" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/>` +
      `<text class="axis" x="${ax}" y="${y + 4}" text-anchor="${RTL ? 'start' : 'end'}" direction="ltr">${t}%</text>`;
  }
  return out;
}

function mobileAxes({ W, H, L, R, T0, pw }) {
  let out = '';
  // Row labels on the start side, pushed apart when rows are thin.
  const labelX = RTL ? W - R + 14 : L - 14;
  const items = cs.coords.map(c => ({ c, cy: c.y + c.h / 2, ly: c.y + c.h / 2 }));
  items.forEach((d, i) => { d.ly = Math.max(d.cy, i ? items[i - 1].ly + 21 : T0 + 9); });
  const maxY = H - 34;
  if (items.at(-1).ly > maxY) {
    items.at(-1).ly = maxY;
    for (let i = items.length - 2; i >= 0; i--) items[i].ly = Math.min(items[i].ly, items[i + 1].ly - 21);
  }
  const edge = RTL ? W - R : L, dir = RTL ? 1 : -1;
  items.forEach(({ c, cy, ly }) => {
    if (Math.abs(cy - ly) > 2) out += `<path d="M${edge},${cy} L${edge + dir * 6},${cy} L${edge + dir * 12},${ly}" class="leader"/>`;
    out += axisLabel(c.gi, RTL ? W - 8 : 8, ly + 4, RTL ? 'left' : 'right', (RTL ? R : L) - 14);
  });
  for (let t = 0; t <= 100; t += 25) {
    const x = RTL ? W - R - pw * t / 100 : L + pw * t / 100;
    const anchor = t === 0 ? (RTL ? 'end' : 'start') : t === 100 ? (RTL ? 'start' : 'end') : 'middle';
    out += `<text class="axis" x="${x}" y="15" text-anchor="${anchor}" direction="ltr">${t}%</text>`;
  }
  return out;
}

function applyClusterHighlight() {
  const sel = selection(), active = selectedIds(), g = currentGroup();
  document.querySelectorAll('#cluster-chart .segment, #group-ranking [data-rank]').forEach(el => {
    const i = +(el.dataset.p ?? el.dataset.rank);
    el.classList.toggle('dim', !!sel && !active.includes(i));
  });
  document.querySelectorAll('#cluster-legend [data-party]').forEach(el => {
    const i = +el.dataset.party;
    el.classList.toggle('dim', !!sel && !active.includes(i));
    el.classList.toggle('active', sel?.kind === 'party' && sel.index === i);
    el.setAttribute('aria-pressed', cs.locked?.kind === 'party' && cs.locked.index === i);
  });
  document.querySelectorAll('#cluster-legend [data-bloc]').forEach(el => {
    const bi = +el.dataset.bloc;
    el.classList.toggle('active', sel?.kind === 'bloc' && sel.index === bi);
    el.setAttribute('aria-pressed', cs.locked?.kind === 'bloc' && cs.locked.index === bi);
    const n = sum(YEAR[cs.year].blocMembers[bi].map(i => g.votes[i]));
    el.querySelector('.bloc-value').textContent = pct(n / g.valid);
  });

  const z = cs.geometry;
  if (!z) return;
  const values = $('cluster-values');
  values.innerHTML = !sel || z.mobile ? '' : cs.coords.filter(c => c.w > 30).map(c =>
    `<text class="value-label" x="${c.x + c.w / 2}" y="18" text-anchor="middle" direction="ltr">${pct(countIn(c.g) / c.g.valid)}</text>`).join('');
  const c = cs.coords.find(c => c.g.id === g.id);
  $('cluster-outline').innerHTML = c ? `<rect class="selected-group" x="${c.x}" y="${c.y}" width="${c.w}" height="${c.h}"/>` : '';

  renderSelectionBanner();
  const ref = $('national-reference');
  if (!sel) { ref.innerHTML = ''; return; }
  const nat = YEAR[cs.year].national, n = countIn(nat), share = n / nat.valid;
  const label = T.clusters.nationalLine(pct(share, 2), fmt(n));
  if (z.mobile) {
    const x = RTL ? z.W - z.R - z.pw * share : z.L + z.pw * share;
    ref.innerHTML = `<line class="national-line" x1="${x}" x2="${x}" y1="${z.T0}" y2="${z.H - z.B}"/>` +
      `<text class="reference-label" x="${RTL ? z.W - z.R : z.L}" y="${z.H - 6}" text-anchor="${anchor(RTL ? 'left' : 'right')}">` +
      `<tspan class="reference-name">${esc(selectionName())}</tspan> · ${esc(label)}</text>`;
  } else {
    const y = z.T0 + z.ph * (1 - share);
    const x = RTL ? z.L + 4 : z.W - z.R - 4;
    // Keep the label inside the plot even when the share is near 0% or 100%.
    const ly = Math.min(Math.max(y - 7, z.T0 + 14), z.T0 + z.ph - 4);
    ref.innerHTML = `<line class="national-line" x1="${z.L}" x2="${z.W - z.R}" y1="${y}" y2="${y}"/>` +
      `<text class="reference-label halo" x="${x}" y="${ly}" text-anchor="${anchor(RTL ? 'right' : 'left')}">` +
      `<tspan class="reference-name">${esc(selectionName())}</tspan> · ${esc(label)}</text>`;
  }
}

function renderSelectionBanner() {
  const sel = selection(), banner = $('selection-banner');
  if (!sel) { banner.innerHTML = `<span class="muted">${T.clusters.allLists}</span>`; banner.classList.remove('on'); return; }
  const y = YEAR[cs.year], g = currentGroup();
  const color = sel.kind === 'party' ? y.parties[sel.index].color : BLOCS[sel.index].color;
  const logo = sel.kind === 'party' && y.parties[sel.index].logo
    ? `<img src="${esc(y.parties[sel.index].logo)}" alt="" onerror="this.remove()">` : '';
  banner.classList.add('on');
  banner.style.setProperty('--sel', color);
  banner.innerHTML = `<i class="swatch big" style="background:${color}"></i>${logo}<b>${esc(selectionName())}</b>` +
    `<span>${esc(groupName(g.id))}: <b>${pct(countIn(g) / g.valid, 1)}</b> · ${fmt(countIn(g))} ${T.votes}</span>` +
    (cs.locked && sameSel(cs.locked, sel) ? '<span class="pin" aria-hidden="true">📌</span>' : '');
}

// --- Side panel --------------------------------------------------------------

function renderGroupPanel() {
  const g = currentGroup(), y = YEAR[cs.year], nat = y.national, sel = selection();
  $('group-select').value = g.id;
  const turnout = g.eligible ? `<span>${T.turnout}: <b>${pct(g.voters / g.eligible)}</b></span>` : '';
  $('group-summary').innerHTML =
    `<span><b>${fmt(g.valid)}</b> ${T.validVotes}</span>` +
    (g.id === 'national' ? '' : `<span><b>${pct(g.valid / nat.valid, 1)}</b> ${T.clusters.shareOfAll}</span>`) + turnout;
  $('group-note').textContent = groupNote(g.id, cs.year);
  $('group-breakdown-title').textContent = T.clusters.breakdown(`${groupName(g.id)} · ${cs.year}`);

  const key = `${cs.year}|${g.id}|${cs.merge}`;
  const rebuild = key !== cs.panelKey;
  cs.panelKey = key;
  renderDonut(g, rebuild);
  if (!rebuild) return;
  const ranking = g.votes.map((v, i) => ({ v, i })).sort((a, b) => b.v - a.v);
  const max = ranking[0].v / g.valid;
  $('group-ranking').innerHTML = ranking.map(({ v, i }) => {
    const p = y.parties[i], share = v / g.valid, natShare = nat.votes[i] / nat.valid;
    const delta = share - natShare;
    const deltaCell = g.id === 'national' ? '' :
      `<span class="delta ${delta > 0.0005 ? 'up' : delta < -0.0005 ? 'down' : ''}" title="${T.clusters.vsNational}">${pts(delta)}</span>`;
    return `<button type="button" class="rank-row" data-rank="${i}" aria-label="${esc(name(p))}: ${pct(share, 2)}">` +
      `<span class="rank-name"><i class="swatch" style="background:${p.color}"></i>${esc(name(p))}</span>` +
      `<span class="rank-bar"><i style="width:${(share / max) * 100}%;background:${p.color}"></i></span>` +
      `<b class="rank-value">${pct(share, 1)}</b>${deltaCell}</button>`;
  }).join('');
  $('group-ranking').querySelectorAll('[data-rank]').forEach(el => {
    const sel = { kind: 'party', index: +el.dataset.rank };
    el.addEventListener('pointerenter', e => setHover(sel, e));
    el.addEventListener('pointerleave', () => setHover(null));
    el.addEventListener('click', () => choose(sel));
  });
}

function renderDonut(g, rebuild) {
  if (!donut) {
    donut = echarts.init($('group-donut'), null, { renderer: 'svg' });
    donut.on('mouseover', e => { cs.hover = { kind: 'party', index: e.dataIndex }; updateClusters(); });
    donut.on('globalout', () => { cs.hover = null; updateClusters(); });
    donut.on('click', e => choose({ kind: 'party', index: e.dataIndex }));
    new ResizeObserver(() => donut.resize()).observe($('group-donut'));
  }
  const sel = selection(), active = selectedIds();
  const shown = sel ? countIn(g) / g.valid : null;
  donut.setOption({
    animation: false,
    tooltip: { show: false },
    aria: { enabled: true },
    graphic: [
      { type: 'text', left: 'center', top: '40%', silent: true,
        style: { text: shown === null ? groupName(g.id, !/^\d+$/.test(g.id)) : pct(shown, 1), fill: '#17384a', font: 'bold 16px system-ui, Arial', textAlign: 'center' } },
      { type: 'text', left: 'center', top: '54%', silent: true,
        style: { text: shown === null ? fmt(g.valid) : selectionName(), fill: '#5d7381', font: '12px system-ui, Arial', textAlign: 'center',
                 width: 90, overflow: 'truncate' } },
    ],
    series: [{
      id: 'votes', type: 'pie', radius: ['55%', '88%'], startAngle: 90, selectedMode: false,
      emphasis: { scale: true, scaleSize: 4, focus: 'none', label: { show: false } },
      label: { show: false }, labelLine: { show: false },
      itemStyle: { borderColor: '#fff', borderWidth: 1 },
      data: g.votes.map((value, i) => ({
        name: name(parties()[i]), value,
        itemStyle: { color: parties()[i].color, opacity: sel && !active.includes(i) ? 0.18 : 1 },
      })),
    }],
  }, rebuild);
}

// --- Legend and table ----------------------------------------------------------

function renderClusterLegend() {
  const legend = $('cluster-legend');
  legend.innerHTML = '';
  const y = YEAR[cs.year];
  BLOCS.forEach((b, bi) => {
    const members = y.blocMembers[bi];
    if (!members.length) return;
    const section = document.createElement('section');
    section.className = 'bloc-group';
    section.innerHTML = `<button type="button" class="bloc-title" data-bloc="${bi}" aria-pressed="false" style="--bloc:${b.color}">` +
      `<span>${esc(name(b))}</span><span class="bloc-value"></span></button><div class="bloc-parties"></div>`;
    const title = section.querySelector('button');
    title.addEventListener('click', () => choose({ kind: 'bloc', index: bi }));
    title.addEventListener('pointerenter', e => setHover({ kind: 'bloc', index: bi }, e));
    title.addEventListener('pointerleave', () => setHover(null));
    members.forEach(i => {
      const p = y.parties[i];
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'party';
      button.dataset.party = i;
      button.setAttribute('aria-pressed', 'false');
      button.innerHTML = `<i class="swatch" style="background:${p.color}"></i>` +
        (p.logo ? `<img src="${esc(p.logo)}" alt="" loading="lazy" onerror="this.remove()">` : '') +
        `<span>${esc(name(p))}</span>` +
        (p.code === '—' ? '' : p.elected ? `<span class="code">${esc(p.code)}</span>`
          : `<span class="code">${esc(p.code)}</span><span class="muted-tag" title="${T.clusters.belowThreshold}">*</span>`);
      const sel = { kind: 'party', index: i };
      button.addEventListener('click', () => choose(sel));
      button.addEventListener('pointerenter', e => setHover(sel, e));
      button.addEventListener('pointerleave', () => setHover(null));
      section.querySelector('.bloc-parties').append(button);
    });
    legend.append(section);
  });
}

function renderClusterTable() {
  const y = YEAR[cs.year];
  $('cluster-table').innerHTML =
    `<thead><tr><th>${T.clusters.group}</th><th>${T.validVotes}</th><th>${T.turnout}</th>` +
    y.parties.map(p => `<th>${esc(name(p))}</th>`).join('') + '</tr></thead><tbody>' +
    cs.groups.map(g => `<tr class="${g.id === 'national' ? 'total-row' : ''}"><th>${esc(groupName(g.id))}</th><td>${fmt(g.valid)}</td>` +
      `<td>${g.eligible ? pct(g.voters / g.eligible) : '—'}</td>` +
      g.votes.map(v => `<td>${pct(v / g.valid, 2)}<small>${fmt(v)}</small></td>`).join('') + '</tr>').join('') + '</tbody>';
}

// --- Orchestration -----------------------------------------------------------------

function updateClusters() {
  const g = currentGroup();
  $('cluster-legend-context').textContent = T.clusters.legendContext(groupName(g.id));
  renderGroupPanel();
  applyClusterHighlight();
}

function regroupClusters() {
  buildGroups();
  $('group-select').innerHTML = cs.groups.map(g => `<option value="${g.id}">${esc(groupName(g.id))}</option>`).join('');
  const nat = YEAR[cs.year].national;
  $('clusters-lead').textContent = T.clusters.lead(cs.year, fmt(nat.valid));
  renderClusterLegend();
  renderClusterChart();
  renderClusterTable();
  updateClusters();
}

function setClusterYear(year) {
  cs.year = +year;
  // Party indices differ between years; bloc selections carry over.
  if (cs.locked?.kind === 'party') cs.locked = null;
  cs.hover = null;
  regroupClusters();
}

function initClusters() {
  segmented($('cluster-year'), YEARS.map(y => ({ value: String(y), label: String(y) })), String(cs.year), setClusterYear);
  $('merge-groups').addEventListener('change', e => { cs.merge = e.target.checked; regroupClusters(); });
  $('cluster-reset').addEventListener('click', () => { cs.locked = cs.hover = cs.hoverGroup = null; updateClusters(); });
  $('group-select').addEventListener('change', e => chooseGroup(e.target.value));
  const details = $('group-breakdown');
  $('expand-breakdown').addEventListener('click', () => {
    details.open = !details.open;
    if (details.open) requestAnimationFrame(() => details.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  });
  details.addEventListener('toggle', () => $('expand-breakdown').setAttribute('aria-expanded', details.open));
  $('cluster-chart').addEventListener('pointerleave', () => { cs.hover = cs.hoverGroup = null; updateClusters(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') $('cluster-reset').click(); });
  new ResizeObserver(() => renderClusterChart()).observe($('cluster-chart').parentElement);
  regroupClusters();
}
