# Handoff for the next analyst or coding agent

## Current state

The latest shipped dashboard is `dist/index.html`. Its source is split into
`src/index.template.html`, `src/dashboard.css`, and `src/dashboard.js`.
`src/parties-2026.json` contains chart names, ballot letters, display colors,
bloc labels, and remote logo URLs. Edit it when changing dashboard metadata;
the analysis script also contains explicit year-specific elected-list mappings.
ECharts is vendored; there is no bundler and no build-time download.

The source and analysis pipeline rebuild the shipped HTML **byte for byte**.
See the manifest and `docs/VALIDATION.md` for the delivered proof and checks.

## Authoritative inputs and denominators

Use `data/raw/` as the source evidence. Everything under `data/derived/` is
rebuildable. Keep the raw inputs unchanged. Keep the election-year key on every
party table and join. The 2022 settlement export independently validates its
ballot-box aggregate; 2026 has no separately supplied settlement export.

The standard denominator is **all valid votes**. Do not silently renormalize to
only elected lists. The chart's residual category is all non-elected lists,
not missing votes. Invalid votes are available in normalized source tables.

Settlement code 9999 is external envelopes, not a settlement. Unmatched LMS
settlements and external envelopes must remain distinct in analysis. The UI
allows combining them as a presentation option; this does not change source data.

## Important historical mapping changes

- `פה`: Yesh Atid in 2022; a different, small list in the 2026 export.
- `אמת`: Labor in 2022; The Democrats in 2026.
- `ט`: a combined Religious Zionism–Otzma Yehudit list in 2022; Religious
  Zionism–Zehut in 2026. Otzma Yehudit is `ב` in 2026.
- `כן`: National Unity in 2022; do not assume the same list identity in 2026.
- `ום` (2022) and `ודם` (2026) represent differently composed Arab lists.
- Joint lists, mergers and withdrawals prevent a naive letter-based vote swing.

The current bloc categories are presentation groupings, not a prediction about
a future coalition. They are not a ready-made cross-election party crosswalk.

## Latest accepted interface behavior

- Hebrew and RTL; parties grouped into selectable blocs.
- Desktop: proportional-width stacked columns with a linked small ECharts
  doughnut beside them. Expand opens a larger breakdown below.
- Phone: transposed stacked rows; thickness represents valid-vote totals.
  Rows touch except for deliberate gaps before 1 and between 9 and 10.
- Hover highlights a party across clusters; clicks pin parties or blocs.
- Cluster axis labels, cluster buttons and the selector change the group.
- No hover popup. A dashed line shows the hovered/selected party or bloc's
  national share and total vote count. Side-panel percentages retain group denominators.
- Unassigned settlements and external envelopes precede cluster 1 and have no
  socioeconomic ranking. Cluster 10 remains proportional, even when very small.

## Useful next analysis paths

These are suggestions, not completed analyses:

- Separate within-settlement from between-settlement change across elections.
- Compare eligible voters, turnout and invalid votes using defensible denominators;
  external-envelope votes and ballots cast away from residence need special handling.
- Build a reviewed party/list crosswalk before interpreting vote transfer or swings.
- Add settlement search and drill-down using normalized ballot and settlement tables.
- Obtain a ballot-to-statistical-area mapping plus CBS statistical-area clusters
  for a finer analysis within large cities. The present files cannot provide it.
- Obtain official snapshot timestamps/certification documents and a complete party
  register if publishing claims beyond the supplied exports.

## External services and secrets

No Site was created: the Sites backend reported that it is not enabled for the
selected workspace. There are no Site IDs, hosting credentials or runtime secrets
in this takeout. Deploy the static bundle through another host if desired.
Logos still load from polimeter.co.il; they are not offline assets or a verified
permanent asset archive. Names and ballot letters remain available without them.
