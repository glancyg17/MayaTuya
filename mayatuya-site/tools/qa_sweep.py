#!/usr/bin/env python3
"""
Load every page in docs/ at desktop and mobile width and report JS errors, horizontal overflow,
failed requests and broken internal links.  Run `python build.py` first.

    pip install playwright && playwright install chromium
    python tools/qa_sweep.py
"""
import functools, http.server, json, re, socketserver, sys, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
pages = json.loads((ROOT / 'src' / 'pages.json').read_text(encoding='utf-8'))


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(DOCS)))
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{port}'

problems = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (1280, 390):
        page = browser.new_context(viewport={'width': width, 'height': 900}).new_page()
        errors, failed = [], []
        page.on('pageerror', lambda e: errors.append(str(e)[:140]))
        page.on('response', lambda r: failed.append(f'{r.status} {r.url.replace(base, "")}')
                if r.status >= 400 and 'fonts.g' not in r.url and 'flagcdn' not in r.url else None)
        for pg in pages:
            errors.clear(); failed.clear()
            page.goto(base + pg['url'], wait_until='load')
            page.wait_for_timeout(150)
            overflow = page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            hrefs = page.evaluate("[...document.querySelectorAll('a[href^=\"/\"]')].map(a => a.getAttribute('href'))")
            bad_links = sorted({h.split('#')[0].split('?')[0] for h in hrefs
                                if not (DOCS / h.split('#')[0].split('?')[0].strip('/') / 'index.html').exists()
                                and not (DOCS / h.split('#')[0].split('?')[0].strip('/')).is_file()
                                and h.split('#')[0] not in ('', '/')})
            if overflow > 1 or errors or failed or bad_links:
                problems.append(f'[{width}] {pg["id"]}: overflow={overflow} js={errors} http={failed[:3]} links={bad_links[:3]}')
    browser.close()
srv.shutdown()

print(f'checked {len(pages) * 2} page loads; {len(problems)} with problems')
for line in problems:
    print(' ', line)
sys.exit(1 if problems else 0)
