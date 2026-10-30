# Geographic inputs (ballot box → statistical area)

| File | What | Source |
| --- | --- | --- |
| `cbs-2021-socioeconomic-statistical-areas.xlsx` | Table C: socioeconomic index 2021 (value, rank, cluster) for 1,641 statistical areas in 81 divided municipalities | CBS, publication 24/230, https://www.cbs.gov.il/he/mediarelease/DocLib/2024/230/24_24_230t4.xlsx |
| `cec-2026-ballot-boxes.xlsx` | 26th Knesset ballot-box list: ballot id, locality, ballot number, polling place (רכוז), address | Central Elections Committee ("קובץ קלפיות") |
| `cec-2026-polling-places.xlsx` | 26th Knesset polling places with ITM coordinates (EPSG:2039) | Central Elections Committee ("רשימת ריכוזים") |
| `statisticalareas_demography2019.gdb` | CBS statistical-area boundaries (2011 codes, `STAT11`) with 2019 demography | CBS GIS |
| `ballot-venues-2022.json` | 25th Knesset ballot → polling-place name, as published by the CEC | Compiled by Harel Cain, https://github.com/harelc/elections-vote-transfer (CC BY-NC-SA 4.0) |

The two CEC files, the boundaries and the 2022 venue list were taken from a copy kept in
harelc/elections-vote-transfer (repository state of 2026-10-30), because cbs.gov.il and the
CEC site refuse automated downloads from outside Israel. The CBS table was downloaded by hand.

`ballot-venues-2022.json` and everything derived from it (`data/derived/geo/ballot_areas_2022.csv`
and the 2022 neighbourhood tables) are third-party compilations licensed **CC BY-NC-SA 4.0**:
attribute Harel Cain, non-commercial use only, and share adaptations under the same licence.

`scripts/geo/build_ballot_areas.py` (needs `pyogrio` and `shapely`) turns these into
`data/derived/geo/ballot_areas_<year>.csv`. That output is committed so the regular pipeline
stays standard-library only.
