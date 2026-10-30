#!/usr/bin/env python3
"""Build a self-contained dashboard from editable source and derived data."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def main():
 src=ROOT/'src';data=ROOT/'data/derived/dashboard-data.json'
 if not data.exists():raise SystemExit('Run python3 scripts/analyze.py first.')
 json.loads(data.read_text())
 app=(src/'dashboard.js').read_text().replace('__DATA__',data.read_text())
 lib=(ROOT/'vendor/echarts-5.6.0.min.js').read_text().replace('</script','<\\/script')
 html=(src/'index.template.html').read_text().replace('__STYLE__',(src/'dashboard.css').read_text()).replace('__APP__',app).replace('__ECHARTS__',lib)
 assert '__DATA__' not in html and '__ECHARTS__' not in html and '__APP__' not in html and '__STYLE__' not in html
 output=ROOT/'dist/index.html';output.parent.mkdir(exist_ok=True);output.write_text(html,encoding='utf-8')
 print('Built dist/index.html SHA256='+hashlib.sha256(output.read_bytes()).hexdigest())
if __name__=='__main__':main()
