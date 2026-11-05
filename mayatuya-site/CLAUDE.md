# CLAUDE.md — Maya Tuya site (mayatuya.com)

Working brief for Claude Code. This repo is **public**: never add private business information (investors, partner financial terms, prospects, personal data, account IDs). When this file and the founder disagree, the founder wins; when in doubt, ask.

*Aligned with Master Codex v6.5 (November 2026). The Codex itself is private and deliberately not in this repo.*

## Status

- **Production is live:** https://mayatuya.com (apex is canonical; `www` redirects to it). Static site, Cloudflare Workers, DNS on Cloudflare.
- **Staging:** https://new.mayatuya.com (noindex).
- **Merging to `main` deploys to PRODUCTION.**

## Workflow (non-negotiable)

1. Work on a branch. Never commit to `main` directly.
2. Run `python build.py`, check the preview.
3. Report: branch name, preview URL, what changed, anything unrequested you touched or couldn't do. Be direct and concise; end with what's waiting on Glancy and the next action.
4. **Wait for Glancy's approval before merging.** No auto-merge, ever.
5. Anything touching **prices, capacities, DNS, `mode: live`, or Stripe/Web3Forms keys** needs Glancy's explicit go-ahead in that request. Do not change DNS.

Change only what was asked. If something looks wrong elsewhere, report it; don't fix it silently. Glancy works alone: keep every change small, reviewable and executable by one person.

You **cannot see Workers Builds status** from here. After a merge, tell Glancy to check the `mayatuya` Worker → Deployments for the build on that commit.

## Repo layout and build (read before editing)

The git repo root contains the **active project in the `mayatuya-site/` folder**. Run every command from inside `mayatuya-site/`.
The old files at the repo root (a previous `src/`, `docs/`, `build.py`, etc.) are **legacy and dead — do not edit them**. Removing them needs Glancy's OK (pending).
Workers Builds uses `mayatuya-site/` as its root directory; if a build ever can't find `wrangler.jsonc`, check that setting first.

- **Edit `src/` and `config.json`. Never edit `docs/` by hand** — it is generated and committed (it is what Cloudflare serves). After any change: `python build.py`, then commit `src/` **and** `docs/` together.
- Preview locally: `python build.py --serve` → http://localhost:8000
- Windows: `python build.py` crashes at its final `print` (the `→` character vs the cp1252 console) unless `PYTHONUTF8=1` is set (`$env:PYTHONUTF8=1` in PowerShell) — see Known issues.
- Check before finishing: `python build.py` (read every `note:` / `todo:` line) and `python tools/qa_sweep.py` (needs `pip install playwright && playwright install chromium`). `qa_sweep` should only report the known-missing Gates images (see Open items); anything else is a regression.
- `python build.py --check-release` should fail **only** on missing images. Don't "fix" it by weakening the checks.
- Local tools (pymupdf, playwright, Chromium) were installed outside the repo — don't add them as dependencies.
- **No frameworks, no build tooling beyond `build.py`.** Zero dependencies (`lxml` is only for the legacy extractor). Links are root-relative (`/assets/…`, `/inicio/…`) and internal page URLs end with `/`.

### Where things live

| Thing | Where |
|---|---|
| Site constants, nav, `hosting` / `mode` flags, Stripe + form keys | `config.json` |
| Every page: URL, title, description, EN↔ES pair, noindex | `src/pages.json` |
| Page bodies (hand-written HTML sections, each with its own `<style>`) | `src/content/<id>.html` |
| Footers | `src/partials/footer_en.html`, `footer_es.html` |
| Forms (`{{form:11}}` token in a page → rendered form) | `src/forms.json` |
| Shared CSS/JS (header, forms, native widgets) | `src/assets/css/site.css`, `src/assets/js/site.js` |
| Old WordPress URLs → new (301s) | `src/redirects.json` |
| Wrong links inherited from the old site → corrected | `src/link_fixes.json` |
| Originals of images/PDFs (local only — **untracked**) | `media_src/` |
| Deployed copies of media | `docs/assets/img`, `docs/assets/dl` (**committed**) |
| Cloudflare config (assets dir = `docs`, custom domains, Worker entry) | `wrangler.jsonc`, `worker.js` |
| Migration tools (legacy, only to re-extract from a WordPress export) | `tools/extract.py`, `tools/manifest.json`, `tools/forms_from_fluent.py` |

Generated for you: header, footer, language switch, canonical + hreflang, sitemap + robots, `_redirects`, `_headers`, 404. Page ids are `<slug>-<lang>` (e.g. `exp-walls-en`). The page files in `src/content/` are the **source of truth** — edit them directly; re-running the extractor would overwrite them. Hand-built (not extracted) pages: the guide product and download pages. Spanish-only pages (Hazte Aliado, acuerdo, bienvenido, Tu Negocio, aliado-en-proceso) have `"lang": "es"` and no `pair`.

**Adding a page:** create `src/content/<id>.html` (one `<section class="mt-sec"><div class="mt-inner">…`), add an entry to `src/pages.json` (real title ≤ ~60 chars, description ≤ ~155, `pair` if bilingual, `noindex` for utility pages), add to nav in `config.json` only if it belongs in the menu, build, check.

### Media and the 25 MiB rule

- `media_src/` holds originals and is **not in git**. The build **wipes `docs/` and re-copies only the files pages reference, from `media_src/`**. If a file is missing there, the build **silently removes it from `docs/assets`** and the next deploy breaks that image. Before committing any build, open `media_needed.txt`: there must be **no new `MISSING` lines** beyond the known list in Open items.
- **Cloudflare rejects any single asset over 25 MiB.** The guide PDFs were compressed to fit. **The compressed versions are the canonical ones** — keep them in `media_src/` (replace the originals) and keep any uncompressed originals elsewhere, outside the repo, or a rebuild will overwrite them and the deploy will fail.
- `python tools/fetch_media.py` downloads referenced files from the old WordPress site. It cannot fetch files that 404 there.
- Image spec for new photos: 1200×800, ~80% JPG, under 200 KB.
- Paid PDFs are protected **only by obscure filenames and noindex pages**. Never link them from indexable pages or list them in a sitemap. Revisit only if abuse appears.

## Voice

Calm, restrained, observational, human. Written as a founder: personal, lived, not corporate. Destination content is first person ("I came to Campeche expecting…") — intentional and locked.

Never: urgency language, hype, salesy or blogger-y copy, marketing metaphors, exaggerated claims. Never position Maya Tuya as a mass-tourism platform, listicle brand, agency, or influencer project.

## Language

- EN and ES are equals. Never literal translation: preserve meaning, rhythm, intent (Mexican Spanish usage).
- Bilingual pairs move together: change one, change the other.
- Traveler pages: EN + ES. Aliado-facing pages: Spanish-first.
- ES pages live under `/inicio/…`. Every page has an EN↔ES pair where one exists (hreflang is generated).
- Typographic punctuation in visible text (’ “ ” «»); straight quotes only in code/attributes.
- **Aliado benefit copy is vague and evocative** on every page — never state the specific benefit. Hazte Aliado mentions two tiers only, with no pricing. Fundador is never advertised on the site (see Products).

## Design system

```css
--g:     #013220;  /* dark green — primary */
--gold:  #c89e4b;  /* accent */
--gold-d:#9a7828;  /* gold dark — hover */
--cream: #f3eee2;  /* page background — use this, NOT #f2e9d0 */
--ink:   #0c0b09;  /* body text */
--muted: #5a5040;  /* secondary text */
```

Fonts: Playfair Display SC / Playfair Display (headings) · Cormorant Garamond (italic/pull) · Lato (body/labels). No new fonts or colours.

Do **not** set a background colour on a page's widget wrapper div. Section backgrounds are set on the `<section class="mt-sec">` that wraps the widget (dark green sections: Fundador confirmation, Contact, Donations).

## Products and prices (locked)

| Product | Price | Status on site |
|---|---|---|
| The Conscious Traveler | Free, always. A tool/compass — never call it a "guide". | Live |
| Campeche Destination Guide — First Edition | $9.99 USD | Live |
| Mérida Destination Guide — First Edition | $9.99 USD | Live |
| Tu Negocio, Mejor. | $950 MXN (free with Destacado/Fundador) | Live, sold in person / WhatsApp |
| Open Heart, Open Table | $195 USD pp · min 3 · max 10 | **Bookable** |
| From the Walls to the Table | $195 USD pp · min 2 · max 6 | "Available soon" — no price, no form |
| The Gates and The Night | TBD · min 2 · max 6 | "Available soon" — no price, no form |
| Aliado Destacado | $749 MXN/month or $7,490 MXN/year | Active |
| Aliado Fundador | $4,500 MXN one-time, max 7 in Campeche | In person only — **never advertised on the site** |

"Available soon" (EN) / "próximamente" (ES). Experience pages stay live; only the price and booking form are removed. "A la Mesa" is not an offer — do not re-add it.

Never display a price that differs from this table. If a page disagrees, report it.

Experience details that are safe to use in copy:

- Walls to the Table: all-inclusive · morning, ~9:00am, ~3 h plus an open close at the table · bilingual guide · starts at Puerta de Mar.
- Open Heart, Open Table: all-inclusive · 10:00am or 4:00pm only · health checkbox required at booking (dose reduction on request).
- The Gates and The Night: evening · includes 3 drinks.
- Optional transport: fixed fare, offered at booking, never bundled into the headline price. $195 pp is all-inclusive; no itemised billing on the day.
- Tu Negocio, Mejor.: B2B guide, included free with Destacado and Fundador.
- Aliado (free): no monthly cost; in-person visit; directory presence; standards review at 30 days. Destacado founding rate is locked while active; 12-month minimum.
- GetYourGuide is operator-distribution only; GYG affiliate links are permanently ruled out.

## Stripe links

All links are `{{stripe:key}}` tokens resolved from `config.json`. **No `PLACEHOLDER` may ever ship.** Never invent a link. Keys:

`destacado_monthly` · `destacado_annual` · `fundador` · `tu_negocio` (reference only, not used on any page) · `guide_campeche` · `guide_merida` · `contribution`

The Stripe account is live-mode only. The old WooCommerce-era links are dead — never reintroduce them. Aliado links collect business name and phone. Stripe can't enforce the 12-month Destacado minimum; that lives in the acuerdo text. Payment-link URLs and the Web3Forms access key are public by design; **never commit secret keys or API tokens.**

**Acuerdo flow:** Step 1 pay (Destacado/Fundador via Stripe link; free Aliado has no payment) → Step 2 accept via the form → welcome page.

## Download pages (post-payment redirects)

| Route | Files in `assets/dl/` |
|---|---|
| `/tu-negocio-mejor` | `Tu-Negocio-Mejor-9m0ieq.pdf` |
| `/campeche-guide-download` | `Campeche-Guide-EN-fcf6ba.pdf`, `Campeche-Guide-ES-d6a86a.pdf` |
| `/merida-guide-download` | `Merida-Guide-EN-cfbfb40166cc.pdf`, `Merida-Guide-ES-4015616edf73.pdf` |

All **noindex, not in the menu, not in the sitemap**. One page per guide, both languages side by side, same pattern. Files are protected only by obscure filenames — never rename or link them elsewhere. Stripe redirects point to these routes on `mayatuya.com`; do not rename the routes without telling Glancy (the Stripe links must be updated too). The Conscious Traveler download (`/conscious-traveler-download/`, `/inicio/viajero-consciente-descarga/`) is noindex too and is served as `assets/dl/The-Conscious-Traveler.zip`.

## Guide product pages

`/product/campeche-travel-guide` and `/product/merida-travel-guide` — EN and ES, always. Never `/tienda/` or any other path. Both editions are included in one purchase.

## Experience URLs (locked)

Slug rule: full name, no spaces, no punctuation, lowercase.

```
EN: /experiences/fromthewallstothetable
    /experiences/thegatesandthenight
    /experiences/openheartopentable
ES: /inicio/experiencias/delasmurallasalamesa
    /inicio/experiencias/laspuertasylanoche
    /inicio/experiencias/corazonabiertomesaabierta
```

## Forms (Web3Forms)

- All forms POST to `https://api.web3forms.com/submit` with the `config.json` access key (public by design).
- Every form carries a hidden **`botcheck`** honeypot (unchecked checkbox, `display:none`). `build.py` adds it to every rendered form; new forms must too.
- Email to hola@mayatuya.com is the record; the **subject prefix** drives Gmail labels: `[MT booking] <experience> (EN|ES)`, `[MT acuerdo] <tier> (ES)`, `[MT traveler]`, `[MT contact]`, `[MT hazte-aliado]`. Don't change prefixes. **Do not rename form field names** (`first_name`, `guests`, `preferred_date`, `acuerdo_accepted`, `tier`, …) without telling Glancy — they appear in the notification emails.
- Acuerdo forms send: full name, business name, email, `acuerdo_accepted`, `tier`.
- After a successful submit: Conscious Traveler forms → the download page; acuerdo forms → the matching `/bienvenido-aliado…` page; Hazte Aliado → `/inicio/aliado-en-proceso/`; contact and booking show an inline confirmation.
- Open Heart booking form: guests 3–10 (EN and ES). The Walls and Gates forms (11–14) stay defined in `src/forms.json` but are not rendered while those experiences are "available soon".
- Contact email: **hola@mayatuya.com for everyone.** Phone/WhatsApp: +52 938 184 2944. Do not add other addresses.
- Mailchimp: contacts are added manually from form emails (Gmail labels) until an integration is justified by revenue.

## Hosting, DNS and Cloudflare

- Cloudflare Worker name: **`mayatuya`** (must match `name` in `wrangler.jsonc`). Repo is connected to Workers Builds; pushes to `main` build and deploy.
- `config.json`: `"hosting": "cloudflare"`, `"mode": "live"`. Live mode: indexable pages are `index, follow`; pages flagged `noindex` stay `noindex, follow` and out of the sitemap; canonicals, `sitemap.xml` and `robots.txt` use the apex. `"mode": "staging"` still exists as a switch (every page noindex, `new.` canonicals, `Disallow`, no sitemap) — don't set either mode without Glancy's go-ahead.
- `wrangler.jsonc` `routes` lists the custom domains attached to the Worker: `mayatuya.com`, `www.mayatuya.com`, `new.mayatuya.com`. They do **not** appear as ordinary A/CNAME rows in the DNS tab; check Workers → mayatuya → Domains & Routes. If `mayatuya.com` ever stops resolving, check that list first.
- `worker.js` sits in front of the static assets (`run_worker_first`): 301s `www` → apex and adds `X-Robots-Tag: noindex` on any non-apex host (`new.`, `*.workers.dev`).
- `_redirects` / `_headers` are generated into `docs/`: real 301s for old WordPress URLs (including `/wp-sitemap.xml` and `/wp-sitemap-*` → `/sitemap.xml`, live mode only). `/about` → `/about/` is a **307** (Cloudflare's trailing-slash handling) — acceptable.
- **Never, without Glancy's explicit go-ahead:** add, change or delete any DNS record or custom domain; merge risky changes straight to `main`; disable or delete anything in Cloudflare or GitHub. In particular never touch **MX, SPF/DKIM/TXT or autodiscover records** — email depends on them.

## Noindex pages

All acuerdo pages · all confirmation (`/bienvenido-aliado…`) pages · all download pages (Conscious Traveler, Tu Negocio, Campeche guide, Mérida guide) · legal pages (`/privacy`, `/terms`, `/cookies`, ES equivalents) · `/inicio/aliado-en-proceso`. Everything else is indexable on production. Utility pages must stay noindex.

## SEO and redirects

- Every page has its own title and description (`src/pages.json`). Canonical and hreflang are generated; canonical host is `https://mayatuya.com`.
- `sitemap.xml` is written only in live mode and excludes the noindex pages. Note `.gitignore` ignores `*.xml` except `docs/sitemap.xml` — keep that exception or the sitemap won't deploy.
- Old WordPress URLs 301 via `_redirects` (shop, cart, my-account, /home, /hazte-aliado, `/wp-sitemap.xml`, …). Keep them working.
- Not yet done: Organization / WebSite structured data.

## Known issues to fix (small, safe — on a branch)

1. **Windows console:** `build.py` should not crash on `→`. Add `sys.stdout.reconfigure(encoding="utf-8")` near the top (guard with `hasattr`).
2. **Media safety net:** before wiping `docs/`, index the existing `docs/assets/img` and `docs/assets/dl` and use them as a **fallback source** when a referenced file isn't in `media_src/`. A build must never delete a deployed image. Keep the `MISSING` report.
3. **Size check:** `build.py` warns above 50 MB (GitHub's limit). Cloudflare's limit is **25 MiB per file** — change the check to fail on > 25 MiB.
4. Favicon / fonts / flags: Google Fonts and `flagcdn.com` flag images are external; self-hosting is a later optimisation.

## Open items (delete as resolved)

- Bastión "Contact" button on experience pages uses placeholder WhatsApp `52XXXXXXXXXX` — **public now**; needs the real number or hide the button.
- `support@mayatuya.com` may still appear on Contact pages — remove unless Glancy confirms it exists.
- Missing images (the only `MISSING` lines allowed in `media_needed.txt`): `PHOTO.jpg` and seven `gtn-*.jpg` files (`gtn-calle59`, `gtn-casavieja-night`, `gtn-loteria`, `gtn-mercado`, `gtn-opalos`, `gtn-puerta-mar`, `gtn-walls-dusk`).
- Styling pass — deferred (includes unifying the two dark greens, `#0b3d2e` in theme sections vs `#013220`).
- Before relaunching Walls to the Table: price $195, min 2, max 6, and align the hours/copy with Glancy. Before relaunching Gates and the Night: price is TBD; align the meal copy (page says a three-course meal, the Codex says 3 drinks).
- Guide product pages: only the EN pages exist; no ES product page for either guide yet.
- `config.json` still carries `stripe_live_reference` (old, dead links, unused by the build) — remove when Glancy confirms.
- `README.md` still describes GitHub Pages hosting; update when convenient.
- Home hero is inset at the top (`home-card-inset`) — Glancy to say whether it should go edge-to-edge.

## Never

- Invent prices, capacities, claims, testimonials, or Aliado details.
- Add urgency, countdowns, scarcity language, or "limited spots" copy (Fundador is never advertised).
- Put private information in this repo.
- Merge, deploy to production, or change DNS without Glancy's explicit approval.
