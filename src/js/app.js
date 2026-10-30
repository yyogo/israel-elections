// ---------------------------------------------------------------------------
// App shell: language, static strings, tabs.
// ---------------------------------------------------------------------------
const TABS = ['clusters', 'trends', 'settlements', 'about'];
const initialised = new Set();

function lookup(path) {
  return path.split('.').reduce((o, k) => o?.[k], T);
}

function applyStrings() {
  document.documentElement.lang = LANG;
  document.documentElement.dir = RTL ? 'rtl' : 'ltr';
  document.title = T.title;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const value = lookup(el.dataset.i18n);
    if (typeof value === 'string') el.innerHTML = value;
  });
  document.querySelectorAll('[data-lang]').forEach(el => { el.hidden = el.dataset.lang !== LANG; });
  const other = new URL(location.href);
  if (LANG === 'he') other.searchParams.set('lang', 'en'); else other.searchParams.delete('lang');
  const link = $('lang-switch');
  link.href = other.pathname + other.search + location.hash;
  link.textContent = T.langSwitch;
  link.lang = LANG === 'he' ? 'en' : 'he';
  $('tab-nav').innerHTML = TABS.map(t => `<a href="#${t}" role="tab" data-tab="${t}">${T.tabs[t]}</a>`).join('');
}

function showTab(tab) {
  if (!TABS.includes(tab)) tab = 'clusters';
  document.querySelectorAll('[data-tab]').forEach(a => a.setAttribute('aria-selected', a.dataset.tab === tab));
  TABS.forEach(t => { $('tab-' + t).hidden = t !== tab; });
  // Charts need a laid-out container, so each tab initialises on first display.
  if (!initialised.has(tab)) {
    initialised.add(tab);
    if (tab === 'clusters') initClusters();
    if (tab === 'trends') initTrends();
    if (tab === 'settlements') initSettlements();
  }
  if (tab === 'trends') requestAnimationFrame(renderTrends);
  if (tab === 'clusters') requestAnimationFrame(renderClusterChart);
}

applyStrings();
window.addEventListener('hashchange', () => {
  showTab(location.hash.slice(1));
  // Keep the language link pointing at the current tab.
  $('lang-switch').hash = location.hash;
});
showTab(location.hash.slice(1));
