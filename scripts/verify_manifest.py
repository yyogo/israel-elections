#!/usr/bin/env python3
"""Check the immutable inputs (raw exports, prior controls, vendored ECharts) against SHA256SUMS."""
from pathlib import Path
import hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 errors=[];count=0
 for line in (ROOT/'SHA256SUMS').read_text().splitlines():
  digest,name=line.split('  ',1);p=ROOT/name
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:errors.append(name)
  count+=1
 if errors:print('MISMATCH: '+', '.join(errors));sys.exit(1)
 print(f'Verified {count} files against SHA256SUMS.')
if __name__=='__main__':main()
