#!/usr/bin/env python3
"""
Download the images your pages need from the live WordPress site into media_src/.
Standard library only. Safe to re-run: files already in media_src/ are skipped.

    python tools/fetch_media.py          # only the files listed MISSING in media_needed.txt
    python tools/fetch_media.py --all    # every image listed in media_needed.txt

Then run `python build.py` and commit.
tools/media_urls.json maps each filename to its public URL (generated from the WordPress export).
"""
import json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / 'media_src'
urls = json.loads((ROOT / 'tools' / 'media_urls.json').read_text())
needed = ROOT / 'media_needed.txt'
if not needed.exists():
    sys.exit('Run `python build.py` first so media_needed.txt exists.')

want_all = '--all' in sys.argv
names = [l.split(None, 1)[1].strip() for l in needed.read_text().splitlines()
         if l.strip() and (want_all or l.startswith('MISSING'))]
MEDIA.mkdir(exist_ok=True)
ok = fail = skipped = 0
for n in names:
    dest = MEDIA / n
    if dest.exists():
        skipped += 1
        continue
    url = urls.get(n)
    if not url:
        print(f'  not in url map : {n}')
        fail += 1
        continue
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (maya-tuya media fetch)'})
        with urllib.request.urlopen(req, timeout=30) as r:
            dest.write_bytes(r.read())
        print(f'  downloaded     : {n}  ({dest.stat().st_size // 1024} KB)')
        ok += 1
    except Exception as e:
        print(f'  FAILED         : {n}  ({e})')
        fail += 1
print(f'\n{ok} downloaded, {skipped} already present, {fail} failed. Now run: python build.py')
