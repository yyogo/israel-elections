#!/usr/bin/env python3
"""Assemble dashboard-data.json from the derived tables and build the self-contained site.

Run scripts/analyze.py and scripts/flows.py first.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / 'data/derived'
SRC = ROOT / 'src'
DIST = ROOT / 'dist'
YEARS = [2022, 2026]
GROUP_IDS = {**{str(i): str(i) for i in range(1, 11)},
             'Unassigned settlements': 'unassigned', 'External envelopes': 'external'}
# Concatenation order matters: later files use helpers from earlier ones.
JS_FILES = ['i18n.js', 'util.js', 'clusters.js', 'trends.js', 'settlements.js', 'app.js']


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def display_votes(row, parties):
    """Votes per displayed list, with every other list summed into the residual."""
    named = {p['code'] for p in parties}
    codes = [k for k in row if k not in SETTLEMENT_FIELDS]
    votes = [int(row[p['code']]) for p in parties]
    votes.append(sum(int(row[c]) for c in codes if c not in named))
    return votes


SETTLEMENT_FIELDS = {'year', 'settlement_code', 'settlement_name_he', 'cluster', 'assignment_status', 'group',
                     'eligible', 'voters', 'invalid', 'valid'}


def build_data():
    meta = json.loads((SRC / 'parties.json').read_text(encoding='utf-8'))
    data = {'blocs': meta['blocs'], 'years': {}, 'settlements': {}}
    for year in YEARS:
        parties = meta['years'][str(year)]['parties']
        groups = {gid: {'id': gid, 'eligible': 0, 'voters': 0, 'valid': 0, 'votes': [0] * (len(parties) + 1)}
                  for gid in GROUP_IDS.values()}
        for row in read_csv(DERIVED / str(year) / 'settlements_wide.csv'):
            g = groups[GROUP_IDS[row['group']]]
            votes = display_votes(row, parties)
            for key in ('eligible', 'voters', 'valid'):
                g[key] += int(row[key])
            g['votes'] = [a + b for a, b in zip(g['votes'], votes)]
            code = int(row['settlement_code'])
            s = data['settlements'].setdefault(code, {'code': code, 'name': row['settlement_name_he'],
                                                      'cluster': int(row['cluster']) if row['cluster'] else None,
                                                      'years': {}})
            s['name'] = row['settlement_name_he']  # prefer the newest label
            s['years'][year] = [int(row['eligible']), int(row['voters']), int(row['valid'])] + votes
        assert sum(g['valid'] for g in groups.values()) == meta['years'][str(year)]['valid']
        data['years'][year] = {'parties': parties + [meta['residual']], 'groups': list(groups.values())}
        # Neighbourhood basis: statistical-area clusters inside divided municipalities.
        area_path = DERIVED / str(year) / 'area_clusters_wide.csv'
        if area_path.exists():
            data['years'][year]['areaGroups'] = [
                {'id': GROUP_IDS[row['group']], 'eligible': int(row['eligible']), 'voters': int(row['voters']),
                 'valid': int(row['valid']), 'votes': display_votes(row, parties)} for row in read_csv(area_path)]
            audit = json.loads((DERIVED / str(year) / 'audit.json').read_text(encoding='utf-8'))
            data['years'][year]['areaBasis'] = audit['area_basis_valid_votes']
    data['settlements'] = sorted(data['settlements'].values(), key=lambda s: s['code'])
    flows = json.loads((DERIVED / 'flows.json').read_text(encoding='utf-8'))
    data['flows'] = {level: flows[level] for level in ('bloc', 'list')}
    for level in data['flows'].values():
        level['diagnostics'].pop('raw_transition', None)
    return data


def main():
    if not (DERIVED / 'flows.json').exists():
        raise SystemExit('Run python3 scripts/analyze.py and python3 scripts/flows.py first.')
    data = build_data()
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    (DERIVED / 'dashboard-data.json').write_text(payload, encoding='utf-8')

    app = '\n'.join((SRC / 'js' / name).read_text(encoding='utf-8') for name in JS_FILES)
    app = '(() => {\n"use strict";\nconst DATA = ' + payload.replace('</', '<\\/') + ';\n' + app + '\n})();'
    lib = (ROOT / 'vendor/echarts-5.6.0.min.js').read_text(encoding='utf-8').replace('</script', '<\\/script')
    html = (SRC / 'index.template.html').read_text(encoding='utf-8')
    for marker, value in (('__STYLE__', (SRC / 'styles.css').read_text(encoding='utf-8')),
                          ('__ECHARTS__', lib), ('__APP__', app)):
        assert html.count(marker) == 1, marker
        html = html.replace(marker, value)
    DIST.mkdir(exist_ok=True)
    out = DIST / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f'Built {out.relative_to(ROOT)} ({len(html) // 1024} KB) SHA256={hashlib.sha256(out.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
