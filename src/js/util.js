// ---------------------------------------------------------------------------
// Shared helpers and derived data.
// ---------------------------------------------------------------------------
const $ = id => document.getElementById(id);
const numberFormat = new Intl.NumberFormat(LANG === 'he' ? 'he-IL' : 'en-US');
const fmt = n => numberFormat.format(Math.round(n));
const pct = (n, digits = 1) => (n * 100).toFixed(digits) + '%';
// The left-to-right mark keeps the sign before the number inside RTL text.
const pts = (n, digits = 1) => '\u200e' + (n > 0 ? '+' : n < 0 ? '−' : '±') + Math.abs(n * 100).toFixed(digits);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const sum = xs => xs.reduce((a, b) => a + b, 0);
const YEARS = Object.keys(DATA.years).map(Number);
const LATEST = Math.max(...YEARS);
const BLOCS = DATA.blocs;
const blocIndex = Object.fromEntries(BLOCS.map((b, i) => [b.id, i]));

// Year-specific helpers: parties, which party indices belong to each bloc, and groups.
const YEAR = Object.fromEntries(YEARS.map(year => {
  const d = DATA.years[year];
  const blocMembers = BLOCS.map(b => d.parties.flatMap((p, i) => (p.bloc === b.id ? [i] : [])));
  const national = {
    id: 'national',
    eligible: sum(d.groups.map(g => g.eligible)),
    voters: sum(d.groups.map(g => g.voters)),
    valid: sum(d.groups.map(g => g.valid)),
    votes: d.parties.map((_, i) => sum(d.groups.map(g => g.votes[i]))),
  };
  return [year, { year, parties: d.parties, groups: d.groups, areaGroups: d.areaGroups, areaBasis: d.areaBasis, blocMembers, national }];
}));

const groupsFor = (year, basis) => (basis === 'area' && YEAR[year].areaGroups) || YEAR[year].groups;
const groupById = (year, id, basis = 'locality') =>
  (id === 'national' ? YEAR[year].national : groupsFor(year, basis).find(g => g.id === id));

function groupName(id, short = false) {
  if (id === 'national') return short ? T.nationalShort : T.national;
  if (/^\d+$/.test(id)) return short ? T.clusterShort(id) : T.cluster(id);
  return T.groups[id + (short ? 'Short' : '')];
}

function groupNote(id, year) {
  const note = T.groupNotes[id];
  if (typeof note === 'function') {
    const count = DATA.settlements.filter(s => s.cluster === null && s.code !== 9999 && s.years[year]).length;
    return note(count);
  }
  return note ?? '';
}

// Metrics comparable across years: bloc shares (of valid votes) and turnout.
const METRICS = [
  ...BLOCS.map(b => ({ id: b.id, label: () => name(b), color: b.color })),
  { id: 'turnout', label: () => T.metrics.turnout, color: '#5b6b75' },
];

/** Metric value for a vote row [eligible, voters, valid, ...votes] or a group object. */
function metricValue(year, metricId, g) {
  const eligible = g.eligible ?? g[0], voters = g.voters ?? g[1], valid = g.valid ?? g[2];
  const votes = g.votes ?? g.slice(3);
  if (metricId === 'turnout') return eligible ? voters / eligible : null;
  if (!valid) return null;
  return sum(YEAR[year].blocMembers[blocIndex[metricId]].map(i => votes[i])) / valid;
}

function segmented(container, options, value, onChange) {
  container.innerHTML = options.map(o =>
    `<button type="button" data-value="${esc(o.value)}" aria-pressed="${o.value === value}">${esc(o.label)}</button>`).join('');
  container.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
    container.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
    onChange(b.dataset.value);
  }));
}

/** Small floating tooltip shared by the SVG charts that use one. */
const tooltip = (() => {
  const el = document.createElement('div');
  el.className = 'tooltip';
  el.hidden = true;
  document.body.append(el);
  return {
    show(html, event) {
      el.innerHTML = html;
      el.hidden = false;
      const pad = 12, r = el.getBoundingClientRect();
      let x = event.clientX + pad, y = event.clientY + pad;
      if (x + r.width > innerWidth - 4) x = event.clientX - r.width - pad;
      if (y + r.height > innerHeight - 4) y = event.clientY - r.height - pad;
      el.style.left = Math.max(4, x) + 'px';
      el.style.top = Math.max(4, y) + 'px';
    },
    hide() { el.hidden = true; },
  };
})();

/**
 * SVG text-anchor for text that should grow towards a physical side of x.
 * In an RTL document "start" is the right edge, so the keywords flip.
 */
const RTL = LANG === 'he';
// Arrows are not mirrored by the bidi algorithm, so pick the one that points in reading order.
const ARROW = RTL ? '←' : '→';
function anchor(grow) {
  if (grow === 'middle') return 'middle';
  return (grow === 'right') !== RTL ? 'start' : 'end';
}

// ECharts containers are LTR (see styles.css); give their HTML tooltips the page direction.
const TOOLTIP_DIR = `direction:${RTL ? 'rtl' : 'ltr'};text-align:start;`;
const ECHARTS_TEXT = { fontFamily: 'system-ui, -apple-system, "Segoe UI", Arial, sans-serif', color: '#17384a' };
