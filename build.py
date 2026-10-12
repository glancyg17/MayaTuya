#!/usr/bin/env python3
"""
Maya Tuya — static site build.

    python build.py                 build into docs/
    python build.py --serve         build, then preview at http://localhost:8000
    python build.py --check-release exit non-zero if anything is unfinished
                                    (placeholder keys, missing images, broken links)

Source of truth:
    config.json            site constants, nav, Stripe links, form key
    src/pages.json         one entry per page (url, title, description, language pair)
    src/content/*.html     page bodies (sections of hand-written HTML)
    src/partials/*.html    footers
    src/forms.json         form definitions ({{form:ID}} tokens in content)
    media_src/             your local WordPress uploads folder (any structure)
    src/assets/            css + js, copied as-is
Output (docs/) is what GitHub Pages serves. Never edit docs/ by hand.
"""
import argparse, json, re, shutil, sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
import os
SRC, OUT, MEDIA = ROOT / 'src', ROOT / 'docs', Path(os.environ.get('MT_MEDIA', ROOT / 'media_src'))

cfg = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
pages = json.loads((SRC / 'pages.json').read_text(encoding='utf-8'))
forms = json.loads((SRC / 'forms.json').read_text(encoding='utf-8')) if (SRC / 'forms.json').exists() else {}
by_id = {p['id']: p for p in pages}
DOMAIN = cfg['domain'].rstrip('/')

problems, notes = [], []          # problems block --check-release; notes are informational
images_used = set()
internal_links = {}               # href -> set(page ids)


def esc(s):
    return escape(str(s), quote=True)


# ── media ─────────────────────────────────────────────────────────
def index_media():
    idx, dupes = {}, set()
    for p in MEDIA.rglob('*'):
        if p.is_file() and not p.name.startswith('.') and p.name != 'README.md':
            if p.name in idx:
                dupes.add(p.name)
            idx.setdefault(p.name, p)
    if dupes:
        notes.append(f'media_src has duplicate filenames (first one wins): {sorted(dupes)[:5]}')
    return idx


# ── html helpers ──────────────────────────────────────────────────
def hoist_styles(html, bag):
    def take(m):
        css = m.group(1).strip()
        if css and css not in bag:
            bag.append(css)
        return ''
    return re.sub(r'<style[^>]*>(.*?)</style>', take, html, flags=re.S)


def norm_links(html):
    def fix(m):
        path, tail = m.group(2), m.group(3) or ''
        if path.startswith('//') or path.startswith('/assets/') or re.search(r'\.[A-Za-z0-9]{2,5}$', path):
            return m.group(0)
        if not path.endswith('/'):
            path += '/'
        return f'{m.group(1)}{path}{tail}"'
    return re.sub(r'(href=")(/[^"#?]*)([?#][^"]*)?"', fix, html)


def stripe_tokens(html):
    def rep(m):
        key = m.group(1)
        if key not in cfg['stripe']:
            problems.append(f'unknown stripe key "{key}"')
            return '#'
        return cfg['stripe'][key]
    return re.sub(r'\{\{stripe:([a-z_]+)\}\}', rep, html)


def collect_assets(html):
    for m in re.finditer(r'/assets/img/([^"\'\s)<>]+)', html):
        images_used.add(m.group(1))


# ── forms ─────────────────────────────────────────────────────────
AUTOCOMPLETE = {'first_name': 'given-name', 'last_name': 'family-name', 'email': 'email', 'phone': 'tel'}
ERRORS = {'en': 'We could not send your message. Please write to us directly at',
          'es': 'No pudimos enviar tu mensaje. Escríbenos directamente a'}


def render_field(x, fid):
    t, name = x['type'], x['name']
    if t == 'hidden':
        return f'<input type="hidden" name="{esc(name)}" value="{esc(x.get("value", ""))}">'
    fld, req = f'f{fid}-{name}', x.get('required')
    label = f'<label class="mt-label{" mt-req" if req else ""}" for="{fld}">{esc(x.get("label", ""))}</label>'
    r = ' required' if req else ''
    if t == 'checkbox':
        o = x['options'][0]
        return (f'<div class="mt-field"><label class="mt-check" for="{fld}"><input type="checkbox" id="{fld}" '
                f'name="{esc(name)}" value="Confirmed"{r}><span>{esc(o["label"])}</span></label></div>')
    if t == 'textarea':
        ctl = f'<textarea id="{fld}" name="{esc(name)}"{r}></textarea>'
    elif t == 'select':
        opts = f'<option value="">{esc(x.get("placeholder", ""))}</option>' + ''.join(
            f'<option value="{esc(o["value"])}">{esc(o["label"])}</option>' for o in x['options'])
        ctl = f'<select id="{fld}" name="{esc(name)}"{r}>{opts}</select>'
    else:
        a = f' autocomplete="{AUTOCOMPLETE[name]}"' if name in AUTOCOMPLETE else ''
        a += f' placeholder="{esc(x["placeholder"])}"' if x.get('placeholder') else ''
        if t == 'number':
            a += ' inputmode="numeric"'
            if x.get('min'): a += f' min="{esc(x["min"])}"'
            if x.get('max'): a += f' max="{esc(x["max"])}"'
        ctl = f'<input type="{t}" id="{fld}" name="{esc(name)}"{a}{r}>'
    return f'<div class="mt-field">{label}{ctl}</div>'


def render_form(fid, page):
    f = forms.get(fid)
    if not f:
        problems.append(f'{page["id"]}: form {fid} not defined in src/forms.json')
        return f'<!-- form {fid} missing -->'
    lang = page['lang']
    exp = next((x['value'] for x in f['fields'] if x['name'] == 'experience'), '')
    subject = f'[MT booking] {exp} ({lang.upper()})' if exp else f'[MT form] {f["title"]} ({lang.upper()})'
    hidden = {'access_key': cfg['form_access_key'], 'subject': subject, 'from_name': 'Maya Tuya website',
              'form_id': fid, 'page_language': lang, 'page_url': DOMAIN + page['url']}
    out = [f'<form class="mt-form" method="POST" action="{esc(cfg["form_endpoint"])}" '
           f'data-success="{esc(f["success"])}" data-error="{esc(ERRORS[lang])}" data-mail="{esc(cfg["email"])}">']
    out += [f'<input type="hidden" name="{k}" value="{esc(v)}">' for k, v in hidden.items()]
    out.append('<input type="checkbox" name="botcheck" class="mt-hp" tabindex="-1" autocomplete="off" aria-hidden="true">')
    fields, i = f['fields'], 0
    while i < len(fields):
        x = fields[i]
        if x['name'] == 'first_name' and i + 1 < len(fields) and fields[i + 1]['name'] == 'last_name':
            out.append('<div class="mt-row">' + render_field(x, fid) + render_field(fields[i + 1], fid) + '</div>')
            i += 2
            continue
        out.append(render_field(x, fid))
        i += 1
    out.append(f'<button type="submit" class="mt-form-btn">{esc(f["button"])}</button>')
    out.append('<p class="mt-form-status" role="alert"></p></form>')
    return '\n'.join(out)


# ── header ────────────────────────────────────────────────────────
def render_header(page):
    lang, url = page['lang'], page['url']
    items = cfg['nav'][lang]
    flat = [(i['href'], i) for i in items] + [(c['href'], c) for i in items for c in i.get('children', [])]
    best = max((h for h, _ in flat if h != '/' and url.startswith(h)), key=len, default=None)

    def link(i, cls=''):
        cur = ' aria-current="page"' if i['href'] == best else ''
        return f'<a href="{i["href"]}"{cur}>{esc(i["label"])}</a>'

    lis = []
    for i in items:
        if i.get('children'):
            sub = ''.join(f'<li>{link(c)}</li>' for c in i['children'])
            lis.append(f'<li class="has-sub"><a href="{i["href"]}" aria-haspopup="true">{esc(i["label"])}</a><ul class="sub">{sub}</ul></li>')
        else:
            lis.append(f'<li>{link(i)}</li>')

    # Language switch: a real link to the paired page (falls back to the other language's home)
    pair = by_id.get(page.get('pair', ''))
    if pair:
        target = pair['url']
    else:
        target = cfg['lang_home']['es' if lang == 'en' else 'en']
        if page.get('pair'):
            notes.append(f'{page["id"]}: pair "{page["pair"]}" not built yet — language switch points to the language home')
    sw = cfg['lang_switch'][lang]
    logo = cfg['logos'][lang]
    images_used.add(logo)
    return f'''<a class="mt-skip" href="#content">{esc(cfg["skip_link"][lang])}</a>
<header class="mt-header" id="masthead">
<div class="mt-header-inner">
<a class="mt-logo" href="{cfg["lang_home"][lang]}"><img src="/assets/img/{logo}" alt="Maya Tuya" width="120" height="56"></a>
<button class="mt-nav-toggle" type="button" aria-expanded="false" aria-controls="mt-nav">{esc(cfg["menu_label"][lang])}</button>
<nav class="mt-nav" id="mt-nav" aria-label="{'Main' if lang == 'en' else 'Principal'}"><ul>{''.join(lis)}</ul></nav>
<a class="mt-lang-switch" href="{target}" hreflang="{sw["hreflang"]}" lang="{sw["hreflang"]}" title="{esc(sw["title"])}">
<img class="mt-lang-flag" src="https://flagcdn.com/20x15/{sw["flag"]}.png" width="20" height="15" alt="">
<span class="mt-lang-divider"></span><span class="mt-lang-code">{sw["label"]}</span></a>
</div>
</header>'''


# ── page ──────────────────────────────────────────────────────────
FONTS = ('https://fonts.googleapis.com/css2?family=Playfair+Display+SC:wght@400;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400'
         '&family=Lato:wght@300;400;700&family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400;1,600&display=swap')

LAYOUT = '''<!DOCTYPE html>
<html lang="%%LANG%%">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%%TITLE%%</title>
<meta name="description" content="%%DESC%%">
<meta name="robots" content="%%ROBOTS%%">
<link rel="canonical" href="%%CANON%%">
%%ALTERNATES%%
<meta property="og:type" content="website">
<meta property="og:site_name" content="Maya Tuya">
<meta property="og:title" content="%%TITLE%%">
<meta property="og:description" content="%%DESC%%">
<meta property="og:url" content="%%CANON%%">
<meta property="og:locale" content="%%LOCALE%%">
%%OGIMAGE%%
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/img/%%FAVICON%%">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="%%FONTS%%">
<link rel="stylesheet" href="/assets/css/site.css">
%%PAGESTYLES%%
</head>
<body class="%%BODYCLASS%%">
%%HEADER%%
<main id="content">
%%CONTENT%%
</main>
<footer id="colophon">
%%FOOTER%%
</footer>
<script src="/assets/js/site.js" defer></script>
</body>
</html>
'''


def build_page(page, footers):
    lang = page['lang']
    styles = []
    body = (SRC / 'content' / page['content']).read_text(encoding='utf-8')
    body = re.sub(r'\{\{form:(\d+)\}\}', lambda m: render_form(m.group(1), page), body)
    body = stripe_tokens(body)
    body = hoist_styles(body, styles)
    foot = hoist_styles(footers[lang], styles)
    body, foot = norm_links(body), norm_links(foot)
    collect_assets(body + foot + ''.join(styles))
    for h in re.findall(r'href="(/[^"#?]*)', body + foot):
        internal_links.setdefault(h, set()).add(page['id'])
    left = re.findall(r'\{\{[^}]+\}\}', body + foot)
    if left:
        problems.append(f'{page["id"]}: unresolved tokens {sorted(set(left))}')
    if re.search(r'wp-content|elementor', body + foot):
        problems.append(f'{page["id"]}: leftover WordPress references')

    alts = ''
    pair = by_id.get(page.get('pair', ''))
    if pair:
        en, es = (page, pair) if lang == 'en' else (pair, page)
        alts = (f'<link rel="alternate" hreflang="en" href="{DOMAIN}{en["url"]}">\n'
                f'<link rel="alternate" hreflang="es" href="{DOMAIN}{es["url"]}">\n'
                f'<link rel="alternate" hreflang="x-default" href="{DOMAIN}{en["url"]}">')
    og = ''
    if page.get('og_image'):
        images_used.add(page['og_image'])
        og = f'<meta property="og:image" content="{DOMAIN}/assets/img/{page["og_image"]}">'
    images_used.add(cfg['favicon'])

    html = LAYOUT
    for k, v in {
        'LANG': lang, 'TITLE': esc(page['title']), 'DESC': esc(page['description']),
        'ROBOTS': 'noindex, follow' if page.get('noindex') else 'index, follow',
        'CANON': DOMAIN + page['url'], 'ALTERNATES': alts, 'OGIMAGE': og,
        'LOCALE': 'en_US' if lang == 'en' else 'es_MX', 'FAVICON': cfg['favicon'], 'FONTS': FONTS,
        'PAGESTYLES': '\n'.join(f'<style>\n{c}\n</style>' for c in styles),
        'BODYCLASS': f'lang-{lang} page-{page["id"]}', 'HEADER': render_header(page),
        'CONTENT': body, 'FOOTER': foot,
    }.items():
        html = html.replace(f'%%{k}%%', v)
    return html


# ── main ──────────────────────────────────────────────────────────
def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--serve', action='store_true')
    ap.add_argument('--check-release', action='store_true')
    a = ap.parse_args()

    # clean output (keep CNAME so the custom domain survives rebuilds)
    OUT.mkdir(exist_ok=True)
    for p in OUT.iterdir():
        if p.name in ('CNAME',):
            continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.copytree(SRC / 'assets', OUT / 'assets', dirs_exist_ok=True)
    (OUT / '.nojekyll').write_text('')

    footers = {l: (SRC / 'partials' / f'footer_{l}.html').read_text(encoding='utf-8') for l in ('en', 'es')}

    built = {}
    for p in pages:
        html = build_page(p, footers)
        write(OUT / 'index.html' if p['url'] == '/' else OUT / p['url'].strip('/') / 'index.html', html)
        built[p['url']] = p

    # 404 (GitHub Pages serves /404.html for unknown paths)
    nf = {'id': '404', 'lang': 'en', 'url': '/404.html', 'noindex': True, 'content': '404.html',
          'title': 'Page not found — Maya Tuya', 'description': 'This page does not exist.'}
    write(SRC / 'content' / '404.html', '''<section class="mt-sec" style="padding:80px 30px"><div class="mt-inner" style="text-align:center">
<p style="font-family:'Playfair Display SC',serif;font-size:clamp(28px,4vw,44px);margin:0">This page isn't here.</p>
<p style="font-family:'Cormorant Garamond',serif;font-style:italic;font-size:20px;color:#9a7828;margin:0">Try the beginning.</p>
<p style="margin:12px 0 0"><a href="/" style="font-size:10px;letter-spacing:.32em;text-transform:uppercase;color:#013220">Home</a>
&nbsp;·&nbsp;<a href="/inicio/" style="font-size:10px;letter-spacing:.32em;text-transform:uppercase;color:#013220">Inicio</a></p>
</div></section>
''')
    write(OUT / '404.html', build_page(nf, footers))

    # sitemap + robots
    urls = [p['url'] for p in pages if not p.get('noindex')]
    write(OUT / 'sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + ''.join(f'  <url><loc>{DOMAIN}{u}</loc></url>\n' for u in urls) + '</urlset>\n')
    write(OUT / 'robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n')

    # media: copy only what the pages actually reference
    idx = index_media()
    (OUT / 'assets' / 'img').mkdir(parents=True, exist_ok=True)
    have, missing = [], []
    for name in sorted(images_used):
        if name in idx:
            shutil.copy2(idx[name], OUT / 'assets' / 'img' / name)
            have.append(name)
        else:
            missing.append(name)
    write(ROOT / 'media_needed.txt', '\n'.join(f'{"OK     " if n in have else "MISSING"}  {n}' for n in sorted(images_used)) + '\n')

    # checks
    broken = sorted(h for h in internal_links
                    if not h.startswith('/assets/') and h not in built and h != '/404.html')
    placeholders = [k for k, v in {**cfg['stripe'], 'form_access_key': cfg['form_access_key']}.items() if str(v).startswith('PLACEHOLDER')]
    if missing: problems.append(f'{len(missing)} image(s) not found in media_src/ (see media_needed.txt)')
    if broken: problems.append(f'{len(broken)} internal link(s) point to pages not built yet')
    if placeholders: problems.append(f'placeholders still in config.json: {", ".join(placeholders)}')

    print(f'Built {len(pages)} pages + 404 → docs/   |   images: {len(have)} ok, {len(missing)} missing')
    for n in notes: print('  note:', n)
    for p in problems: print('  todo:', p)
    if broken: print('  unbuilt link targets:', ', '.join(broken[:12]) + (' …' if len(broken) > 12 else ''))

    if a.check_release and problems:
        print('\nNOT ready to release.')
        sys.exit(1)
    if a.serve:
        import http.server, socketserver, os
        os.chdir(OUT)
        with socketserver.TCPServer(('', 8000), http.server.SimpleHTTPRequestHandler) as s:
            print('\nPreview: http://localhost:8000  (Ctrl+C to stop)')
            s.serve_forever()


if __name__ == '__main__':
    main()
