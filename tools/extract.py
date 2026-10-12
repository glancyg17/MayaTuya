#!/usr/bin/env python3
"""
Extract page bodies from a WordPress/Elementor export (WXR .xml) into clean
HTML fragments in src/content/. Run once per page you want to migrate.

    python tools/extract.py --xml path/to/export.xml home-en=15 home-es=2239
    python tools/extract.py --xml path/to/export.xml --footer footer_en=2197 footer_es=2205

Each Elementor top-level container becomes one <section class="mt-sec">.
HTML widgets are carried over as-is (they are already hand-written HTML).
"""
import argparse, json, re
from pathlib import Path
from lxml import etree

NS = {'wp': 'http://wordpress.org/export/1.2/'}
ROOT = Path(__file__).resolve().parent.parent


def load_posts(xml_path):
    posts = {}
    for it in etree.parse(str(xml_path)).findall('.//item'):
        pid = it.findtext('wp:post_id', namespaces=NS)
        meta = {m.findtext('wp:meta_key', namespaces=NS): (m.findtext('wp:meta_value', namespaces=NS) or '')
                for m in it.findall('wp:postmeta', namespaces=NS)}
        posts[pid] = {'slug': it.findtext('wp:post_name', namespaces=NS), 'meta': meta}
    return posts


def clean_widget_html(h):
    h = re.sub(r'<!--.*?-->', '', h, flags=re.S)                       # authoring comments
    h = re.sub(r"@import\s+url\([^)]*\);?\s*", '', h)                   # fonts are loaded once, in the layout
    h = re.sub(r'https?://(?:www\.)?mayatuya\.com/?', '/', h)           # absolute -> root-relative
    h = re.sub(r'/?wp-content/uploads/(?:[^"\')\s]*/)?([^"\')\s/]+)', r'/assets/img/\1', h)  # flat image dir
    h = re.sub(r'\[fluentform id=["\']?(\d+)["\']?\]', r'{{form:\1}}', h)
    h = re.sub(r'\n{3,}', '\n\n', h)
    return h.strip()


def sd(x):
    """Elementor serialises empty settings as [] - normalise to a dict."""
    return x if isinstance(x, dict) else {}


def px(v):
    u = v.get('unit', 'px')
    return f"{v.get('top','0')}{u} {v.get('right','0')}{u} {v.get('bottom','0')}{u} {v.get('left','0')}{u}"


def pad_vars(v):
    """Padding as CSS variables, so site.css can enforce a minimum side gutter on small screens."""
    if not v:
        return '--pt:10px;--pr:10px;--pb:10px;--pl:10px'
    u = v.get('unit', 'px')
    return ';'.join(f'--p{k}:{v.get(n, "0") or "0"}{u}' for k, n in (('t', 'top'), ('r', 'right'), ('b', 'bottom'), ('l', 'left')))


def collect_widgets(el, out, warn):
    for c in el.get('elements', []):
        if c.get('elType') == 'container':
            collect_widgets(c, out, warn)
        elif c.get('elType') == 'widget':
            wt, s = c.get('widgetType'), sd(c.get('settings'))
            if wt == 'html':
                out.append(clean_widget_html(s.get('html', '')))
            elif wt == 'shortcode':
                out.append(clean_widget_html(s.get('shortcode', '')))
            elif wt == 'image':
                img = sd(s.get('image'))
                if img.get('url'):
                    out.append(clean_widget_html(f'<img src="{img["url"]}" alt="{img.get("alt", "")}">'))
            else:
                warn.append(wt)


def extract(post, kind='page'):
    data = json.loads(post['meta'].get('_elementor_data') or '[]')
    sections, warn = [], []
    for top in data:
        s = sd(top.get('settings'))
        widgets = []
        if top.get('elType') == 'widget':
            collect_widgets({'elements': [top]}, widgets, warn)
        else:
            collect_widgets(top, widgets, warn)
        body = '\n'.join(w for w in widgets if w)
        if not body:
            continue
        if kind == 'footer':
            sections.append(body)
            continue
        style = [pad_vars(s.get('padding'))]
        if s.get('margin'):
            style.append('margin:' + px(s['margin']))
        if s.get('background_background') == 'classic' and s.get('background_color'):
            style.append('background:' + s['background_color'])
        cls = 'mt-sec' + (' mt-full' if s.get('content_width') == 'full' else '')
        sections.append(f'<section class="{cls}" style="{";".join(style)}">\n<div class="mt-inner">\n{body}\n</div>\n</section>')
    return '\n\n'.join(sections), sorted(set(warn))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xml', required=True)
    ap.add_argument('--footer', action='store_true', help='write to src/partials instead of src/content')
    ap.add_argument('pairs', nargs='+', help='name=post_id')
    a = ap.parse_args()
    posts = load_posts(a.xml)
    for pair in a.pairs:
        name, pid = pair.split('=')
        if pid not in posts:
            print(f'!! post {pid} not found')
            continue
        html, warn = extract(posts[pid], 'footer' if a.footer else 'page')
        dest = ROOT / ('src/partials' if a.footer else 'src/content') / f'{name}.html'
        dest.write_text(html + '\n', encoding='utf-8')
        print(f'{name}: post {pid} ({posts[pid]["slug"]}) -> {dest.relative_to(ROOT)}  {len(html):,} chars'
              + (f'  unhandled widgets: {warn}' if warn else ''))


if __name__ == '__main__':
    main()
