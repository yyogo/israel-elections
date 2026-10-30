#!/usr/bin/env python3
"""Estimate 2022 -> 2026 vote flows by ecological inference over settlements.

Standard library only. Requires data/derived/<year>/settlements_wide.csv from analyze.py.

Model
-----
For every settlement s, let x_s be the 2022 share of eligible voters per category
(each list group, plus "did not vote") and y_s the same for 2026. We fit one
national transition matrix T (rows sum to 1, all entries >= 0) minimising

    sum_s w_s * || x_s T - y_s ||^2,    w_s = mean eligible voters in s

with accelerated projected gradient descent (each row projected onto the simplex).
The estimated flow matrix diag(N_2022) T is then raked (iterative proportional
fitting) so that both margins equal the official national totals, including
external-envelope votes that cannot be placed in any settlement.

This is a classic "ecological" estimate: it assumes voters of a given 2022 list
behaved similarly wherever they lived. It is reliable for large, geographically
distinctive groups (blocs, Arab lists, Haredi lists) and weak for lists whose
voters live in the same places (e.g. splits within the change bloc). Bootstrap
intervals over settlements are reported alongside every flow.
"""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/derived'
EXTERNAL = 9999
NONVOTE = 'nonvote'
OTHER = 'other_lists'
BOOTSTRAP = 60
MIN_LOCATED = 0.95
SEED = 2026


def read_settlements(year):
    with (OUT / str(year) / 'settlements_wide.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    skip = {'year', 'settlement_code', 'settlement_name_he', 'cluster', 'assignment_status', 'group',
            'eligible', 'voters', 'invalid', 'valid'}
    codes = [k for k in rows[0] if k not in skip]
    return codes, rows


def categorise(year, level, parties):
    """Map ballot code -> category id for a level ('bloc' or 'list')."""
    known = {p['code']: p for p in parties['years'][str(year)]['parties']}
    if level == 'bloc':
        return lambda code: known[code]['bloc'] if code in known else 'other'
    return lambda code: code if code in known else OTHER


def category_order(year, level, parties):
    if level == 'bloc':
        cats = [b['id'] for b in parties['blocs']]
    else:
        cats = [p['code'] for p in parties['years'][str(year)]['parties']] + [OTHER]
    return cats + [NONVOTE]


def read_areas(year):
    path = OUT / str(year) / 'areas_wide.csv'
    if not path.exists():
        return None
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def unit_keys(areas22, areas26):
    """Use statistical areas as units inside a locality when at least MIN_LOCATED of its
    eligible voters were located in both years; otherwise the whole locality is one unit."""
    def located_share(rows):
        total, located = defaultdict(int), defaultdict(int)
        for r in rows:
            loc, e = int(r['settlement_code']), int(r['eligible'])
            total[loc] += e
            if r['stat11']:
                located[loc] += e
        return {loc: located[loc] / total[loc] if total[loc] else 0 for loc in total}
    a, b = located_share(areas22), located_share(areas26)
    return {loc for loc in a if a[loc] >= MIN_LOCATED and b.get(loc, 0) >= MIN_LOCATED}


def tabulate(year, level, parties, split=frozenset()):
    """Return categories, per-unit counts (incl. non-voters) and national totals."""
    codes, rows = read_settlements(year)
    cat_of = categorise(year, level, parties)
    cats = category_order(year, level, parties)
    index = {c: i for i, c in enumerate(cats)}
    national = [0] * len(cats)
    eligible_total = 0
    for r in rows:
        eligible_total += int(r['eligible'])
        for code in codes:
            national[index[cat_of(code)]] += int(r[code])
    national[index[NONVOTE]] = eligible_total - sum(national)

    unit_rows = []
    areas = read_areas(year) if split else None
    for r in areas or rows:
        loc = int(r['settlement_code'])
        if loc == EXTERNAL:
            continue
        sa = r.get('stat11', '') if loc in split else ''
        if loc in split and not sa:
            continue  # the small unlocated remainder of a split locality
        unit_rows.append(((loc, sa), r))
    units = {}
    for key, r in unit_rows:
        eligible, counts = units.get(key, (0, [0] * len(cats)))
        for code in codes:
            counts[index[cat_of(code)]] += int(r[code])
        eligible += int(r['eligible'])
        units[key] = (eligible, counts)
    for key, (eligible, counts) in list(units.items()):
        if eligible <= 0:
            del units[key]
            continue
        valid = sum(counts)
        # Abstention and invalid ballots are grouped as "did not cast a valid vote".
        counts[index[NONVOTE]] = max(0, eligible - valid)
    return cats, units, national


def project_simplex(v):
    u = sorted(v, reverse=True)
    cumulative, theta = 0.0, 0.0
    for i, x in enumerate(u):
        cumulative += x
        t = (cumulative - 1) / (i + 1)
        if x - t > 0:
            theta = t
    return [max(0.0, x - theta) for x in v]


def fit(xs, ys, ws, start=None, iterations=4000, tol=1e-9):
    J, K = len(xs[0]), len(ys[0])
    A = [[0.0] * J for _ in range(J)]
    B = [[0.0] * K for _ in range(J)]
    for x, y, w in zip(xs, ys, ws):
        for a in range(J):
            wa = w * x[a]
            if not wa:
                continue
            Aa, Ba = A[a], B[a]
            for b in range(J):
                Aa[b] += wa * x[b]
            for k in range(K):
                Ba[k] += wa * y[k]
    # Lipschitz constant = largest eigenvalue of A (power iteration).
    v = [1.0] * J
    lipschitz = 1.0
    for _ in range(200):
        w = [sum(A[a][b] * v[b] for b in range(J)) for a in range(J)]
        lipschitz = max(abs(x) for x in w) or 1.0
        v = [x / lipschitz for x in w]
    step = 1 / lipschitz
    T = [row[:] for row in start] if start else [[1 / K] * K for _ in range(J)]
    Z, t = [row[:] for row in T], 1.0
    for _ in range(iterations):
        G = [[sum(A[a][c] * Z[c][k] for c in range(J)) - B[a][k] for k in range(K)] for a in range(J)]
        new = [project_simplex([Z[a][k] - step * G[a][k] for k in range(K)]) for a in range(J)]
        t_next = (1 + (1 + 4 * t * t) ** 0.5) / 2
        momentum = (t - 1) / t_next
        Z = [[new[a][k] + momentum * (new[a][k] - T[a][k]) for k in range(K)] for a in range(J)]
        change = max(abs(new[a][k] - T[a][k]) for a in range(J) for k in range(K))
        T, t = new, t_next
        if change < tol:
            break
    return T


def r_squared(xs, ys, ws, T):
    K = len(ys[0])
    total_w = sum(ws)
    mean = [sum(w * y[k] for y, w in zip(ys, ws)) / total_w for k in range(K)]
    ss_res = ss_tot = 0.0
    for x, y, w in zip(xs, ys, ws):
        for k in range(K):
            pred = sum(x[a] * T[a][k] for a in range(len(x)))
            ss_res += w * (pred - y[k]) ** 2
            ss_tot += w * (y[k] - mean[k]) ** 2
    return 1 - ss_res / ss_tot


def rake(T, row_totals, col_totals, rounds=500):
    """Scale diag(row_totals) @ T until rows and columns match the given margins."""
    scale = sum(row_totals) / sum(col_totals)
    cols = [c * scale for c in col_totals]
    F = [[row_totals[a] * T[a][k] for k in range(len(cols))] for a in range(len(row_totals))]
    for _ in range(rounds):
        for k, target in enumerate(cols):
            s = sum(F[a][k] for a in range(len(F)))
            if s:
                for a in range(len(F)):
                    F[a][k] *= target / s
        for a, target in enumerate(row_totals):
            s = sum(F[a])
            if s:
                F[a] = [v * target / s for v in F[a]]
    return F


def percentile(values, q):
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def unit_clusters():
    """Socioeconomic cluster per unit: statistical-area cluster where split, else the locality's."""
    _, rows = read_settlements(2026)
    clusters = {(int(r['settlement_code']), ''): r['cluster'] for r in rows}
    for r in read_areas(2026) or []:
        if r['stat11']:
            clusters[int(r['settlement_code']), r['stat11']] = r['area_cluster']
    return clusters


def export_units(level, keys, rows22, cols26, units22, units26):
    """Unit-level counts for the offline Bayesian model (scripts/ei/bayes_flows.py)."""
    clusters = unit_clusters()
    with (OUT / f'flows_units_{level}.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['settlement_code', 'stat11', 'cluster', 'eligible_2022', 'eligible_2026'] +
                   [f'2022:{c}' for c in rows22] + [f'2026:{c}' for c in cols26])
        for k in keys:
            w.writerow([k[0], k[1], clusters.get(k, ''), units22[k][0], units26[k][0], *units22[k][1], *units26[k][1]])


def estimate(level, parties):
    areas22, areas26 = read_areas(2022), read_areas(2026)
    split = frozenset(unit_keys(areas22, areas26)) if areas22 and areas26 else frozenset()
    rows22, units22, nat22 = tabulate(2022, level, parties, split)
    cols26, units26, nat26 = tabulate(2026, level, parties, split)
    keys = sorted(set(units22) & set(units26))
    xs = [[v / units22[k][0] for v in units22[k][1]] for k in keys]
    ys = [[v / units26[k][0] for v in units26[k][1]] for k in keys]
    ws = [(units22[k][0] + units26[k][0]) / 2 for k in keys]

    export_units(level, keys, rows22, cols26, units22, units26)

    T = fit(xs, ys, ws)
    F = rake(T, nat22, nat26)
    fit_r2 = r_squared(xs, ys, ws, T)

    # Net exchange is only defined where the same category exists in both years (blocs).
    pairs = []
    if level == 'bloc':
        pos = {c: k for k, c in enumerate(cols26)}
        pairs = [(a, b) for a in range(len(rows22)) for b in range(a + 1, len(rows22))
                 if rows22[a] in pos and rows22[b] in pos]
    net = lambda M, a, b: M[a][pos[rows22[b]]] - M[b][pos[rows22[a]]]

    rng = random.Random(SEED)
    samples = defaultdict(list)
    vote_samples = defaultdict(list)
    net_samples = defaultdict(list)
    for _ in range(BOOTSTRAP):
        idx = [rng.randrange(len(keys)) for _ in keys]
        Tb = fit([xs[i] for i in idx], [ys[i] for i in idx], [ws[i] for i in idx], start=T, iterations=1500, tol=1e-7)
        Fb = rake(Tb, nat22, nat26, rounds=200)
        for a in range(len(rows22)):
            for k in range(len(cols26)):
                samples[a, k].append(Fb[a][k] / nat22[a] if nat22[a] else 0)
                vote_samples[a, k].append(Fb[a][k])
        for a, b in pairs:
            net_samples[a, b].append(net(Fb, a, b))

    flows = []
    for a, source in enumerate(rows22):
        for k, target in enumerate(cols26):
            s = samples[a, k]
            flows.append({'from': source, 'to': target, 'value': round(F[a][k]),
                          'share_of_source': F[a][k] / nat22[a] if nat22[a] else 0,
                          'ci90': [percentile(s, 0.05), percentile(s, 0.95)],
                          'ci90_votes': [round(percentile(vote_samples[a, k], q)) for q in (0.05, 0.95)]})
    nets = [{'a': rows22[a], 'b': rows22[b], 'net': round(net(F, a, b)),
             'ci90': [round(percentile(net_samples[a, b], q)) for q in (0.05, 0.95)]} for a, b in pairs]
    return {
        'level': level,
        'sources': [{'id': c, 'total': n} for c, n in zip(rows22, nat22)],
        'targets': [{'id': c, 'total': n} for c, n in zip(cols26, nat26)],
        'flows': flows,
        'net': nets,
        'diagnostics': {'units': len(keys), 'split_localities': len(split), 'weighted_r2': fit_r2, 'bootstrap_replicates': BOOTSTRAP,
                        'raw_transition': [[round(v, 4) for v in row] for row in T]},
    }


def summarise(level, rows22, cols26, nat22, nat26, draws, point=None):
    """Flows, intervals and net exchange from a list of raked flow matrices (one per draw)."""
    n = len(draws)
    mean = [[sum(d[a][k] for d in draws) / n for k in range(len(cols26))] for a in range(len(rows22))]
    F = point or mean
    pairs, net = [], None
    if level == 'bloc':
        pos = {c: k for k, c in enumerate(cols26)}
        pairs = [(a, b) for a in range(len(rows22)) for b in range(a + 1, len(rows22))
                 if rows22[a] in pos and rows22[b] in pos]
        net = lambda M, a, b: M[a][pos[rows22[b]]] - M[b][pos[rows22[a]]]
    flows = []
    for a, source in enumerate(rows22):
        for k, target in enumerate(cols26):
            votes = [d[a][k] for d in draws]
            shares = [v / nat22[a] if nat22[a] else 0 for v in votes]
            flows.append({'from': source, 'to': target, 'value': round(F[a][k]),
                          'share_of_source': F[a][k] / nat22[a] if nat22[a] else 0,
                          'ci90': [percentile(shares, 0.05), percentile(shares, 0.95)],
                          'ci90_votes': [round(percentile(votes, q)) for q in (0.05, 0.95)]})
    nets = [{'a': rows22[a], 'b': rows22[b], 'net': round(net(F, a, b)),
             'ci90': [round(percentile([net(d, a, b) for d in draws], q)) for q in (0.05, 0.95)]} for a, b in pairs]
    return flows, nets


def bayes_estimate(level, lsq):
    """Combine the per-stratum posterior draws of scripts/ei/bayes_flows.py, draw by draw."""
    path = OUT / f'flows_bayes_{level}.json'
    if not path.exists():
        return None
    post = json.loads(path.read_text(encoding='utf-8'))
    rows22 = [s['id'] for s in lsq['sources']]
    cols26 = [s['id'] for s in lsq['targets']]
    assert post['rows'] == rows22 and post['cols'] == cols26, 'rerun scripts/ei/bayes_flows.py'
    nat22 = [s['total'] for s in lsq['sources']]
    nat26 = [s['total'] for s in lsq['targets']]
    draws = []
    for i in range(min(len(s['samples']) for s in post['strata'])):
        # National flow = sum over strata of (2022 group size x stratum transition), then raked.
        F0 = [[sum(s['group_totals_2022'][a] * s['samples'][i][a][k] for s in post['strata'])
               for k in range(len(cols26))] for a in range(len(rows22))]
        T = [[v / sum(row) if sum(row) else 1 / len(row) for v in row] for row in F0]
        draws.append(rake(T, nat22, nat26, rounds=200))
    flows, nets = summarise(level, rows22, cols26, nat22, nat26, draws)
    lsq_share = {(f['from'], f['to']): f['share_of_source'] for f in lsq['flows']}
    for f in flows:
        f['lsq_share_of_source'] = lsq_share[f['from'], f['to']]
    return {**lsq, 'flows': flows, 'net': nets, 'model': 'bayes',
            'diagnostics': {'units': lsq['diagnostics']['units'], 'model': post['model'], 'draws': len(draws),
                            'strata': [{'name': s['name'], **s['diagnostics']} for s in post['strata']],
                            'lsq_weighted_r2': lsq['diagnostics']['weighted_r2']}}


def main():
    parties = json.loads((ROOT / 'src/parties.json').read_text(encoding='utf-8'))
    lsq = {level: estimate(level, parties) for level in ('bloc', 'list')}
    # The Bayesian stratified model is the published estimate when its offline output exists;
    # the least-squares fit stays available for comparison.
    result = {level: bayes_estimate(level, lsq[level]) or {**lsq[level], 'model': 'lsq'} for level in lsq}
    result['lsq'] = lsq
    (OUT / 'flows.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    with (OUT / 'flows.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['level', 'from_2022', 'to_2026', 'estimated_votes', 'votes_ci90_low', 'votes_ci90_high',
                    'share_of_source', 'ci90_low', 'ci90_high'])
        for level in ('bloc', 'list'):
            for x in result[level]['flows']:
                w.writerow([level, x['from'], x['to'], x['value'], *x['ci90_votes'], f"{x['share_of_source']:.4f}",
                            f"{x['ci90'][0]:.4f}", f"{x['ci90'][1]:.4f}"])
    with (OUT / 'flows_net.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['bloc_a', 'bloc_b', 'net_votes_a_to_b', 'ci90_low', 'ci90_high'])
        for x in result['bloc']['net']:
            w.writerow([x['a'], x['b'], x['net'], *x['ci90']])
    for level in ('bloc', 'list'):
        print(level, result[level]['model'], json.dumps({k: v for k, v in result[level]['diagnostics'].items() if k != 'raw_transition'}))


if __name__ == '__main__':
    main()
