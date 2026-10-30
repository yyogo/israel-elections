"""Minimal standard-library reader for .xlsx worksheets (values only)."""
import re
import zipfile
import xml.etree.ElementTree as ET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'


def _col(ref):
    n = 0
    for ch in re.match(r'[A-Z]+', ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_xlsx(path):
    """Return {sheet name: list of rows}, each row a list of str/float/None."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
                shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
        book = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        target = {r.get('Id'): r.get('Target') for r in rels}
        sheets = {}
        for s in book.find('m:sheets', NS):
            path_in_zip = 'xl/' + target[s.get(REL)].lstrip('/').removeprefix('xl/')
            rows = []
            for row in ET.fromstring(z.read(path_in_zip)).iter('{%s}row' % NS['m']):
                values = {}
                for c in row.findall('m:c', NS):
                    v = c.find('m:v', NS)
                    kind = c.get('t')
                    if kind == 'inlineStr':
                        val = ''.join(t.text or '' for t in c.iter('{%s}t' % NS['m']))
                    elif v is None:
                        val = None
                    elif kind == 's':
                        val = shared[int(v.text)]
                    elif kind in ('str', 'e'):
                        val = v.text
                    else:
                        val = float(v.text)
                    values[_col(c.get('r'))] = val
                rows.append([values.get(i) for i in range(max(values) + 1)] if values else [])
            sheets[s.get('name')] = rows
        return sheets
