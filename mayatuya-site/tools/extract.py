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


# Live Stripe payment links -> tokens (the real links live in config.json at launch; placeholders until then)
STRIPE_MAP = {
    'https://buy.stripe.com/14AbJ1eZT4gvfQmfYD2cg04': '{{stripe:destacado_monthly}}',
    'https://buy.stripe.com/7sY14ndVP7sHeMi9Af2cg05': '{{stripe:destacado_annual}}',
    'https://buy.stripe.com/00wcN52d75kz9rYaEj2cg06': '{{stripe:fundador}}',
}

# Old WordPress / Polylang URLs that no longer exist -> where they live now
LEGACY_LINKS = [
    (r'href="/es/inicio/?"', 'href="/inicio/"'),
    (r'href="/es/destinos/?"', 'href="/inicio/destinos/"'),
    (r'href="/es/aportaciones/?"', 'href="/inicio/aportaciones/"'),
    (r'href="/es/acceso-aliados/?"', 'href="/inicio/hazte-aliado/"'),
    (r'href="/become-allied/?"', 'href="/inicio/hazte-aliado/"'),
    (r'href="/hazte-aliado/?"', 'href="/inicio/hazte-aliado/"'),
    (r'href="/home/?"', 'href="/"'),
]


def clean_widget_html(h):
    h = h.replace('\r\n', '\n').replace('\r', '\n')
    for url, token in STRIPE_MAP.items():
        h = h.replace(url, token)
    h = re.sub(r'<!--.*?-->', '', h, flags=re.S)                       # authoring comments
    h = re.sub(r"@import\s+url\([^)]*\);?\s*", '', h)                   # fonts are loaded once, in the layout
    h = re.sub(r'https?://(?:www\.)?mayatuya\.com/?', '/', h)           # absolute -> root-relative
    # uploads -> flat folders: images in /assets/img/, PDFs/ZIPs in /assets/dl/
    h = re.sub(r'/?wp-content/uploads/(?:[^"\')\s]*/)?([^"\')\s/]+)',
               lambda m: ('/assets/dl/' if re.search(r'\.(pdf|zip)$', m.group(1), re.I) else '/assets/img/') + m.group(1), h)
    h = re.sub(r'\[fluentform id=["\']?(\d+)["\']?\]', r'{{form:\1}}', h)
    for pat, rep in LEGACY_LINKS:
        h = re.sub(pat, rep, h)
    h = re.sub(r'\n{3,}', '\n\n', h)
    return h.strip()


# Astra theme palette (read from the inline CSS of the live site: --ast-global-color-N)
PALETTE = {'0': '#0b3d2e', '1': '#c6a45a', '2': '#1a1a1a', '3': '#3c3c3c', '4': '#f3eee2',
           '5': '#ffffff', '6': '#d5cbbe', '7': '#e9e2d3', '8': '#d98c5f'}


def sd(x):
    """Elementor serialises empty settings as [] - normalise to a dict."""
    return x if isinstance(x, dict) else {}


def color_of(s, key):
    """Resolve an Elementor colour setting, following Astra global-colour references."""
    m = re.search(r'astglobalcolor(\d)', sd(s.get('__globals__')).get(key, '') or '')
    return PALETTE[m.group(1)] if m else (s.get(key) or '')


def rgba(hexcol, a=1.0):
    """#RGB / #RRGGBB / #RRGGBBAA -> rgba(), multiplying alpha by `a`."""
    h = hexcol.lstrip('#')
    if len(h) == 3: h = ''.join(c * 2 for c in h)
    try:
        alpha = (int(h[6:8], 16) / 255 if len(h) == 8 else 1.0) * a
        return f'rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha:.2f})'
    except ValueError:
        return hexcol


def size_of(v, default):
    v = sd(v)
    try:
        return float(v.get('size')) if v.get('size') not in (None, '') else default
    except (TypeError, ValueError):
        return default


def luminance(hexcol):
    h = (hexcol or '').lstrip('#')
    if len(h) == 3: h = ''.join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return 1.0
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def container_background(s, has_white_heading=False):
    """CSS declarations for a container's background (colour, gradient, image + overlay)."""
    bg = s.get('background_background')
    layers, color = [], ''
    if bg == 'gradient':
        a, b = color_of(s, 'background_color'), color_of(s, 'background_color_b')
        if a and b:
            sa, sb = size_of(s.get('background_color_stop'), 0), size_of(s.get('background_color_b_stop'), 100)
            ang = size_of(s.get('background_gradient_angle'), 180)
            layers.append(f'linear-gradient({ang:g}deg,{a} {sa:g}%,{b} {sb:g}%)')
    elif bg == 'classic':
        color = color_of(s, 'background_color')
    img = clean_widget_html(sd(s.get('background_image')).get('url', '')) if bg in ('classic', 'gradient') else ''
    if img and s.get('background_size') == 'auto' and (s.get('background_xpos') or s.get('background_ypos')):
        img = ''                   # a hand-positioned watermark we cannot reproduce faithfully
    out = []
    ob = s.get('background_overlay_background')
    op = size_of(s.get('background_overlay_opacity'), 0.5)
    if ob == 'classic' and op > 0:
        oc = color_of(s, 'background_overlay_color')
        if oc and (img or color or layers):
            layers.insert(0, f'linear-gradient({rgba(oc, op)},{rgba(oc, op)})')
    elif ob == 'gradient' and op > 0:
        a, b = color_of(s, 'background_overlay_color'), color_of(s, 'background_overlay_color_b')
        if a and b:
            sa, sb = size_of(s.get('background_overlay_color_stop'), 0), size_of(s.get('background_overlay_color_b_stop'), 100)
            ang = size_of(s.get('background_overlay_gradient_angle'), 180)
            layers.insert(0, f'linear-gradient({ang:g}deg,{rgba(a, op)} {sa:g}%,{rgba(b, op)} {sb:g}%)')
    if img:
        layers.append(f"url('{img}')")
        out.append(f"background-size:{s.get('background_size') or 'cover'}")
        out.append(f"background-position:{s.get('background_position') or 'center center'}")
        out.append('background-repeat:no-repeat')
    if has_white_heading and (not color or luminance(color) > 0.5) and not img:
        color = PALETTE['0']       # the section's heading is white, so the original must have been dark
    if color:
        out.insert(0, f'background-color:{color}')
    if layers:
        out.insert(1 if color else 0, 'background-image:' + ','.join(layers))
    return ';'.join(out)


def px(v):
    u = v.get('unit', 'px')
    return f"{v.get('top','0')}{u} {v.get('right','0')}{u} {v.get('bottom','0')}{u} {v.get('left','0')}{u}"


def pad_vars(v):
    """Padding as CSS variables, so site.css can enforce a minimum side gutter on small screens."""
    if not v:
        return '--pt:10px;--pr:10px;--pb:10px;--pl:10px'
    u = v.get('unit', 'px')
    return ';'.join(f'--p{k}:{v.get(n, "0") or "0"}{u}' for k, n in (('t', 'top'), ('r', 'right'), ('b', 'bottom'), ('l', 'left')))


def link_url(s):
    return clean_widget_html(sd(s.get('link')).get('url', '#'))


def clean_editor(h):
    h = re.sub(r'\sdata-(?:start|end|is-last-node|is-only-node)="[^"]*"', '', h)
    h = re.sub(r'<p>(?:\s|&nbsp;)*</p>', '', h)
    return clean_widget_html(h)


def font_size_css(s):
    d = size_of(s.get('typography_font_size'), None)
    if not d:
        return ''
    m = size_of(s.get('typography_font_size_mobile'), None) or max(14, round(d * 0.6))
    return f'font-size:clamp({m:g}px,{d / 12.8:.2f}vw,{d:g}px)' if m < d else f'font-size:{d:g}px'


def style_of(s, kind='t', *extra):
    st = list(extra)
    if s.get('align'): st.append(f"text-align:{s['align']}")
    col = color_of(s, 'title_color') if kind == 'h' else color_of(s, 'text_color')
    if col: st.append(f'color:{col}')
    fs = font_size_css(s)
    if fs: st.append(fs)
    lh = sd(s.get('typography_line_height')).get('size')
    if lh: st.append(f'line-height:{lh}')
    return f' style="{";".join(st)}"' if st else ''


def native_widget(wt, s, lang):
    """Convert Elementor's built-in widgets to plain HTML. Returns None when a widget should be dropped."""
    if wt == 'heading':
        size = s.get('header_size') or 'h2'
        title = (s.get('title') or '').replace('\n', '<br>')
        return f'<{size} class="mt-h"{style_of(s, "h")}>{title}</{size}>'
    if wt == 'text-editor':
        return f'<div class="mt-text"{style_of(s, "t")}>{clean_editor(s.get("editor", ""))}</div>'
    if wt == 'button':
        return f'<p class="mt-btn-wrap"{style_of(s, "b")}><a class="mt-btn" href="{link_url(s)}">{clean_widget_html(s.get("text", ""))}</a></p>'
    return None


def collect_widgets(el, out, warn, lang='en'):
    for c in el.get('elements', []):
        if c.get('elType') == 'container':
            collect_widgets(c, out, warn, lang)
        elif c.get('elType') == 'widget':
            wt, s = c.get('widgetType'), sd(c.get('settings'))
            if wt == 'html':
                out.append(clean_widget_html(s.get('html', '')))
            elif wt == 'shortcode':
                sc = s.get('shortcode', '')
                if 'product_page' in sc:        # WooCommerce "pay what you want" contribution -> Stripe link
                    label = 'Make a contribution' if lang == 'en' else 'Hacer una aportación'
                    out.append(f'<p class="mt-btn-wrap" style="text-align:center"><a class="mt-btn" href="{{{{stripe:contribution}}}}">{label}</a></p>')
                else:
                    out.append(clean_widget_html(sc))
            elif wt == 'social-icons':
                pass                              # old footer remnant
            elif native_widget(wt, s, lang) is not None:
                out.append(native_widget(wt, s, lang))
            elif wt == 'image':
                img = sd(s.get('image'))
                if img.get('url'):
                    out.append(clean_widget_html(f'<img src="{img["url"]}" alt="{img.get("alt", "")}">'))
            else:
                warn.append(wt)


def extract(post, kind='page', lang='en', keep=None):
    data = json.loads(post['meta'].get('_elementor_data') or '[]')
    sections, warn, kept = [], [], [0]
    for top in data:
        s = sd(top.get('settings'))
        widgets = []
        if top.get('elType') == 'widget':
            collect_widgets({'elements': [top]}, widgets, warn, lang)
        else:
            collect_widgets(top, widgets, warn, lang)
        widgets = [w for w in widgets if w]
        if keep is not None:                      # some legacy pages have a copy of the old footer pasted in
            widgets = widgets[:max(0, keep - kept[0])]
            kept[0] += len(widgets)
        body = '\n'.join(widgets)
        if not body:
            continue
        if kind == 'footer':
            sections.append(body)
            continue
        style = [pad_vars(s.get('padding'))]
        if s.get('margin'):
            style.append('margin:' + px(s['margin']))
        white_heading = any('color:#ffffff' in w or 'color:#fff' in w for w in widgets if w.startswith('<h'))
        bgcss = container_background(s, white_heading)
        if bgcss:
            style.append(bgcss)
        cls = 'mt-sec' + (' mt-full' if s.get('content_width') == 'full' else '')
        m = re.search(r'background-color:(#[0-9a-fA-F]{3,8})', bgcss)
        if m and luminance(m.group(1)) < 0.3 and 'background-image' not in bgcss:
            cls += ' mt-dark'
        sections.append(f'<section class="{cls}" style="{";".join(style)}">\n<div class="mt-inner">\n{body}\n</div>\n</section>')
    html = '\n\n'.join(sections)
    for pat, rep in LEGACY_LINKS:            # also catches links built from native button widgets
        html = re.sub(pat, rep, html)
    return html, sorted(set(warn))


def run_manifest(xml, manifest):
    posts = load_posts(xml)
    for m in json.loads(Path(manifest).read_text()):
        post = posts.get(str(m['post']))
        if not post:
            print(f'!! {m["id"]}: post {m["post"]} not found')
            continue
        html, warn = extract(post, 'page', m.get('lang', 'en'), m.get('keep'))
        (ROOT / 'src' / 'content' / f'{m["id"]}.html').write_text(html + '\n', encoding='utf-8')
        print(f'{m["id"]:34} post {m["post"]:>5}  {len(html):>6,} chars' + (f'  unhandled: {warn}' if warn else ''))


def main():
    if len(__import__('sys').argv) > 2 and __import__('sys').argv[1] == '--manifest':
        return run_manifest(__import__('sys').argv[3], __import__('sys').argv[2])
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
