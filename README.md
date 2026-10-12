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

## Images

Copy your local WordPress uploads folder into `media_src/` (keep it as it is). The build copies **only the files pages actually
reference** into `docs/assets/img/`, so the 214 unused media-library items never reach the repo.

## Placeholders (swap before launch)

`config.json` holds `PLACEHOLDER_…` values for the Web3Forms access key and every Stripe link.
In content, use `{{stripe:tu_negocio_mejor}}` etc. — the build swaps in the link from `config.json`.

```bash
python build.py --check-release   # fails while placeholders, missing images or broken links remain
```

## Adding / migrating a page

```bash
python tools/extract.py --xml path/to/wordpress-export.xml new-page-id=POST_ID
```
then add an entry to `src/pages.json` (write a real title and description — most old pages shared one generic title).
Forms: `python tools/forms_from_fluent.py path/to/fluentform-export.json 6 8 9 …`

## Going live (GitHub Pages)

1. Repo → Settings → Pages → Deploy from branch → `main` / `/docs`.
2. **Root-relative paths:** links are `/assets/…`, which work on a custom domain or a `username.github.io` repo, but **not** on
   a project URL like `username.github.io/repo/`. Preview locally with `--serve`, or test on a subdomain (e.g. `new.mayatuya.com`)
   before switching the main domain. Switching only a *subdomain* CNAME does not touch email (MX) records.
3. When ready for the real domain, add `docs/CNAME` containing `mayatuya.com` (the build preserves it).

## Not done yet

- Remaining ~55 pages (run the extractor + add to `pages.json`)
- Forms other than bookings (contact, Conscious Traveler, acuerdo ×3, Hazte Aliado)
- Self-hosted fonts and flag icons (currently Google Fonts + flagcdn.com)
- Structured data (Organization / WebSite JSON-LD) to replace SureRank's
