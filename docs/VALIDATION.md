# Verification at handoff

## Data controls

| Check | 2022 | 2026 |
|---|---:|---:|
| Raw ballot rows | 12,545 | 12,926 |
| Settlement codes including external envelopes | 1,216 | 1,225 |
| List columns | 40 | 38 |
| Valid votes | 4,764,742 | 5,690,682 |
| Unassigned settlement codes | 35 | 41 |
| Unassigned settlement valid votes | 20,466 | 43,003 |
| External-envelope valid votes | 458,714 | 449,357 |
| Cluster-10 valid votes | 4,004 | 4,551 |

Every raw ballot row passes party-sum and valid/invalid accounting checks. The
2022 ballot aggregates match the independent settlement export for every list
and valid-vote total; eligible, voter and invalid national control differences are zero.
Both years' elected-list cluster totals match the independently retained prior CSV controls.
The complete pipeline emits auditable counts into `data/derived/*/audit.json`.

## Pipeline rewrite (repository import)

`scripts/analyze.py` was rewritten for readability. Run against the same raw inputs,
it regenerates every per-year derived CSV, `audit.json`, `audit_summary.json` and
`settlement_presence_and_totals_comparison.csv` byte-for-byte identical to the delivered
takeout. The only intended change is `party_mapping.csv`, which now names five notable
non-elected lists (2022: Meretz, Balad, Jewish Home; 2026: The Reservists & Economic
Party, Amcha Yisrael) and uses the bloc ids from `src/parties.json`.

`SHA256SUMS` now covers only the immutable inputs: raw exports, the prior cluster
controls and vendored ECharts. Derived files and `dist/` are rebuilt, not pinned.

## Vote-flow model

`scripts/flows.py` reports a weighted R² of 0.91 (bloc level) and 0.86 (list level)
over 1,215 localities present in both elections, with 60 bootstrap replicates for
90% intervals. Raked flows reproduce the official national totals of both years exactly.

## Browser checks

`tests/browser-smoke.cjs` loads the built page with all network requests blocked and
checks: RTL Hebrew and LTR English modes, cluster chart rendering, hover banner and
nationwide reference (Likud 20.52% in 2026), bloc pinning, the 2022/2026 switch, the
nationwide group, the Sankey at bloc and list levels, the locality scatter, and
locality search at phone width. No page errors are allowed.

## Not established by these checks

- Official 2026 certification/finality or exact source download timestamp.
- Complete list names and party identity crosswalks for all minor/changed lists.
- Settlement boundary changes or residential assignment of external-envelope votes.
- Ballot-to-statistical-area assignment or individual voter socioeconomic status.
- Permanent availability or copyright clearance of remote party-logo hosts.
