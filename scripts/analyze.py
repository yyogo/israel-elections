#!/usr/bin/env python3
"""Rebuild analysis from immutable CSV inputs. Python 3.10+, standard library only."""
import csv,json,math
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'data/derived'
META={'חיצוניות','קלפי אחרת'}
EXPECTED={2022:4764742,2026:5690682}
ORDER=[str(i) for i in range(1,11)]+['Unassigned settlements','External envelopes']
def read(path):
 with path.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f); return reader.fieldnames,list(reader)
def num(x):
 s=str(x or '').replace(',','').strip()
 if not s:return 0
 v=float(s)
 if not math.isfinite(v) or not v.is_integer():raise ValueError(f'Non-integer count: {x!r}')
 return int(v)
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write(path,fields,rows):
 with path.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def load_clusters():
 _,rows=read(ROOT/'data/raw/lms-2021/settlementSCS.csv'); lookup={}
 for r in rows:
  if not r['סמל היישוב'].strip():continue
  code=num(r['סמל היישוב']);cluster=num(r['אשכול 2021'])
  if code in lookup:raise ValueError(f'Duplicate LMS code {code}')
  assert cluster in range(1,11)
  lookup[code]=(cluster,r['שם יישוב'])
 return lookup
# Only names for elected lists were established in this analysis. Preserve all other ballot codes.
P22=[('מחל','הליכוד','Likud','netanyahu'),('ט','הציונות הדתית–עוצמה יהודית','Religious Zionism–Otzma Yehudit','netanyahu'),('שס','ש״ס','Shas','netanyahu'),('ג','יהדות התורה','United Torah Judaism','netanyahu'),('פה','יש עתיד','Yesh Atid','opposition'),('כן','המחנה הממלכתי','National Unity','opposition'),('ל','ישראל ביתנו','Yisrael Beiteinu','opposition'),('אמת','העבודה','Labor','opposition'),('ום','חד״ש–תע״ל','Hadash–Ta’al','arab_lists'),('עם','רע״ם','Ra’am','arab_lists')]
P26=[('מחל','Likud'),('ב','Otzma Yehudit'),('ט','Religious Zionism–Zehut'),('שס','Shas'),('ג','United Torah Judaism'),('דרך','Yashar'),('רק','Together'),('אמת','The Democrats'),('ל','Yisrael Beiteinu'),('ודם','Joint List'),('עם','Ra’am')]

def analyze(year,lookup):
 folder=OUT/str(year);folder.mkdir(parents=True,exist_ok=True)
 file=ROOT/'data/raw'/str(year)/('expb.csv' if year==2022 else 'expb (1).csv')
 headers,rows=read(file); start=headers.index('כשרים')+1
 codes=[h for h in headers[start:] if h and h not in META and not h.startswith('Unnamed:')]
 assert len(codes)==(40 if year==2022 else 38)
 controls=['בזב','מצביעים','פסולים','כשרים'];en=['eligible','voters','invalid','valid']
 values=defaultdict(lambda:[0]*(4+len(codes)));names={};ballots=[]
 for r in rows:
  code=num(r['סמל ישוב']);names[code]=r['שם ישוב'];counts=[num(r[h]) for h in controls+codes]
  assert sum(counts[4:])==counts[3],('party sum',year,r['ברזל'])
  assert counts[1]==counts[2]+counts[3],('ballot accounting',year,r['ברזל'])
  assert all(c>=0 for c in counts)
  for i,v in enumerate(counts):values[code][i]+=v
  cluster=lookup.get(code,(None,None))[0] if code!=9999 else None
  status='external_envelopes' if code==9999 else 'assigned' if cluster else 'unassigned_settlement'
  ballots.append(dict(year=year,settlement_code=code,settlement_name_he=names[code],ballot_id=r['ברזל'],ballot_number=r['קלפי'],cluster=cluster or '',assignment_status=status,**dict(zip(en+codes,counts))))
 assert sum(v[3] for v in values.values())==EXPECTED[year]
 check={'year':year,'ballot_rows':len(rows),'settlement_rows_including_external':len(values),'party_columns':len(codes),'valid_votes':EXPECTED[year],'ballot_party_totals_reconcile':True,'voters_equal_valid_plus_invalid':True}
 if year==2022:
  _,source=read(ROOT/'data/raw/2022/expc.csv'); assert len(source)==len(values)
  for r in source:
   code=num(r['סמל ישוב']);assert code in values
   assert [num(r[k]) for k in ['כשרים']+codes]==[values[code][3]]+values[code][4:],('settlement control',code)
  check['matches_supplied_settlement_export_for_all_parties_and_valid_votes']=True
  check['settlement_export_control_differences']={k:sum(num(r[k]) for r in source)-sum(v[i] for v in values.values()) for i,k in enumerate(controls)}
 grouped={g:[0]*len(codes) for g in ORDER};totals={g:0 for g in ORDER};settlements=[];long=[]
 for code,v in sorted(values.items()):
  cluster=lookup.get(code,(None,None))[0] if code!=9999 else None
  status='external_envelopes' if code==9999 else 'assigned' if cluster else 'unassigned_settlement'
  group='External envelopes' if code==9999 else str(cluster) if cluster else 'Unassigned settlements'
  r=dict(year=year,settlement_code=code,settlement_name_he=names[code],cluster=cluster or '',assignment_status=status,group=group,**dict(zip(en+codes,v)))
  settlements.append(r);totals[group]+=v[3]
  for i,c in enumerate(codes):
   grouped[group][i]+=v[4+i]
   long.append(dict(year=year,settlement_code=code,settlement_name_he=names[code],cluster=cluster or '',assignment_status=status,ballot_code=c,votes=v[4+i]))
 cluster_rows=[dict(year=year,group=g,valid=totals[g],share_of_all_valid_votes=totals[g]/EXPECTED[year],**dict(zip(codes,grouped[g]))) for g in ORDER]
 cluster_long=[dict(year=year,group=g,valid=totals[g],share_of_all_valid_votes=totals[g]/EXPECTED[year],ballot_code=c,votes=grouped[g][i],share_within_group=grouped[g][i]/totals[g]) for g in ORDER for i,c in enumerate(codes)]
 write(folder/'ballots_wide.csv',list(ballots[0]),ballots);write(folder/'settlements_wide.csv',list(settlements[0]),settlements);write(folder/'settlements_long.csv',list(long[0]),long);write(folder/'clusters_wide.csv',list(cluster_rows[0]),cluster_rows);write(folder/'clusters_long.csv',list(cluster_long[0]),cluster_long)
 unassigned=[r for r in settlements if r['assignment_status']=='unassigned_settlement'];write(folder/'unassigned_settlements.csv',list(settlements[0]),unassigned)
 selected=next(r for r in cluster_rows if r['group']=='10')
 check.update(unassigned_settlements=len(unassigned),unassigned_votes=totals['Unassigned settlements'],external_envelope_votes=totals['External envelopes'],cluster_10_valid=selected['valid'],cluster_10_settlements=[{'code':r['settlement_code'],'name_he':r['settlement_name_he'],'valid':r['valid']} for r in settlements if r['cluster']==10])
 # Independent controls exported during the original dashboard work.
 _,prior=read(ROOT/f'archive/reports/{year}_votes_by_cluster.csv');elected=P22 if year==2022 else P26
 for r in prior:
  group=r['group'];assert num(r['valid_votes'])==totals[group]
  for p in elected:
   code=p[0];name=p[2] if year==2022 else p[1]
   # Original English dashboard shortened the joint list label.
   if year==2022 and code=='ט':name='Religious Zionism'
   assert num(r[name+' votes'])==grouped[group][codes.index(code)],(year,group,name)
 check['matches_previous_cluster_controls']=True;dump(folder/'audit.json',check)
 return {'year':year,'codes':codes,'groups':grouped,'totals':totals,'settlements':settlements,'audit':check}

def main():
 OUT.mkdir(parents=True,exist_ok=True);lookup=load_clusters();results={y:analyze(y,lookup) for y in [2022,2026]}
 metadata=json.loads((ROOT/'src/parties-2026.json').read_text());r=results[2026];groups=[]
 for g in ORDER:
  groups.append({'id':g,'name':'אשכול '+g if g.isdigit() else 'יישובים ללא אשכול' if g=='Unassigned settlements' else 'מעטפות חיצוניות','total':r['totals'][g],'votes':[r['groups'][g][r['codes'].index(code)] for code,_ in P26]+[sum(v for c,v in zip(r['codes'],r['groups'][g]) if c not in {p[0] for p in P26})]})
 (OUT/'dashboard-data.json').write_text(json.dumps({'groups':groups,'parties':metadata},ensure_ascii=False),encoding='utf-8')
 mappings=[]
 for year,result in results.items():
  known={p[0]:p for p in P22} if year==2022 else {code:(code,metadata[i]['name'],name,(['netanyahu']*5+['opposition']*4+['arab_lists']*2)[i]) for i,(code,name) in enumerate(P26)}
  for code in result['codes']:
   p=known.get(code);name_he=p[1] if p else '';name_en=p[2] if p else '';bloc=p[3] if p else 'other_lists'
   mappings.append(dict(year=year,ballot_code=code,name_he=name_he,name_en=name_en,bloc=bloc,elected=int(p is not None),name_status='mapped_elected_list' if p else 'not_mapped_retained_as_ballot_code'))
 write(OUT/'party_mapping.csv',list(mappings[0]),mappings)
 a={x['settlement_code']:x for x in results[2022]['settlements']};b={x['settlement_code']:x for x in results[2026]['settlements']};comp=[]
 for code in sorted(set(a)|set(b)):
  x=a.get(code);y=b.get(code);comp.append(dict(settlement_code=code,name_2022=x['settlement_name_he'] if x else '',name_2026=y['settlement_name_he'] if y else '',present_2022=int(x is not None),present_2026=int(y is not None),valid_2022=x['valid'] if x else '',valid_2026=y['valid'] if y else '',cluster_2021=(y or x)['cluster']))
 write(OUT/'settlement_presence_and_totals_comparison.csv',list(comp[0]),comp)
 dump(OUT/'audit_summary.json',{'lms_settlement_rows':len(lookup),'years':{str(y):r['audit'] for y,r in results.items()}})
 print(json.dumps({y:r['audit'] for y,r in results.items()},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
