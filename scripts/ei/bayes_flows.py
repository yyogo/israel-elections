#!/usr/bin/env python3
"""Bayesian, stratified estimate of 2022 -> 2026 transitions (offline step).

Requires NumPyro/JAX/ArviZ (scripts/ei/requirements.txt). Input: data/derived/flows_units_<level>.csv
from scripts/flows.py. Output: data/derived/flows_bayes_<level>.json (committed), which
scripts/flows.py turns into flows, intervals and net exchange.

Model, per stratum s and unit u (a locality or statistical area):
    T_s[r, :] ~ Dirichlet(1)                    transition matrix, rows on the simplex
    kappa_s   ~ LogNormal(4, 1)                 overdispersion (95% prior range ~7-400)
    y_u ~ DirichletMultinomial(n_u, kappa_s * x_u T_s)
x_u are 2022 shares of eligible voters by group (incl. "did not vote"), y_u the 2026 counts.

kappa measures how far areas depart from the uniform-behaviour assumption: if areas differ
more than sampling noise allows, kappa is small and the posterior for T_s widens. Strata,
defined on 2022 composition, absorb the largest departures: Arab-majority and Haredi-majority
areas, and the remaining areas by socioeconomic cluster band (1-4, 5-7, 8-10).
"""
import argparse
import csv
import json
import os
import time
from pathlib import Path

os.environ.setdefault('XLA_FLAGS', '--xla_force_host_platform_device_count=8')
import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402
import numpy as np  # noqa: E402
import numpyro  # noqa: E402

numpyro.enable_x64()  # float32 rounding inflates R-hat for cells pinned near 0 or 1
import numpyro.distributions as dist  # noqa: E402
from numpyro.diagnostics import effective_sample_size, split_gelman_rubin  # noqa: E402
from numpyro.infer import MCMC, NUTS, init_to_value  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/derived'
ARAB_2022 = ('ום', 'עם', 'ד')
HAREDI_2022 = ('ג', 'שס')
STRATA = ['arab', 'haredi', 'clusters_1_4', 'clusters_5_7', 'clusters_8_10']
MIN_ROW_SHARE = 0.002  # 2022 groups smaller than this within a stratum carry no information there


def stratum_of(list_row):
    voted = sum(int(v) for k, v in list_row.items() if k.startswith('2022:') and k != '2022:nonvote')
    if voted:
        if sum(int(list_row[f'2022:{c}']) for c in ARAB_2022) / voted >= 0.5:
            return 'arab'
        if sum(int(list_row[f'2022:{c}']) for c in HAREDI_2022) / voted >= 0.5:
            return 'haredi'
    cluster = int(list_row['cluster']) if list_row['cluster'] else 0
    return 'clusters_1_4' if cluster <= 4 else 'clusters_5_7' if cluster <= 7 else 'clusters_8_10'


def read_units(level):
    with (OUT / f'flows_units_{level}.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    with (OUT / 'flows_units_list.csv').open(encoding='utf-8', newline='') as f:
        strata = {(r['settlement_code'], r['stat11']): stratum_of(r) for r in csv.DictReader(f)}
    cats22 = [k.split(':', 1)[1] for k in rows[0] if k.startswith('2022:')]
    cats26 = [k.split(':', 1)[1] for k in rows[0] if k.startswith('2026:')]
    return rows, strata, cats22, cats26


def model(x, n, y=None):
    r, c = x.shape[1], (y.shape[1] if y is not None else None)
    with numpyro.plate('rows', r):
        T = numpyro.sample('T', dist.Dirichlet(jnp.ones(c)))
    kappa = numpyro.sample('kappa', dist.LogNormal(4.0, 1.0))
    p = jnp.clip(x @ T, 1e-7, None)
    p = p / p.sum(axis=1, keepdims=True)
    with numpyro.plate('units', x.shape[0]):
        numpyro.sample('y', dist.DirichletMultinomial(kappa * p, total_count=n), obs=y)


def least_squares(xs, ys, iterations=5000):
    """Simplex-constrained least squares (as in scripts/flows.py), used to start the chains."""
    def project(v):
        u = -np.sort(-v, axis=1)
        css = np.cumsum(u, axis=1) - 1
        idx = np.arange(1, v.shape[1] + 1)
        rho = (u - css / idx > 0).sum(axis=1)
        theta = css[np.arange(v.shape[0]), rho - 1] / rho
        return np.maximum(v - theta[:, None], 0)
    A, B = xs.T @ xs, xs.T @ ys
    step = 1 / np.linalg.eigvalsh(A).max()
    T = np.full((xs.shape[1], ys.shape[1]), 1 / ys.shape[1])
    for _ in range(iterations):
        T = project(T - step * (A @ T - B))
    return T


def fit_stratum(rows, cats22, cats26, args, seed):
    x = np.array([[int(r[f'2022:{c}']) for c in cats22] for r in rows], dtype=float)
    y = np.array([[int(r[f'2026:{c}']) for c in cats26] for r in rows], dtype=float)
    # Groups/lists absent from a stratum (e.g. Balad outside Arab areas) are dropped: they hold no votes there.
    keep_r = x.sum(axis=0) >= MIN_ROW_SHARE * x.sum()
    keep_c = y.sum(axis=0) > 0
    xs = x[:, keep_r] / x[:, keep_r].sum(axis=1, keepdims=True)
    ys = y[:, keep_c]
    shares = ys / ys.sum(axis=1, keepdims=True)
    start = least_squares(xs, shares)
    start = (start + 1e-3) / (start + 1e-3).sum(axis=1, keepdims=True)  # off the boundary
    # Starting near typical kappa and capping tree depth keeps step-size adaptation from
    # collapsing in small strata (seen in the 36-unit Haredi stratum).
    kernel = NUTS(model, target_accept_prob=0.95, dense_mass=True, max_tree_depth=8,
                  init_strategy=init_to_value(values={'T': jnp.array(start), 'kappa': 60.0}))
    mcmc = MCMC(kernel, num_warmup=args.tune, num_samples=args.draws,
                num_chains=args.chains, chain_method='parallel', progress_bar=False)
    mcmc.run(jax.random.PRNGKey(seed), jnp.array(xs), jnp.array(ys.sum(axis=1)), y=jnp.array(ys))
    chains = mcmc.get_samples(group_by_chain=True)
    rhat = max(float(np.nanmax(split_gelman_rubin(np.asarray(chains[k])))) for k in ('T', 'kappa'))
    ess = min(float(np.nanmin(effective_sample_size(np.asarray(chains[k])))) for k in ('T', 'kappa'))
    T = np.asarray(mcmc.get_samples()['T'])  # S x r' x c'
    kappa = np.asarray(mcmc.get_samples()['kappa'])
    rng = np.random.default_rng(seed)
    T = T[rng.permutation(T.shape[0])[:args.keep]]
    full = np.zeros((T.shape[0], len(cats22), len(cats26)))
    full[np.ix_(range(T.shape[0]), np.flatnonzero(keep_r), np.flatnonzero(keep_c))] = T
    totals = np.zeros(len(cats22))
    totals[keep_r] = x[:, keep_r].sum(axis=0)
    divergences = int(np.asarray(mcmc.get_extra_fields()['diverging']).sum())
    return full, totals, {'units': len(rows), 'max_r_hat': rhat, 'min_ess': ess, 'divergences': divergences,
                          'kappa_median': float(np.median(kappa))}


def fit_converged(rows, cats22, cats26, args, seed, attempts=3):
    """Refit with a new seed and longer warm-up until diagnostics pass; never return a bad fit."""
    tune = args.tune
    for attempt in range(attempts):
        run = argparse.Namespace(**{**vars(args), 'tune': tune})
        samples, totals, diag = fit_stratum(rows, cats22, cats26, run, seed + 100 * attempt)
        diag['attempt'] = attempt + 1
        if diag['max_r_hat'] <= 1.01 and diag['divergences'] == 0 and diag['min_ess'] >= 400:
            return samples, totals, diag
        print('  retry:', json.dumps(diag), flush=True)
        tune *= 2
    raise SystemExit(f'stratum did not converge after {attempts} attempts: {diag}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--level', choices=['bloc', 'list'], required=True)
    ap.add_argument('--draws', type=int, default=1000)
    ap.add_argument('--tune', type=int, default=1000)
    ap.add_argument('--chains', type=int, default=4)
    ap.add_argument('--keep', type=int, default=400, help='posterior draws kept per stratum')
    ap.add_argument('--strata', nargs='*', default=STRATA)
    args = ap.parse_args()
    rows, strata, cats22, cats26 = read_units(args.level)
    out = {'level': args.level, 'rows': cats22, 'cols': cats26,
           'model': 'stratified Dirichlet-multinomial transition model (NumPyro NUTS)', 'settings': vars(args), 'strata': []}
    for i, name in enumerate(args.strata):
        subset = [r for r in rows if strata[r['settlement_code'], r['stat11']] == name]
        t0 = time.time()
        samples, totals, diag = fit_converged(subset, cats22, cats26, args, seed=2026 + i)
        diag['seconds'] = round(time.time() - t0)
        print(args.level, name, json.dumps(diag), flush=True)
        out['strata'].append({'name': name, 'diagnostics': diag, 'group_totals_2022': totals.round().tolist(),
                              'samples': np.round(samples, 5).tolist()})
    path = OUT / f'flows_bayes_{args.level}.json'
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print('wrote', path.relative_to(ROOT))


if __name__ == '__main__':
    main()
