// ---------------------------------------------------------------------------
// Trends tab: national KPIs, estimated vote-flow Sankey, change by cluster and
// change by locality.
// ---------------------------------------------------------------------------
const [Y0, Y1] = YEARS;
const trendState = { level: 'bloc', nonvoters: true, metric: 'netanyahu' };
let byClusterChart = null, scatterChart = null;
const NONVOTE_COLOR = '#93a1aa';

// --- KPIs ----------------------------------------------------------------------

function renderKpis() {
  $('trend-kpis').innerHTML = METRICS.map(m => {
    const a = metricValue(Y0, m.id, YEAR[Y0].national), b = metricValue(Y1, m.id, YEAR[Y1].national);
    const d = b - a;
    return `<div class="kpi" style="--accent:${m.color}"><span class="kpi-label">${esc(m.label())}</span>` +
      `<span class="kpi-values"><span>${Y0}: ${pct(a)}</span><b>${Y1}: ${pct(b)}</b></span>` +
      `<span class="kpi-delta"><span class="delta ${d > 0 ? 'up' : 'down'}">${pts(d)}</span> ${T.clusters.pts}</span></div>`;
  }).join('');
}

// --- Sankey --------------------------------------------------------------------------

function flowNodeInfo(year, id) {
  if (id === 'nonvote') return { label: T.trends.nonvote, short: T.trends.nonvoteShort, color: NONVOTE_COLOR };
  if (id === 'other_lists') return { label: T.trends.otherLists, short: T.trends.otherLists, color: '#c3cbd0' };
  if (blocIndex[id] !== undefined) {
    const b = BLOCS[blocIndex[id]];
    return { label: name(b), short: name(b), color: b.color };
  }
  const p = YEAR[year].parties.find(p => p.code === id);
  return { label: name(p), short: shortName(p), color: p.color };
}

function renderSankey() {
  const model = DATA.flows[trendState.level];
  const keep = id => trendState.nonvoters || id !== 'nonvote';
  const flows = model.flows.filter(f => keep(f.from) && keep(f.to) && f.value > 0);
  const sources = model.sources.filter(s => keep(s.id));
  const targets = model.targets.filter(s => keep(s.id));
  const totalOut = id => sum(flows.filter(f => f.from === id).map(f => f.value));
  const totalIn = id => sum(flows.filter(f => f.to === id).map(f => f.value));
  const grand = sum(flows.map(f => f.value));
  const eligible = { [Y0]: sum(model.sources.map(s => s.total)), [Y1]: sum(model.targets.map(s => s.total)) };

  const svg = $('sankey');
  const W = svg.parentElement.clientWidth;
  if (!W) return;
  const mobile = W < 620;
  const labelW = mobile ? 96 : 175, nodeW = mobile ? 10 : 14;
  const nodeCount = Math.max(sources.length, targets.length);
  const gap = trendState.level === 'list' ? 5 : 10;
  const H = Math.max(trendState.level === 'list' ? (mobile ? 560 : 640) : (mobile ? 420 : 470), nodeCount * 22);
  const top = 30, bottom = 10;
  const usable = H - top - bottom - gap * (nodeCount - 1);
  const k = usable / grand;
  // 2022 on the start side, 2026 on the end side.
  const xStart = RTL ? W - labelW - nodeW : labelW;
  const xEnd = RTL ? labelW : W - labelW - nodeW;

  const layout = (list, year, x, total) => {
    let y = top;
    return list.map(n => {
      const h = Math.max(1, total(n.id) * k);
      const node = { ...n, year, x, y, h, ...flowNodeInfo(year, n.id), outY: y, inY: y };
      y += h + gap;
      return node;
    });
  };
  const left = layout(sources, Y0, xStart, totalOut);
  const right = layout(targets, Y1, xEnd, totalIn);
  const L = Object.fromEntries(left.map(n => [n.id, n])), R = Object.fromEntries(right.map(n => [n.id, n]));

  // Links are stacked in node order on both ends, so bands never cross inside a node.
  let links = '';
  const sx = RTL ? xStart : xStart + nodeW, tx = RTL ? xEnd + nodeW : xEnd;
  const mid = (sx + tx) / 2;
  flows.slice().sort((a, b) => sources.findIndex(s => s.id === a.from) - sources.findIndex(s => s.id === b.from) ||
    targets.findIndex(s => s.id === a.to) - targets.findIndex(s => s.id === b.to)).forEach(f => {
    const s = L[f.from], t = R[f.to], h = f.value * k;
    const y0 = s.outY, y1 = t.inY;
    s.outY += h;
    t.inY += h;
    if (f.value / grand < 0.0008) return; // invisible slivers
    const i = model.flows.indexOf(f);
    links += `<path class="flow" data-flow="${i}" data-from="${esc(f.from)}" data-to="${esc(f.to)}" fill="${s.color}" ` +
      `d="M${sx},${y0} C${mid},${y0} ${mid},${y1} ${tx},${y1} L${tx},${y1 + h} C${mid},${y1 + h} ${mid},${y0 + h} ${sx},${y0 + h} Z"/>`;
  });

  let nodes = '';
  const nodeLabel = (n, outer) => {
    if (n.h < 9) return '';
    const x = outer === 'left' ? n.x - 6 : n.x + nodeW + 6;
    const cy = n.y + n.h / 2;
    const share = pct(n.total / eligible[n.year]);
    const second = n.h >= 24 ? `<tspan x="${x}" dy="14" class="node-sub">${fmt(n.total)} · ${share}</tspan>` : '';
    return `<text class="node-label" x="${x}" y="${second ? cy - 3 : cy + 4}" text-anchor="${anchor(outer)}">${esc(n.short)}${second}</text>`;
  };
  [...left, ...right].forEach(n => {
    nodes += `<rect class="node" data-node="${n.year}:${esc(n.id)}" x="${n.x}" y="${n.y}" width="${nodeW}" height="${n.h}" fill="${n.color}"/>`;
  });
  left.forEach(n => { nodes += nodeLabel(n, RTL ? 'right' : 'left'); });
  right.forEach(n => { nodes += nodeLabel(n, RTL ? 'left' : 'right'); });
  const headX0 = RTL ? xStart + nodeW : xStart, headX1 = RTL ? xEnd : xEnd + nodeW;
  const heads = `<text class="sankey-year" x="${headX0}" y="16" text-anchor="${anchor(RTL ? 'left' : 'right')}">${Y0}</text>` +
    `<text class="sankey-year" x="${headX1}" y="16" text-anchor="${anchor(RTL ? 'right' : 'left')}">${Y1}</text>`;

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.style.height = H + 'px';
  svg.innerHTML = heads + `<g class="flows">${links}</g>` + nodes;

  const nodeById = Object.fromEntries([...left, ...right].map(n => [`${n.year}:${n.id}`, n]));
  const highlight = (pred) => svg.querySelectorAll('.flow').forEach(p => p.classList.toggle('dim', !!pred && !pred(p)));
  svg.querySelectorAll('.flow').forEach(p => {
    const f = model.flows[+p.dataset.flow];
    const from = flowNodeInfo(Y0, f.from).label, to = flowNodeInfo(Y1, f.to).label;
    const ci = `${pct(f.ci90[0], 0)}–${pct(f.ci90[1], 0)}`;
    p.addEventListener('pointermove', e => {
      highlight(q => q === p);
      tooltip.show(esc(T.trends.flowTip(from, to, pct(f.share_of_source, 0), ci, fmt(f.value))), e);
    });
    p.addEventListener('pointerleave', () => { highlight(null); tooltip.hide(); });
  });
  svg.querySelectorAll('.node').forEach(r => {
    const n = nodeById[r.dataset.node];
    r.addEventListener('pointermove', e => {
      highlight(q => (n.year === Y0 ? q.dataset.from : q.dataset.to) === n.id);
      tooltip.show(esc(T.trends.flowTipNode(n.label, n.year, fmt(n.total), pct(n.total / eligible[n.year]))), e);
    });
    r.addEventListener('pointerleave', () => { highlight(null); tooltip.hide(); });
  });

  const d = model.diagnostics;
  $('sankey-note').textContent = T.trends.fitNote(d.weighted_r2.toFixed(2), trendState.level === 'bloc' ? T.trends.levelBloc : T.trends.levelList);
  $('sankey-caveat').hidden = trendState.level !== 'list';
  renderFlowTable(model, keep);
}

function renderFlowTable(model, keep) {
  const rows = model.flows.filter(f => keep(f.from) && keep(f.to) && f.share_of_source >= 0.01)
    .sort((a, b) => b.value - a.value);
  $('flow-table').innerHTML = `<thead><tr><th>${Y0}</th><th>${Y1}</th><th>${T.votes}</th><th>%</th><th>90%</th></tr></thead><tbody>` +
    rows.map(f => `<tr><th>${esc(flowNodeInfo(Y0, f.from).label)}</th><th>${esc(flowNodeInfo(Y1, f.to).label)}</th>` +
      `<td>${fmt(f.value)}</td><td>${pct(f.share_of_source)}</td><td>${pct(f.ci90[0], 0)}–${pct(f.ci90[1], 0)}</td></tr>`).join('') + '</tbody>';
}

// --- Change by cluster -------------------------------------------------------------

function renderByCluster() {
  const m = METRICS.find(m => m.id === trendState.metric);
  const ids = [...Array.from({ length: 10 }, (_, i) => String(i + 1)), 'national'];
  const values = year => ids.map(id => metricValue(year, m.id, groupById(year, id)));
  const a = values(Y0), b = values(Y1);
  if (!byClusterChart) {
    byClusterChart = echarts.init($('by-cluster'), null, { renderer: 'svg' });
    new ResizeObserver(() => byClusterChart.resize()).observe($('by-cluster'));
  }
  byClusterChart.setOption({
    animation: false,
    textStyle: ECHARTS_TEXT,
    grid: { left: 48, right: 48, top: 36, bottom: 30 },
    legend: { top: 0, data: [String(Y0), String(Y1)], textStyle: ECHARTS_TEXT, align: RTL ? 'right' : 'left' },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: ps => {
        const i = ps[0].dataIndex, d = b[i] - a[i];
        return `<b>${esc(groupName(ids[i]))}</b><br>${esc(m.label())}<br>${Y0}: ${pct(a[i])}<br>${Y1}: ${pct(b[i])}<br>${T.trends.change}: ${pts(d)} ${T.clusters.pts}`;
      },
    },
    xAxis: { type: 'category', inverse: RTL, data: ids.map(id => groupName(id, true)), axisTick: { show: false },
             axisLine: { lineStyle: { color: '#b8c4cb' } }, axisLabel: { color: '#405866', fontWeight: 600 } },
    yAxis: { type: 'value', position: RTL ? 'right' : 'left', axisLabel: { formatter: v => Math.round(v * 100) + '%', color: '#61727d' },
             splitLine: { lineStyle: { color: '#e6ecef' } }, min: v => Math.max(0, Math.floor(v.min * 10 - 0.5) / 10) },
    series: [
      {
        type: 'custom', silent: true, z: 1,
        renderItem: (params, api) => {
          const p0 = api.coord([api.value(0), api.value(1)]), p1 = api.coord([api.value(0), api.value(2)]);
          return { type: 'line', shape: { x1: p0[0], y1: p0[1], x2: p1[0], y2: p1[1] },
                   style: { stroke: api.value(2) >= api.value(1) ? m.color : '#8d9aa3', lineWidth: 3, opacity: 0.55 } };
        },
        data: ids.map((_, i) => [i, a[i], b[i]]),
      },
      { name: String(Y0), type: 'scatter', symbolSize: 11, z: 2, data: a,
        itemStyle: { color: '#fff', borderColor: m.color, borderWidth: 2 } },
      { name: String(Y1), type: 'scatter', symbolSize: 12, z: 3, data: b, itemStyle: { color: m.color, borderColor: '#fff', borderWidth: 1.5 },
        label: { show: true, position: RTL ? 'left' : 'right', distance: 7, fontSize: 11, color: '#405866', formatter: p => pts(b[p.dataIndex] - a[p.dataIndex], 0) } },
    ],
  }, true);
}

// --- Change by locality ------------------------------------------------------------

const CLUSTER_COLORS = ['#e8e3f3', '#d6cdea', '#c2b5df', '#ad9dd3', '#9886c6', '#8470b8', '#715ca8', '#5f4a96', '#4e3a82', '#3e2c6d'];

function renderScatter() {
  const m = METRICS.find(m => m.id === trendState.metric);
  // x = level in 2022, y = change by 2026: swings stand out instead of hugging a diagonal.
  const points = DATA.settlements.filter(s => s.code !== 9999 && s.years[Y0] && s.years[Y1] &&
    s.years[Y0][2] >= 500 && s.years[Y1][2] >= 500).map(s => {
    const a = metricValue(Y0, m.id, s.years[Y0]), b = metricValue(Y1, m.id, s.years[Y1]);
    return { value: [a, b - a, s.years[Y1][2], b], code: s.code, name: s.name, cluster: s.cluster,
             itemStyle: { color: s.cluster ? CLUSTER_COLORS[s.cluster - 1] : '#c9d1d6' } };
  });
  const xs = points.map(p => p.value[0]), ys = points.map(p => p.value[1]);
  const xlo = m.id === 'turnout' ? Math.floor(Math.min(...xs) * 10) / 10 : 0;
  const xhi = Math.min(1, Math.ceil(Math.max(...xs) * 10) / 10);
  const yabs = Math.ceil(Math.max(...ys.map(Math.abs)) * 20) / 20;
  if (!scatterChart) {
    scatterChart = echarts.init($('scatter'), null, { renderer: 'canvas' });
    scatterChart.on('click', e => { if (e.data?.code) openSettlement(e.data.code); });
    new ResizeObserver(() => scatterChart.resize()).observe($('scatter'));
  }
  const percentAxis = { axisLabel: { formatter: v => Math.round(v * 100) + '%', color: '#61727d' }, splitLine: { lineStyle: { color: '#eef2f4' } } };
  scatterChart.setOption({
    animation: false,
    textStyle: ECHARTS_TEXT,
    grid: { left: 64, right: 20, top: 14, bottom: 50 },
    tooltip: {
      formatter: p => p.data.code
        ? `<b>${esc(p.data.name)}</b><br>${p.data.cluster ? T.cluster(p.data.cluster) : T.settlements.noCluster}<br>` +
          `${esc(m.label())}: ${pct(p.value[0])} → <b>${pct(p.value[3])}</b> (${pts(p.value[1])} ${T.clusters.pts})<br>${fmt(p.value[2])} ${T.validVotes}`
        : '',
    },
    xAxis: { type: 'value', min: xlo, max: xhi, name: `${m.label()} · ${Y0}`, nameLocation: 'middle', nameGap: 30,
             nameTextStyle: { fontWeight: 600, color: '#405866' }, ...percentAxis },
    yAxis: { type: 'value', min: -yabs, max: yabs, name: `${T.trends.change} ${Y0}→${Y1}`, nameLocation: 'middle', nameGap: 46,
             nameTextStyle: { fontWeight: 600, color: '#405866' },
             axisLabel: { formatter: v => pts(v, 0), color: '#61727d' }, splitLine: { lineStyle: { color: '#eef2f4' } } },
    series: [{
      type: 'scatter', data: points, cursor: 'pointer',
      symbolSize: d => Math.max(4, Math.min(34, Math.sqrt(d[2]) / 9)),
      itemStyle: { borderColor: '#4b3a78', borderWidth: 0.5, opacity: 0.85 },
      emphasis: { itemStyle: { borderColor: '#17384a', borderWidth: 2 } },
      markLine: { silent: true, symbol: 'none', lineStyle: { color: '#5d7381', type: 'solid', width: 1 }, label: { show: false },
                  data: [{ yAxis: 0 }] },
    }],
  }, true);
  $('scatter-legend').innerHTML = `<span>${T.cluster('')}</span>` +
    CLUSTER_COLORS.map((c, i) => `<span><i class="swatch" style="background:${c}"></i>${i + 1}</span>`).join('') +
    `<span><i class="swatch" style="background:#c9d1d6"></i>${T.settlements.noCluster}</span>`;
}

// --- Orchestration -----------------------------------------------------------------

function renderTrends() {
  renderSankey();
  renderByCluster();
  renderScatter();
}

function initTrends() {
  renderKpis();
  segmented($('flow-level'), [{ value: 'bloc', label: T.trends.levelBloc }, { value: 'list', label: T.trends.levelList }],
    trendState.level, v => { trendState.level = v; renderSankey(); });
  $('flow-nonvoters').addEventListener('change', e => { trendState.nonvoters = e.target.checked; renderSankey(); });
  segmented($('trend-metric'), METRICS.map(m => ({ value: m.id, label: m.label() })), trendState.metric,
    v => { trendState.metric = v; renderByCluster(); renderScatter(); });
  new ResizeObserver(() => renderSankey()).observe($('sankey').parentElement);
}
