# Maya Tuya — static site

Plain HTML/CSS/JS, built by one Python script, served by GitHub Pages from `docs/`.
No WordPress, no WooCommerce, no plugins. Payments are Stripe Payment Links; forms go through Web3Forms.

## Daily workflow

```bash
pip install lxml            # only needed for tools/extract.py
python build.py --serve     # build + preview at http://localhost:8000
git add -A && git commit -m "…" && git push
```

`docs/` is generated — never edit it by hand. Edit `src/` and rebuild.

## Where things live

| What | Where |
|---|---|
| Site constants, nav, Stripe links, form key | `config.json` |
| Every page's URL, title, description, EN↔ES pair | `src/pages.json` |
| Page bodies (hand-written HTML sections) | `src/content/*.html` |
| Footers | `src/partials/footer_en.html`, `footer_es.html` |
| Forms (`{{form:11}}` in a page becomes a form) | `src/forms.json` |
| Shared CSS / JS | `src/assets/css/site.css`, `src/assets/js/site.js` |
| Your local WordPress uploads | `media_src/` (any folder structure) |
| Which images pages need, found or missing | `media_needed.txt` (written on each build) |

Header, footer, language switch, canonical + hreflang tags, sitemap and robots are generated for you.
Page-specific CSS stays inside each page's HTML; the build hoists it into `<head>` and de-duplicates.

## Images and downloads

`python tools/fetch_media.py` downloads every image/ZIP the pages need from the live WordPress site into `media_src/`
(run `python build.py` first so `media_needed.txt` exists). Three files are **not** public on the live site and must come from
your own copies — put them in `media_src/` with exactly these names:

- `Guide-Campeche-First-Edition-ipt3rn.pdf` (paid guide, English)
- `ES_Campeche_FirstEdition-zs7f1m.pdf` (paid guide, Spanish)
- `Tu-Negocio-Mejor-9m0ieq.pdf`

The build copies **only the files pages actually reference** into `docs/assets/img/` and `docs/assets/dl/`, so unused media-library
items never reach the repo. Paid PDFs are protected only by their obscure filenames (noindex pages) — see the Codex decision.

## Staging vs live

`config.json` has `"mode": "staging"`: every page is `noindex`, canonicals use `new.mayatuya.com`, robots.txt blocks crawling and
no sitemap is written. When you switch the real domain: set `"mode": "live"`, put `mayatuya.com` in `docs/CNAME`, rebuild.

## Old WordPress URLs

`src/redirects.json` maps dead WordPress URLs (shop, cart, my-account, `/home`, `-2` slugs…) to their new homes as static redirect
pages. `src/link_fixes.json` repairs wrong links that existed inside the old pages (e.g. `/experiencias/…` → `/inicio/experiencias/…`).

## Placeholders (swap before launch)

`config.json` holds `PLACEHOLDER_…` values for the Web3Forms access key and the Stripe links (Aliado Destacado monthly/annual,
Fundador, Campeche guide, contribution). The three existing live Stripe links are saved under `stripe_live_reference` for when
you're ready. In content, use `{{stripe:guide_campeche}}` etc. — the build swaps in the link from `config.json`.

Stripe settings to make at launch: set the guide's Payment Link to redirect after payment to `/campeche-guide-download/`, the
Destacado/Fundador links to `/acuerdo-aliado-destacado/` and `/acuerdo-aliado-fundador/` flow as today (pay → accept agreement → welcome).

```bash
python build.py --check-release   # fails while placeholders, missing images or broken links remain
```

## Re-running the migration

All 69 pages were extracted from the WordPress export with `tools/manifest.json` (id, post, language, URL, EN/ES pair):

```bash
python tools/extract.py --manifest tools/manifest.json path/to/wordpress-export.xml
python tools/forms_from_fluent.py path/to/fluentform-export.json 3 6 7 8 9 11 12 13 14 15 16 17 18 19
```
Page bodies in `src/content/` are now the source of truth — edit them directly; re-extracting overwrites them.
Two pages are hand-built, not extracted: `product-campeche-guide-en` and `campeche-guide-download-en`.

## Going live (GitHub Pages)

1. Repo → Settings → Pages → Deploy from branch → `main` / `/docs`.
2. **Root-relative paths:** links are `/assets/…`, which work on a custom domain or a `username.github.io` repo, but **not** on
   a project URL like `username.github.io/repo/`. Preview locally with `--serve`, or test on a subdomain (e.g. `new.mayatuya.com`)
   before switching the main domain. Switching only a *subdomain* CNAME does not touch email (MX) records.
3. When ready for the real domain, add `docs/CNAME` containing `mayatuya.com` (the build preserves it).

## Not done yet

- Final styling/uniformity pass (two greens in use: #0b3d2e from the theme palette vs #013220 in the widgets; off-brand fonts
  were mapped to brand fonts only on the native-widget pages)
- Self-hosted fonts and flag icons (currently Google Fonts + flagcdn.com)
- Structured data (Organization / WebSite JSON-LD) to replace SureRank's
