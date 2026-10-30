# Israel election analysis — source takeout

This is a portable source and data handoff, not just a website upload bundle.
It includes the 2022 and 2026 raw election files, the supplied LMS/CBS 2021
settlement clusters, analysis tables for **all** lists, and the latest Hebrew dashboard.

## Start here

- **Another analyst or coding agent:** read `HANDOFF.md`, then `docs/METHODOLOGY.md`.
- **Open the dashboard immediately:** open `dist/index.html` in a browser.
- **Deploy immediately:** upload the contents of `dist/deployable-site.zip` to a static web host.
- **Analyze:** start with `data/derived/<year>/settlements_long.csv` and `party_mapping.csv`.
- **Work at ballot-box level:** use `data/derived/<year>/ballots_wide.csv` or the original CSVs.

## Rebuild on another machine

Python 3.10+ is sufficient. The pipeline uses only the standard library: no pip
packages, Node.js, server, credentials, or network are required.

```sh
python3 scripts/verify_manifest.py
python3 scripts/analyze.py
python3 scripts/build_dashboard.py
python3 scripts/package_site.py
```

The scripts find the project root relative to themselves, so these commands do
not depend on the current working directory. The rebuild regenerates both years'
normalized and aggregated data, then the latest 2026 dashboard and deployment ZIP.
`SHA256SUMS` is the delivery baseline; it is not automatically rewritten after edits.

For a local HTTP preview, from this directory:

```sh
python3 -m http.server 8000 --directory dist
```

Visit http://localhost:8000/. Party logos are remote images; chart data and
Apache ECharts 5.6.0 are embedded, so the charts work offline.

## Contents

```text
data/raw/2022/             Original expb.csv and expc.csv, byte-for-byte copies
data/raw/2026/             Original expb (1).csv, byte-for-byte copy
data/raw/lms-2021/         Original settlementSCS.csv, byte-for-byte copy
data/derived/2022/         Ballots, settlements, clusters, unmatched rows, audit
data/derived/2026/         Same products for 2026
data/derived/              Cross-year presence table, party mapping, dashboard data
src/                      Editable HTML template, CSS, JS, 2026 party metadata
vendor/                   Pinned ECharts distribution, with embedded license headers
scripts/                  Portable analysis, dashboard build, packaging, hash verification
tests/                    Optional browser smoke test
archive/reports/          Earlier 2022/2026 chart reports and independent cluster controls
docs/                     Method, schemas, deployment, validation and provenance
licenses/                 Apache 2.0 and upstream ECharts NOTICE
dist/                     Latest self-contained dashboard and static deployment ZIP
```

## Scope and limits

The supplied older election CSVs are from **2022**, despite the initial 2026
request. The newer ballot-box export is treated as the **2026 supplied snapshot**.
No 2026 settlement-level source export was supplied; its settlement table is
aggregated from ballots. No election data before 2022 were supplied.

A single 2021 cluster is assigned to an entire settlement, including all its
ballot boxes. This is not a statistical-area or voter-income analysis. External
envelopes have no settlement assignment. Ballot letters and list membership
change between elections: **join party identities on year + ballot_code**.

Non-elected lists are fully preserved in the tables, but their names and bloc
identities were not comprehensively mapped. Blank names are deliberate.

For optional browser checks, see `tests/README.md`. Python rebuild and hash verification
were exercised after extracting the archive to another directory. No different-machine
or cross-operating-system run is claimed.
