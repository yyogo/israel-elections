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

## Dashboard source proof

The extracted source plus regenerated `dashboard-data.json` builds the delivered
`dist/index.html` byte-for-byte. Its SHA-256 is:

`6bff4e0d1cb0abfc65195b6e32739cebabac4607e839742ea6d620244210ce46`

The exact delivered HTML was checked in headless Chrome at desktop, 320, 390 and
768 pixel widths during the dashboard work: offline library loading, cluster selection,
party/bloc highlighting, expanded pie, no hover tooltips, and national reference counts.
The final mobile-spacing change was additionally checked at 320 and 390 pixels:
all adjacent rows touch except for the 12-pixel gaps before cluster 1 and cluster 10;
axis labels do not overlap and selecting cluster 10 updates the pie.

The bundled optional browser smoke test can be rerun with Playwright. It is not
needed to rebuild data or HTML. It requires installing a browser on the new machine.

## Not established by these checks

- Official 2026 certification/finality or exact source download timestamp.
- Complete list names and party identity crosswalks for all minor/changed lists.
- Settlement boundary changes or residential assignment of external-envelope votes.
- Ballot-to-statistical-area assignment or individual voter socioeconomic status.
- Permanent availability or copyright clearance of remote party-logo hosts.

## Portable takeout rebuild

The completed source ZIP was extracted to a separate location. From a working
directory outside that project, `verify_manifest.py`, `analyze.py`,
`build_dashboard.py`, `package_site.py`, and `verify_manifest.py` all passed in sequence.
The complete unmodified rebuild preserved every delivered file checksum, including
the deterministic deployment ZIP. This verifies relocation and rebuild on the current
machine; a different operating system/Python installation has not been tested here.
