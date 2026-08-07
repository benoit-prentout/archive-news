# Design Spec — `archive-news` → milled-style brand newsletter archive (V1)

**Date:** 2026-06-25
**Status:** Approved (brainstorming) — pending implementation plan
**Branch:** `rebuild/milled-brand-archive`

## 1. Problem & goal

`archive-news` today polls a Gmail label over IMAP every 30 min (GitHub Actions), sanitizes
newsletter HTML, **downloads every image into the repo**, renders a Jinja2 viewer, and **commits
everything to `docs/`** for GitHub Pages. It is a single-account, date-sorted personal archive with a
strong analysis layer.

Measured pain: `.git` = 157 MB, `docs/` = 106 MB (99 MB images), 470 image files → 274 unique
(42% byte-identical duplicates), growing every 30 min forever.

**Goal:** rebuild it into a **personal/agency milled.com-style archive** — *brand-organized*, so you
can browse **every newsletter a given brand has sent**, with a visual thumbnail grid and faceted
search, keeping the existing analysis ("testing") features as **brand-level competitive intelligence**.

This is honestly a *personal competitive-intel archive shaped like milled* — its corpus is only what
*you* subscribe to in one Gmail account, not milled's 98K-brand firehose. The design owns that framing.

## 2. Decisions (locked via brainstorming)

| Area | Decision |
|---|---|
| Language/foundation | Keep **Python**; **SQLite** = source of truth; **Cloudflare R2** for images + thumbnails; deploy to **Cloudflare Pages** |
| Scale/serving | Personal/agency **static site** (tens–hundreds of brands, low-thousands of emails); graduation path to dynamic noted |
| Visibility | **Public but `noindex`** — shareable by URL, blocked from search engines, logos self-hosted (never hotlinked), takedown path |
| Thumbnails | **Headless screenshot** (Playwright) |
| Categories | **Manual** |
| Scope | **Lean V1 + iterate** (this spec = V1) |

## 3. Challenges resolved

- **Brand identity ≠ naive `tldextract`.** Brands often send via shared ESP domains
  (`shopifyemail.com`, `mailchimpapp.com`, `klaviyomail.com`) where eTLD+1 / DKIM `d=` = the ESP, not
  the brand — naive keying collapses distinct brands into one. V1 uses an **ESP-aware fallback chain** (§5).
- **Playwright thumbnails are the riskiest UX piece** → de-risked by a **spike first**, full-height
  render + smart top-crop on real emails, before architecture commits.
- **Scope = several independent subsystems** → decomposed into sub-projects that double as the
  sub-agent work split (§9).

## 4. Architecture

```
Gmail IMAP cron (*/30)
   ↓ parse (reuse parser.py)
   ├─ identify BRAND (ESP-aware chain)        ──► brands
   ├─ images → R2 (SHA-256 dedup)
   ├─ Playwright full-render screenshot → R2   ──► thumb_url
   └─ rows → SQLite (archive.db = source of truth)
archive.db change → build (render from SQLite)
   ├─ home visual feed     /
   ├─ brand pages          /<brand-slug>/
   ├─ email viewer         /<brand-slug>/<email-slug>/
   └─ search.json (+facets: brand, ESP, date) → MiniSearch, client-side
   ↓ dist/ → Cloudflare Pages (robots: noindex)
```

### Package layout (`pyproject.toml`, installable)
```
newsletter_archive/
  config.py        # pydantic-settings; replaces ALL hardcoded consts
  logging_conf.py  # structured JSON logging; removes print()
  retry.py         # retry+backoff for IMAP + HTTP + R2 PUT
  db.py            # SQLite connection, schema bootstrap, FTS5, migrations — SOLE schema owner  [CONTRACT]
  models.py        # dataclasses: Brand, Newsletter, Link, Image, Pixel, Audit                  [CONTRACT]
  ingest/imap_client.py  # + retry/logging/config; captures From, DKIM d=, List-Id, List-Unsubscribe
  ingest/pipeline.py     # orchestrator: email → parser → brand identify → assets → thumbnail → db
  brands/identify.py     # ESP-aware brand resolution
  brands/esp_domains.py  # KNOWN_ESP shared-sending domains (seeded from CRM_PATTERNS + curated)
  parsing/parser.py      # current parser.py; CRM/detect/clean/resolve UNTOUCHED; image half → assets.store
  assets/store.py        # download → sha256 → dedup → PUT R2 if new → URL (the dedup engine)
  assets/r2.py           # boto3 S3-compatible R2 client
  assets/thumbnail.py    # Playwright full-render screenshot → smart crop → webp → sha256 → R2
  build/site.py          # render home/brand/email pages from SQLite (Jinja2)
  build/search_index.py  # search.json incl. facet fields
  cli.py                 # archive ingest | build | backfill | migrate | brand (set-category/merge)
  templates/             # home.html (grid), brand.html, email.html (viewer crown jewel)
tests/                   # parser_crm, parser_links, brand_identify, assets_dedup, thumbnail, db_schema, search + fixtures/
.github/workflows/  ingest.yml (cron, Playwright chromium; commits archive.db only) ; deploy.yml (on db change → Pages)
```

## 5. Brand identity — ESP-aware fallback chain (`brands/identify.py`)

From captured headers, derive the brand **key** by precedence, skipping shared-ESP domains:
1. **DMARC-aligned From org-domain** (registrable via `tldextract`) **if not in `KNOWN_ESP`** — e.g. `email.sephora.com` → `sephora.com`.
2. else **`List-Id` host** domain (usually brand-specific even via an ESP).
3. else **`List-Unsubscribe`** mailto/URL host domain.
4. else **normalized From display name** (last resort).

Store all raw signals (`from_domain`, `dkim_d`, `list_id`, `sender_display`) on the newsletter so a
wrong guess is fixable via `archive brand merge`. Upsert `brands` by key; `display_name` =
most-frequent From display; `category` left null (manual). `KNOWN_ESP` seeds from ESP sending domains
already in `CRM_PATTERNS` + a curated list (`shopifyemail.com`, `mailchimpapp.com`/`rsgsv.net`/`mcsv.net`,
`klaviyomail.com`, `sendgrid.net`, …).

## 6. Data model (SQLite)

```sql
CREATE TABLE brands (
  id INTEGER PRIMARY KEY, key TEXT UNIQUE, slug TEXT UNIQUE, display_name TEXT,
  category TEXT, homepage_url TEXT, first_seen TEXT, last_seen TEXT, email_count INTEGER DEFAULT 0);
CREATE TABLE newsletters (
  id TEXT PRIMARY KEY, brand_id INTEGER REFERENCES brands(id), subject TEXT, slug TEXT,
  sender_display TEXT, from_domain TEXT, list_id TEXT, dkim_d TEXT,
  preheader TEXT, date_iso TEXT, date_rec TEXT, date_arch TEXT, reading_time TEXT,
  crm TEXT, email_size INTEGER, html_key TEXT, thumb_url TEXT, created_at TEXT);
CREATE TABLE images (sha256 TEXT PRIMARY KEY, url TEXT, content_type TEXT, bytes INTEGER, first_seen TEXT);
CREATE TABLE newsletter_images (newsletter_id TEXT, sha256 TEXT, position INTEGER, original_src TEXT,
  PRIMARY KEY (newsletter_id, position));
CREATE TABLE links (newsletter_id TEXT, idx INTEGER, txt TEXT, original_url TEXT, final_url TEXT,
  domain TEXT, is_tracking INT, is_secure INT, is_dev INT, redirect_chain JSON, audit_date TEXT);
CREATE TABLE pixels (newsletter_id TEXT, url TEXT, domain TEXT, status TEXT);
CREATE TABLE audits (newsletter_id TEXT PRIMARY KEY, subject_check TEXT, unsubscribe_found INT,
  link_count INT, images_no_alt INT);
CREATE VIRTUAL TABLE newsletters_fts USING fts5(subject, brand_display, preheader, body,
  content='', tokenize='unicode61 remove_diacritics 2');   -- French content
```
Email slug = `kebab(subject)` + short hash; brand slug from key/display.

## 7. Assets, pages, search

- **Dedup** (`assets/store.py`): replace the local-file half of `download_images_parallel`
  (parser.py ~232–274) with download → sha256 → reuse-or-PUT. Bucket `newsletter-assets`:
  `images/<sha[0:2]>/<sha[2:4]>/<sha>.<ext>`, `thumbs/<sha>.webp`, `html/<id>.html`,
  `Cache-Control: immutable`. **CORS policy** allowing GET from the site origin (required for the
  viewer's zip export, else zips come out image-less).
- **Thumbnails** (`assets/thumbnail.py`): Playwright loads sanitized HTML (images → R2), full-height
  render, smart top-crop to a webp tile, sha256 → R2, store `thumb_url`.
- **Pages:** Home `/` (thumbnail grid + client facet filters); Brand `/<brand-slug>/` (intelligence
  header: ESP used, send cadence, avg links, tracking rate, clipping-risk from aggregated audits +
  chronological grid of all the brand's newsletters — *the core ask*); Email
  `/<brand-slug>/<email-slug>/` (crown-jewel viewer). `robots.txt`/meta `noindex`, footer takedown note.
- **Search:** prebuilt `search.json` + MiniSearch (facets: brand, ESP, date). FTS5 kept populated so a
  later sql.js/WASM or search-Worker upgrade is non-destructive.

## 8. Migration of the 52 existing archives

Prefer **`archive migrate --reingest`** from Gmail (idempotent via deterministic `id`) — recovers the
**real From/DKIM/List-Id headers** needed for correct brand identity + fresh thumbnails. **Fallback**
for emails Gmail no longer holds: parse `docs/<id>/index.html` (`emailLinks`/`content`) →
links/HTML→R2/FTS, backfill images via dedup, key brand by display-name only (flag for manual `merge`),
screenshot stored HTML. Validate: counts match, brands resolve, 3 spot-checked viewers render
identically, thumbnails exist. Keep `docs/` until validated. Run migration **before** any history rewrite.

## 9. Execution: sub-agent-driven, contract-first

- **Spike (first, solo):** throwaway prototype of ESP-aware brand identity on real Gmail + Playwright
  thumbnail quality on real emails. Gates the architecture.
- **Wave 1 — Contracts (sequential):** package skeleton, `config`, `logging`, `db.py` schema, `models.py`. Freeze first.
- **Wave 2 — Fan-out (parallel sub-agents):** ① parser refactor + characterization tests · ② brand
  identity + esp_domains + tests · ③ assets store/r2/thumbnail + tests · ④ search_index.
- **Wave 3 — Consumers (sequential):** `ingest/pipeline.py`, then `build/site.py` + templates, then `archive migrate --reingest`.
- **Wave 4 — Deploy:** workflows, R2 CORS, Pages, `noindex`, end-to-end verification.

## 10. Cleanup

Delete `patch_viewers*.py` (4), `injector.py`, empty `static/`+`test_output/`, `streamlit` dep; after
migration validates, the `docs/<id>/` binaries (optional `git filter-repo` to purge 99 MB history).
Externalize all hardcoded config. Add tests (currently zero) across CRM, link/pixel audit, brand
identity, dedup, thumbnail, DB+FTS5 diacritics, search.

## 11. V2 backlog (deferred)

Logos (fetch + store in R2, initials fallback), manual **category pages** + taxonomy, global &
per-brand **RSS/Atom/JSON feeds**, advanced/boolean search, richer brand-intelligence charts,
sql.js/WASM or search-Worker upgrade at scale.

## 12. Risks & tradeoffs

- **Brand identity** is the deepest risk; fallback chain + stored raw signals + manual `merge` are the net.
- **Playwright** is the heaviest dep (chromium in CI ~1–2 min); thumbnails cached in R2 → steady-state cheap.
- **R2 CORS** for zip export — miss it → image-less zips.
- **Static-gen ceiling** — fine for personal/agency; graduate to dynamic + Meilisearch/Elastic for milled-scale.
- **Diacritics** — preserve FTS5 `remove_diacritics 2` + existing zero-width-char stripping.
- **`noindex` ≠ zero risk** — still public-by-URL republishing; logos self-hosted, takedown path.

## 13. Verification (end-to-end)

1. `pytest` green incl. brand identity (`email.sephora.com`→`sephora`; `shopifyemail.com` From → keyed
   by List-Id/display, NOT collapsed; `merge`), thumbnail produced, FTS5 accented-term query.
2. `archive backfill` → R2 images ≈ 274 (dedup); every newsletter has `thumb_url`.
3. `archive migrate --reingest` → brands resolve; counts match; 3 brand pages + 3 email pages render
   (badges, dark mode, zip-with-images via CORS).
4. `archive build` → home grid renders thumbnails; faceted search filters by brand/ESP/date; `noindex` present.
5. Send a real newsletter → `archive ingest` → brand resolved, image dedup, thumbnail, viewer, brand page
   updated — repo gains **no binaries**.
