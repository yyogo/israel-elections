#!/usr/bin/env python3
"""Assign each ballot box to a CBS statistical area (offline step, needs GIS packages).

Requires: pyogrio, shapely (see scripts/geo/requirements.txt). The output CSV is committed,
so the regular pipeline and CI stay standard-library only.

2026: official CEC files give every ballot box its polling place, and every polling place
      ITM coordinates (EPSG:2039, same as the CBS boundaries). Point-in-polygon.
2022: ballot -> polling-place name (CEC 2022 venue list), matched by locality and normalised
      name to a 2026 polling place with coordinates; then the same point-in-polygon.

A polling place is a proxy for where its voters live: voters are assigned to a nearby
station, but a station can serve neighbouring statistical areas.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyogrio
import shapely
from shapely import STRtree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xlsx import read_xlsx  # noqa: E402

GEO = ROOT / 'data/raw/geo'
OUT = ROOT / 'data/derived/geo'
MAX_NEAREST_M = 1500  # snap to a same-locality area only if the point is this close


def num_key(x):
    """Normalise ballot numbers: 576.1, '576.1', '576.10' -> '576.1'; 3.0 -> '3'."""
    s = str(x).strip()
    try:
        f = float(s)
    except ValueError:
        return s
    return str(int(f)) if f.is_integer() else ('%g' % f)


def norm_venue(s):
    s = (s or '').replace('"', '').replace('״', '').replace("'", '').replace('׳', '')
    s = re.sub(r'[\-–,.()]', ' ', s)
    s = re.sub(r'\bבית ספר\b', 'ביס', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


GENERIC = {'ביס', 'ביה', 'בית', 'ספר', 'מבנה', 'כניסה', 'אגף', 'צפונית', 'דרומית', 'מזרחית', 'מערבית', 'צפוני',
           'דרומי', 'מזרחי', 'מערבי', 'ראשי', 'מרכזי', 'חדש', 'ישן', 'עש', 'את', 'של'}


def tokens(s):
    # Single letters stay: they tell apart "עירוני ג" and "עירוני ה".
    return {t for t in norm_venue(s).split() if t not in GENERIC}


def fuzzy_match(venue, candidates):
    """Best same-locality polling place by token overlap; None when ambiguous or weak."""
    want = tokens(venue)
    if not want:
        return None
    scored = sorted(((len(want & tokens(v)) / len(want | tokens(v)), k) for k, v in candidates.items()), reverse=True)
    if not scored or scored[0][0] < 0.6 or (len(scored) > 1 and scored[1][0] == scored[0][0]):
        return None
    return candidates[scored[0][1]]


def load_areas():
    info, _, wkb, fields = pyogrio.raw.read(GEO / 'statisticalareas_demography2019.gdb',
                                            columns=['SEMEL_YISHUV', 'STAT11'])
    geoms = shapely.from_wkb(wkb)
    keys = [(int(a), int(b) if b == b else None) for a, b in zip(fields[0], fields[1])]
    return geoms, keys


def load_places():
    rows = read_xlsx(GEO / 'cec-2026-polling-places.xlsx')['רשימת ריכוזים']
    places = {}
    for r in rows[1:]:
        if not r or not isinstance(r[4], float):
            continue
        x, y = r[14], r[15]
        places[(int(r[4]), int(r[8]))] = {'venue': (r[11] or '').strip(), 'address': (r[10] or '').strip(),
                                          'xy': (x, y) if isinstance(x, float) and x > 0 else None}
    return places


def locate(points, settlements, geoms, keys):
    """Return (locality, stat11, method) per point."""
    tree = STRtree(geoms)
    by_locality = defaultdict(list)
    for i, (loc, _) in enumerate(keys):
        by_locality[loc].append(i)
    out = []
    for xy, settlement in zip(points, settlements):
        if xy is None:
            out.append((None, None, 'no_coordinates'))
            continue
        p = shapely.Point(xy)
        hits = [i for i in tree.query(p, predicate='intersects')]
        same = [i for i in hits if keys[i][0] == settlement]
        if same:
            out.append((*keys[same[0]], 'inside'))
        elif by_locality.get(settlement):
            cand = by_locality[settlement]
            d, i = min((shapely.distance(p, geoms[i]), i) for i in cand)
            out.append((*keys[i], 'nearest_same_locality') if d <= MAX_NEAREST_M else (None, None, 'outside_locality'))
        else:
            # Localities without statistical areas fall back to the locality cluster downstream.
            out.append((None, None, 'locality_has_no_areas'))
    return out


def main():
    geoms, keys = load_areas()
    places = load_places()
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- 2026: official station list -> polling place -> coordinates
    stations = read_xlsx(GEO / 'cec-2026-ballot-boxes.xlsx')['קובץ קלפיות']
    rows26 = []
    for r in stations[1:]:
        if not r or not isinstance(r[3], float):
            continue
        place = places.get((int(r[3]), int(r[6])), {})
        rows26.append({'settlement_code': int(r[3]), 'ballot_number': num_key(r[5]), 'polling_place': int(r[6]),
                       'venue': place.get('venue', ''), 'matched_venue': place.get('venue', ''), 'address': place.get('address', ''), 'xy': place.get('xy'),
                       'source': 'cec_2026_station'})

    # ---- 2022: venue names per ballot -> 2026 polling place with the same name in the same locality
    venues22 = json.loads((GEO / 'ballot-venues-2022.json').read_text(encoding='utf-8'))['ballot_to_location']
    venue_index = defaultdict(dict)
    for (settlement, pid), p in places.items():
        if p['xy']:
            venue_index[settlement].setdefault(norm_venue(p['venue']), (pid, p))
    ballot26 = {(r['settlement_code'], r['ballot_number']): r for r in rows26}
    rows22 = []
    for key, venue in venues22.items():
        settlement, ballot = key.split(':', 1)
        settlement, ballot = int(settlement), num_key(ballot)
        match = venue_index[settlement].get(norm_venue(venue))
        source = 'venue_name_match'
        if not match:
            names = {name: name for name in venue_index[settlement]}
            best = fuzzy_match(venue, names)
            if best is not None:
                match = venue_index[settlement][best]
                source = 'venue_fuzzy_match'
        pid, p = match if match else (None, {'xy': None, 'address': ''})
        rows22.append({'settlement_code': settlement, 'ballot_number': ballot, 'polling_place': pid or '',
                       'venue': venue, 'matched_venue': p.get('venue', ''), 'address': p.get('address', ''), 'xy': p['xy'], 'source': source if match else 'unmatched'})

    for year, rows in ((2022, rows22), (2026, rows26)):
        located = locate([r['xy'] for r in rows], [r['settlement_code'] for r in rows], geoms, keys)
        with (OUT / f'ballot_areas_{year}.csv').open('w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['year', 'settlement_code', 'ballot_number', 'polling_place', 'venue', 'matched_venue_2026', 'address', 'x_itm', 'y_itm',
                        'location_source', 'area_locality', 'stat11', 'area_method'])
            for r, (loc, sa, method) in zip(rows, located):
                x, y = r['xy'] or ('', '')
                w.writerow([year, r['settlement_code'], r['ballot_number'], r['polling_place'], r['venue'], r['matched_venue'], r['address'],
                            x, y, r['source'], loc or '', sa if sa is not None else '', method])
        print(year, len(rows), dict(Counter(m for *_, m in located)), dict(Counter(r['source'] for r in rows)))


if __name__ == '__main__':
    main()
