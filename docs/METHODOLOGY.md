# Methodology

1. Read the original CSVs as UTF-8 with optional BOM. Preserve their bytes in `data/raw/`.
2. Identify vote columns after `כשרים`, excluding `חיצוניות`, `קלפי אחרת`, and empty
   trailing headers. There are 40 list columns in 2022 and 38 in 2026.
3. Verify every ballot row: party sum = valid; valid + invalid = voters; no negative counts.
4. Aggregate all ballots by numeric settlement code. Preserve original settlement labels
   in each year. Do not use fuzzy name matching or transfer unmatched codes to another year.
5. Normalize the LMS settlement code by removing its thousands separators. Require a
   unique code and a cluster from 1 to 10. Ignore the final empty LMS row.
6. Left join settlements to LMS by numeric settlement code. Explicitly exclude code 9999
   from the settlement join. Keep unmatched settlements as unassigned.
7. Sum vote counts by cluster, unmatched settlements and external envelopes. Shares
   use the entire valid-vote total of that group, including non-elected lists.
8. For the 2022 independent control, compare every list and valid vote by settlement
   against `expc.csv`; report differences in the other source control totals.
9. Reconcile elected-list cluster counts and group totals against the separately retained
   outputs from the original chart work. These are historical controls, not source inputs.

The LMS file labels its measures and clusters as 2021. Both elections use this same
settlement-level classification. A 2026 change in vote share does not establish a change
in socioeconomic position. No official source-download timestamp is encoded in the
supplied file contents; treat 2026 as the supplied snapshot, not live data.

## Cluster 10

Exactly three LMS settlements have cluster 10: Kfar Shmaryahu (267), Savyon (587),
and Arsuf (1324). Their valid votes are 4,004 in 2022 and 4,551 in 2026. Caesarea is
cluster 9 in this LMS file. Affluent neighborhoods inside cities are assigned their
city's cluster; this explains why the highest settlement cluster is very small.

## Cross-election comparisons

`settlement_presence_and_totals_comparison.csv` is a code-presence and vote-total
comparison only. A common code does not prove unchanged boundaries or list identity.
Missing rows are left blank, not treated as zero votes. Settlement 9999 remains present
as a national external-envelope aggregate. No voter-residence reassignment is possible.

Party/list names were mapped for elected lists used in the delivered charts. All minor
lists remain in the raw and derived tables; their unmapped names are blank, with an
explicit `name_status`. Do not interpret their `other_lists` bucket as an ideological bloc.

## Neighbourhood clusters (statistical areas)

The "by neighbourhood" view replaces the locality cluster with the cluster of the CBS
statistical area (SA) in which the ballot box's polling place is located, for the 81
municipalities that CBS divides into clustered SAs (Table C of publication 24/230).

1. 2026: the CEC ballot-box list links each box to its polling place; the CEC polling-place
   list gives ITM coordinates. 2022: the CEC venue name of each box is matched to a 2026
   polling place in the same locality, exactly after normalisation (10,369 boxes) or by
   token overlap ≥ 0.6 with a unique best match (163 boxes). 2,013 boxes stay unlocated.
2. Point-in-polygon against CBS SA boundaries (2011 codes). Points outside their own
   locality are snapped to the nearest SA of that locality within 1.5 km.
3. A box takes its SA's 2021 cluster when its locality is divided and it was located;
   otherwise it keeps the locality cluster (`basis` in `ballot_area_assignment.csv`).

Coverage (valid votes): 2026 — 3.80M by SA, 12k city votes fall back to the city cluster;
2022 — 2.94M by SA, 321k fall back (mainly Bnei Brak, Jerusalem, Tel Aviv). Votes outside
the 81 municipalities (1.5–1.9M, including external envelopes) keep their locality grouping.

Caveats: a polling place stands in for its voters' homes; a station can serve neighbouring
SAs. SA and locality clusters come from separate CBS tables on the same 1–10 scale. Cluster
10 stays small (8 SAs, about 21k residents), as in the CBS table.

The flow model uses SAs as units inside the 32 localities where at least 95% of eligible
voters were located in both years (1,709 units in total, against 1,215 localities). Bloc
flows changed by at most four points against the locality-only model.

## Ballot-letter changes between elections

- `פה`: Yesh Atid in 2022; a different, small list in the 2026 export.
- `אמת`: Labor in 2022; The Democrats in 2026.
- `ט`: a combined Religious Zionism–Otzma Yehudit list in 2022; Religious
  Zionism–Zehut in 2026. Otzma Yehudit is `ב` in 2026.
- `כן`: National Unity in 2022; do not assume the same list identity in 2026.
- `ום` (2022) and `ודם` (2026) represent differently composed Arab lists.
- Joint lists, mergers and withdrawals prevent a naive letter-based vote swing.

The current bloc categories are presentation groupings, not a prediction about
a future coalition. They are not a ready-made cross-election party crosswalk.

## Estimated vote flows (2022 → 2026)

`scripts/flows.py` estimates how 2022 voters voted in 2026 by ecological inference.

1. Units: the 1,215 localities present in both elections with eligible voters (code 9999 excluded).
2. Categories: blocs (or displayed lists plus "other lists") and "did not cast a valid vote"
   (eligible − valid, so invalid ballots count as non-votes). Shares are of eligible voters.
3. Fit one transition matrix T (rows on the simplex) minimizing Σ w_s‖x_s T − y_s‖², with
   w_s the mean eligible voters of locality s, by accelerated projected gradient descent.
4. Rake diag(N₂₀₂₂)·T by iterative proportional fitting to the official national margins
   of both years (including external envelopes); the 2026 margin is scaled to the 2022 electorate.
5. Bootstrap localities (60 replicates, fixed seed) for 90% intervals on each row share.

Assumptions and limits: voters of a list behave alike across localities (no contextual
effects); register churn (new voters, deaths, moves) is folded into each locality's
electorate; locality turnout excludes external envelopes. Estimates are robust for blocs and
geographically distinctive lists, and weak for lists with overlapping voter bases. Bootstrap
intervals capture sampling variation across localities, not model misspecification.
