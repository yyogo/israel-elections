#!/usr/bin/env python3
"""Create a static-host upload ZIP from the current dashboard build."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
def main():
 out=ROOT/'dist/deployable-site.zip'
 entries={'index.html':(ROOT/'dist/index.html').read_bytes(),'README.md':(ROOT/'docs/DEPLOY.md').read_bytes(),'.nojekyll':b''}
 for p in sorted((ROOT/'licenses').glob('*')):entries['licenses/'+p.name]=p.read_bytes()
 with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name,data in sorted(entries.items()):
   info=zipfile.ZipInfo(name,date_time=(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
   z.writestr(info,data,compresslevel=9)
 with zipfile.ZipFile(out) as z:assert z.testzip() is None
 print('Built dist/deployable-site.zip')
if __name__=='__main__':main()
