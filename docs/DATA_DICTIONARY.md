# Data dictionary

All derived CSVs are UTF-8 with headers. Counts are integers. Share fields are fractions
between 0 and 1, not percentage points. Blank cluster means no cluster assignment.

## Common keys

- `year`: election dataset, 2022 or 2026.
- `settlement_code`: numeric election code. Code 9999 is external envelopes.
- `settlement_name_he`: election-export label, preserved by year.
- `ballot_id`: source `ברזל`; retain with year. `ballot_number`: source `קלפי`,
  preserved as a string (including decimals). A settlement may have multiple ballot rows.
- `cluster`: LMS 2021 settlement cluster, 1–10, or blank.
- `assignment_status`: `assigned`, `unassigned_settlement`, or `external_envelopes`.
- `group`: string `1`…`10`, `Unassigned settlements`, or `External envelopes`.
- `eligible`, `voters`, `invalid`, `valid`: source counts (`בזב`, `מצביעים`, `פסולים`, `כשרים`).
  Eligible-voter and turnout calculations require care for special ballots. No turnout
  measure is asserted by this handoff pipeline.
- `ballot_code`: exact Hebrew list letters; identity key is **year + ballot_code**.
- `votes`: count for that party/list at that table's observation level.

## Per-year files

- `ballots_wide.csv`: one source ballot-box row, normalized metadata and one numeric
  column per list. Other source metadata remain available in the unchanged raw export.
- `settlements_wide.csv`: one aggregate per settlement code, including external envelopes.
- `settlements_long.csv`: one settlement/list pair, including zero-vote pairs. Join to
  `settlements_wide.csv` on year + settlement_code for group denominators and controls.
- `clusters_wide.csv`: one group, valid denominator, share of all valid votes, and list columns.
- `clusters_long.csv`: one group/list pair with counts and `share_within_group`.
- `unassigned_settlements.csv`: settlement-wide rows with no LMS match; excludes 9999.
- `audit.json`: totals, reconciliation outcomes, coverage, and cluster-10 constituent totals.

## Shared derived files

- `party_mapping.csv`: year, ballot_code, English/Hebrew mapped name, presentation bloc,
  elected flag, name_status. Minor-list names remain unmapped rather than guessed.
- `settlement_presence_and_totals_comparison.csv`: union of settlement codes, per-year
  names/presence/valid votes, and the same LMS 2021 cluster.
- `dashboard-data.json`: the exact compact 2026 data consumed by the current dashboard;
  ten numeric clusters plus unassigned settlements and external envelopes. It displays
  eleven elected lists plus a residual category. Use long CSVs for all-list analysis.
- `audit_summary.json`: combined audit summary and LMS row count.

## Raw file inventory

- `data/raw/2022/expc.csv`: 1,216 settlement aggregates, including external envelopes.
- `data/raw/2022/expb.csv`: 12,545 ballot-box rows, including external-envelope rows.
- `data/raw/2026/expb (1).csv`: 12,926 ballot-box rows, including external-envelope rows.
- `data/raw/lms-2021/settlementSCS.csv`: 1,197 nonempty settlement rows plus an empty row;
  original Hebrew columns include settlement code, name, settlement form, 2021 index
  population, index value and cluster. Preserve fractional population/index values;
  do not use these population figures as eligible-voter counts.
