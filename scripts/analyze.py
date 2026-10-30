#!/usr/bin/env python3
"""Rebuild the analysis tables from the immutable CSV inputs.

Python 3.10+, standard library only. Run from anywhere; paths are resolved
relative to the repository root.
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/derived'
RAW = {2022: ROOT / 'data/raw/2022/expb.csv', 2026: ROOT / 'data/raw/2026/expb (1).csv'}
YEARS = [2022, 2026]
# Columns that follow the valid-vote column but are not lists.
META_COLUMNS = {'חיצוניות', 'קלפי אחרת'}
EXPECTED_VALID = {2022: 4764742, 2026: 5690682}
EXPECTED_LIST_COLUMNS = {2022: 40, 2026: 38}
EXTERNAL = 9999
GROUP_ORDER = [str(i) for i in range(1, 11)] + ['Unassigned settlements', 'External envelopes']
CONTROLS = ['בזב', 'מצביעים', 'פסולים', 'כשרים']
CONTROLS_EN = ['eligible', 'voters', 'invalid', 'valid']


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def num(x):
    s = str(x or '').replace(',', '').strip()
    if not s:
        return 0
    v = float(s)
    if not math.isfinite(v) or not v.is_integer():
        raise ValueError(f'Non-integer count: {x!r}')
    return int(v)


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load_parties():
    return json.loads((ROOT / 'src/parties.json').read_text(encoding='utf-8'))


def load_clusters():
    """LMS 2021 settlement clusters keyed by numeric settlement code."""
    _, rows = read(ROOT / 'data/raw/lms-2021/settlementSCS.csv')
    lookup = {}
    for r in rows:
        if not r['סמל היישוב'].strip():
            continue
        code = num(r['סמל היישוב'])
        cluster = num(r['אשכול 2021'])
        if code in lookup:
            raise ValueError(f'Duplicate LMS code {code}')
        assert cluster in range(1, 11)
        lookup[code] = (cluster, r['שם יישוב'])
    return lookup


def classify(code, lookup):
    """Return (cluster or None, assignment status, group label) for a settlement code."""
    if code == EXTERNAL:
        return None, 'external_envelopes', 'External envelopes'
    cluster = lookup.get(code, (None, None))[0]
    if cluster:
        return cluster, 'assigned', str(cluster)
    return None, 'unassigned_settlement', 'Unassigned settlements'


def analyze(year, lookup, parties):
    folder = OUT / str(year)
    folder.mkdir(parents=True, exist_ok=True)
    headers, rows = read(RAW[year])
    start = headers.index('כשרים') + 1
    codes = [h for h in headers[start:] if h and h not in META_COLUMNS and not h.startswith('Unnamed:')]
    assert len(codes) == EXPECTED_LIST_COLUMNS[year]

    # values[settlement] = [eligible, voters, invalid, valid, *list votes]
    values = defaultdict(lambda: [0] * (4 + len(codes)))
    names, ballots = {}, []
    for r in rows:
        code = num(r['סמל ישוב'])
        names[code] = r['שם ישוב']
        counts = [num(r[h]) for h in CONTROLS + codes]
        assert sum(counts[4:]) == counts[3], ('party sum', year, r['ברזל'])
        assert counts[1] == counts[2] + counts[3], ('ballot accounting', year, r['ברזל'])
        assert all(c >= 0 for c in counts)
        for i, v in enumerate(counts):
            values[code][i] += v
        cluster, status, _ = classify(code, lookup)
        ballots.append(dict(year=year, settlement_code=code, settlement_name_he=names[code],
                            ballot_id=r['ברזל'], ballot_number=r['קלפי'], cluster=cluster or '',
                            assignment_status=status, **dict(zip(CONTROLS_EN + codes, counts))))
    assert sum(v[3] for v in values.values()) == EXPECTED_VALID[year]

    audit = {'year': year, 'ballot_rows': len(rows), 'settlement_rows_including_external': len(values),
             'party_columns': len(codes), 'valid_votes': EXPECTED_VALID[year],
             'ballot_party_totals_reconcile': True, 'voters_equal_valid_plus_invalid': True}

    if year == 2022:
        # 2022 also ships a settlement-level export: it must equal our ballot aggregate.
        _, source = read(ROOT / 'data/raw/2022/expc.csv')
        assert len(source) == len(values)
        for r in source:
            code = num(r['סמל ישוב'])
            assert code in values
            assert [num(r[k]) for k in ['כשרים'] + codes] == [values[code][3]] + values[code][4:], ('settlement control', code)
        audit['matches_supplied_settlement_export_for_all_parties_and_valid_votes'] = True
        audit['settlement_export_control_differences'] = {
            k: sum(num(r[k]) for r in source) - sum(v[i] for v in values.values()) for i, k in enumerate(CONTROLS)}

    grouped = {g: [0] * len(codes) for g in GROUP_ORDER}
    controls = {g: [0] * 4 for g in GROUP_ORDER}
    totals = {g: 0 for g in GROUP_ORDER}
    settlements, long = [], []
    for code, v in sorted(values.items()):
        cluster, status, group = classify(code, lookup)
        settlements.append(dict(year=year, settlement_code=code, settlement_name_he=names[code], cluster=cluster or '',
                                assignment_status=status, group=group, **dict(zip(CONTROLS_EN + codes, v))))
        totals[group] += v[3]
        for i in range(4):
            controls[group][i] += v[i]
        for i, c in enumerate(codes):
            grouped[group][i] += v[4 + i]
            long.append(dict(year=year, settlement_code=code, settlement_name_he=names[code], cluster=cluster or '',
                             assignment_status=status, ballot_code=c, votes=v[4 + i]))

    valid = EXPECTED_VALID[year]
    cluster_rows = [dict(year=year, group=g, valid=totals[g], share_of_all_valid_votes=totals[g] / valid,
                         **dict(zip(codes, grouped[g]))) for g in GROUP_ORDER]
    cluster_long = [dict(year=year, group=g, valid=totals[g], share_of_all_valid_votes=totals[g] / valid, ballot_code=c,
                         votes=grouped[g][i], share_within_group=grouped[g][i] / totals[g])
                    for g in GROUP_ORDER for i, c in enumerate(codes)]
    unassigned = [r for r in settlements if r['assignment_status'] == 'unassigned_settlement']
    write(folder / 'ballots_wide.csv', ballots)
    write(folder / 'settlements_wide.csv', settlements)
    write(folder / 'settlements_long.csv', long)
    write(folder / 'clusters_wide.csv', cluster_rows)
    write(folder / 'clusters_long.csv', cluster_long)
    with (folder / 'unassigned_settlements.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(settlements[0]))
        w.writeheader()
        w.writerows(unassigned)

    audit.update(unassigned_settlements=len(unassigned), unassigned_votes=totals['Unassigned settlements'],
                 external_envelope_votes=totals['External envelopes'], cluster_10_valid=totals['10'],
                 cluster_10_settlements=[{'code': r['settlement_code'], 'name_he': r['settlement_name_he'], 'valid': r['valid']}
                                         for r in settlements if r['cluster'] == 10])

    # Independent controls exported during the original chart work.
    _, prior = read(ROOT / f'archive/reports/{year}_votes_by_cluster.csv')
    elected = [p for p in parties['years'][str(year)]['parties'] if p['elected']]
    legacy_names = {(2022, 'ט'): 'Religious Zionism', (2026, 'דרך'): 'Yashar', (2026, 'ודם'): 'Joint List'}
    for r in prior:
        group = r['group']
        assert num(r['valid_votes']) == totals[group]
        for p in elected:
            name = legacy_names.get((year, p['code']), p['en'])
            assert num(r[name + ' votes']) == grouped[group][codes.index(p['code'])], (year, group, name)
    audit['matches_previous_cluster_controls'] = True
    dump(folder / 'audit.json', audit)
    return {'year': year, 'codes': codes, 'groups': grouped, 'controls': controls, 'totals': totals,
            'settlements': settlements, 'ballots': ballots, 'audit': audit}


def ballot_key(number):
    """Ballot numbers as written in the crosswalk: '3', '576.1'."""
    f = float(number)
    return str(int(f)) if f.is_integer() else '%g' % f


def load_area_clusters():
    """CBS 2021 clusters per statistical area: {(locality, stat11): cluster}."""
    from xlsx import read_xlsx
    rows = read_xlsx(ROOT / 'data/raw/geo/cbs-2021-socioeconomic-statistical-areas.xlsx')['לוח ג table C']
    clusters = {}
    for r in rows:
        if r and len(r) > 10 and all(isinstance(r[i], float) for i in (0, 1, 6, 10)):
            clusters[int(r[1]), int(r[6])] = int(r[10])
    assert len(clusters) == 1641
    return clusters


def analyze_areas(result, lookup, area_clusters):
    """Neighbourhood-level clusters: a ballot box takes its statistical area's cluster when
    the locality is divided into clustered areas and the box was located; otherwise it keeps
    the locality cluster. Writes per-year assignment, group and area tables."""
    year, codes = result['year'], result['codes']
    path = OUT / 'geo' / f'ballot_areas_{year}.csv'
    with path.open(encoding='utf-8', newline='') as f:
        located = {(int(r['settlement_code']), r['ballot_number']): r for r in csv.DictReader(f)}
    divided = {loc for loc, _ in area_clusters}
    grouped = {g: [0] * (4 + len(codes)) for g in GROUP_ORDER}
    areas, assignments = defaultdict(lambda: [0] * (4 + len(codes))), []
    basis_votes = defaultdict(int)
    for b in result['ballots']:
        code = b['settlement_code']
        cluster, status, group = classify(code, lookup)
        row = located.get((code, ballot_key(b['ballot_number'])))
        stat11 = int(row['stat11']) if row and row['stat11'] and int(row['area_locality']) == code else None
        basis = 'locality'
        if code in divided:
            if stat11 is not None and (code, stat11) in area_clusters:
                cluster, basis = area_clusters[code, stat11], 'statistical_area'
                group = str(cluster)
            else:
                basis = 'locality_fallback'
        counts = [b[k] for k in CONTROLS_EN + codes]
        for i, v in enumerate(counts):
            grouped[group][i] += v
            areas[code, stat11 if code in divided else None][i] += v
        basis_votes[basis] += b['valid']
        assignments.append(dict(year=year, settlement_code=code, ballot_number=b['ballot_number'], stat11=stat11 if stat11 is not None else '',
                                area_cluster=cluster or '', basis=basis, location_source=row['location_source'] if row else 'not_in_crosswalk'))
    folder = OUT / str(year)
    write(folder / 'ballot_area_assignment.csv', assignments)
    write(folder / 'area_clusters_wide.csv', [dict(year=year, group=g, **dict(zip(CONTROLS_EN + codes, v))) for g, v in grouped.items()])
    write(folder / 'areas_wide.csv', [dict(year=year, settlement_code=loc, stat11=sa if sa is not None else '',
                                           area_cluster=area_clusters.get((loc, sa), ''), **dict(zip(CONTROLS_EN + codes, v)))
                                      for (loc, sa), v in sorted(areas.items(), key=lambda kv: (kv[0][0], kv[0][1] or -1))])
    assert sum(v[3] for v in grouped.values()) == EXPECTED_VALID[year]
    result['audit']['area_basis_valid_votes'] = dict(sorted(basis_votes.items()))
    dump(folder / 'audit.json', result['audit'])


def write_party_mapping(results, parties):
    rows = []
    for year, result in results.items():
        known = {p['code']: p for p in parties['years'][str(year)]['parties']}
        for code in result['codes']:
            p = known.get(code)
            status = 'not_mapped_retained_as_ballot_code'
            if p:
                status = 'mapped_elected_list' if p['elected'] else 'mapped_notable_list'
            rows.append(dict(year=year, ballot_code=code, name_he=p['he'] if p else '', name_en=p['en'] if p else '',
                             bloc=p['bloc'] if p else 'other_lists', elected=int(bool(p and p['elected'])),
                             name_status=status))
    write(OUT / 'party_mapping.csv', rows)


def write_presence_comparison(results):
    a = {x['settlement_code']: x for x in results[2022]['settlements']}
    b = {x['settlement_code']: x for x in results[2026]['settlements']}
    rows = []
    for code in sorted(set(a) | set(b)):
        x, y = a.get(code), b.get(code)
        rows.append(dict(settlement_code=code, name_2022=x['settlement_name_he'] if x else '',
                         name_2026=y['settlement_name_he'] if y else '', present_2022=int(x is not None),
                         present_2026=int(y is not None), valid_2022=x['valid'] if x else '',
                         valid_2026=y['valid'] if y else '', cluster_2021=(y or x)['cluster']))
    write(OUT / 'settlement_presence_and_totals_comparison.csv', rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lookup = load_clusters()
    parties = load_parties()
    results = {y: analyze(y, lookup, parties) for y in YEARS}
    write_party_mapping(results, parties)
    write_presence_comparison(results)
    if (OUT / 'geo/ballot_areas_2026.csv').exists():
        area_clusters = load_area_clusters()
        for r in results.values():
            analyze_areas(r, lookup, area_clusters)
    dump(OUT / 'audit_summary.json', {'lms_settlement_rows': len(lookup), 'years': {str(y): r['audit'] for y, r in results.items()}})
    print(json.dumps({y: r['audit'] for y, r in results.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
