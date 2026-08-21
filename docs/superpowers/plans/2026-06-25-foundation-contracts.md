# Foundation & Contracts Implementation Plan (Wave 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `newsletter_archive` Python package with the frozen contracts every later wave depends on: config, logging, retry, the SQLite schema/data layer, the domain models, and a CLI skeleton.

**Architecture:** A single installable package (`pyproject.toml`). `db.py` is the sole owner of the SQLite schema (tables + FTS5); `models.py` defines the dataclasses that are the contract between parser, db, and templates. `config.py` (pydantic-settings) replaces every hardcoded constant. Everything is TDD with an in-memory/tmp SQLite so tests need no network.

**Tech Stack:** Python 3.9, pytest, pydantic-settings (pydantic v2), stdlib `sqlite3` (FTS5 ships with CPython's sqlite), stdlib `logging`.

**Spike validation (already done):** ESP-aware brand identity resolves distinct brands (fixtures pass; `KNOWN_ESP` must include unsubscribe-infra domains like `list-manage.com`, and `List-Unsubscribe` parsing must iterate all hosts). Playwright full-render thumbnails are faithful when images are localized first. These inform Wave 2/3, not this wave.

---

## File structure (this wave)
- Create: `pyproject.toml` — package metadata + deps + pytest config
- Create: `newsletter_archive/__init__.py`
- Create: `newsletter_archive/config.py` — `Settings` (pydantic-settings)
- Create: `newsletter_archive/logging_conf.py` — `configure_logging()` + `get_logger()`
- Create: `newsletter_archive/retry.py` — `retry()` decorator
- Create: `newsletter_archive/models.py` — `Brand, Newsletter, Link, Image, Pixel, Audit`
- Create: `newsletter_archive/db.py` — `connect()`, `bootstrap_schema()`, insert/query helpers
- Create: `newsletter_archive/cli.py` — argparse skeleton (`ingest|build|backfill|migrate|brand`)
- Create: `tests/__init__.py`, `tests/test_config.py`, `tests/test_logging.py`, `tests/test_retry.py`, `tests/test_models.py`, `tests/test_db_schema.py`, `tests/test_cli.py`
- Create: `.gitignore`

The existing `src/`, `templates/`, `process_email.py`, `patch_viewers*.py`, `injector.py` are NOT touched in this wave (refactored/deleted in later waves).

---

### Task 1: Package skeleton + pytest + .gitignore

**Files:**
- Create: `pyproject.toml`
- Create: `newsletter_archive/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`
- Test: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_smoke.py
def test_package_imports():
    import newsletter_archive
    assert newsletter_archive.__version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'newsletter_archive'`

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[project]
name = "newsletter-archive"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
  "beautifulsoup4>=4.12",
  "lxml>=5.0",
  "requests>=2.31",
  "jinja2>=3.1",
  "boto3>=1.34",
  "pydantic-settings>=2.2",
  "tldextract>=5.1",
  "playwright>=1.44",
  "Pillow>=10.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
archive = "newsletter_archive.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

```python
# newsletter_archive/__init__.py
__version__ = "0.1.0"
```

```python
# tests/__init__.py
```

```gitignore
# .gitignore
__pycache__/
*.pyc
.venv/
venv/
dist/
build/
*.egg-info/
.pytest_cache/
.playwright-mcp/
# generated site + local DB artifacts (never commit binaries again)
/dist/
*.sqlite
*.sqlite-*
```

- [ ] **Step 4: Install package (editable) and run test**

Run: `pip install -e ".[dev]" && python -m pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml newsletter_archive/__init__.py tests/__init__.py tests/test_smoke.py .gitignore
git commit -m "feat: scaffold newsletter_archive package + pytest"
```

---

### Task 2: `config.py` — Settings

**Files:**
- Create: `newsletter_archive/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import importlib
from newsletter_archive import config

def test_defaults_and_env_override(monkeypatch):
    monkeypatch.setenv("ARCHIVE_GMAIL_USER", "me@example.com")
    monkeypatch.setenv("ARCHIVE_TARGET_LABEL", "X/labels")
    s = config.Settings()
    assert s.gmail_user == "me@example.com"
    assert s.target_label == "X/labels"
    # defaults preserved
    assert s.db_path == "archive.db"
    assert s.image_workers == 5
    assert s.redirect_workers == 10
    assert s.http_timeout == 15
    assert "Mozilla" in s.user_agent
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError`/`ImportError` (no `Settings`)

- [ ] **Step 3: Write minimal implementation**

```python
# newsletter_archive/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime config. Replaces every hardcoded constant in the old code."""
    model_config = SettingsConfigDict(env_prefix="ARCHIVE_", env_file=".env", extra="ignore")

    # Gmail / IMAP
    gmail_user: str = ""
    gmail_password: str = ""
    target_label: str = "Github/archive-newsletters"
    batch_size: int = 9999
    force_update: bool = False

    # Storage
    db_path: str = "archive.db"
    site_base_url: str = "http://localhost:8000"

    # R2 (S3-compatible) — filled in Wave 2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "newsletter-assets"
    r2_public_base_url: str = ""

    # Tuning
    image_workers: int = 5
    redirect_workers: int = 10
    http_timeout: int = 15
    resolve_redirects: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add newsletter_archive/config.py tests/test_config.py
git commit -m "feat: pydantic Settings replacing hardcoded config"
```

---

### Task 3: `logging_conf.py` — structured logging

**Files:**
- Create: `newsletter_archive/logging_conf.py`
- Test: `tests/test_logging.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_logging.py
import json, logging
from newsletter_archive import logging_conf

def test_logger_emits_json(capsys):
    logging_conf.configure_logging(level="INFO")
    log = logging_conf.get_logger("test")
    log.info("hello", extra={"email_id": "abc123"})
    err = capsys.readouterr().err.strip().splitlines()[-1]
    rec = json.loads(err)
    assert rec["message"] == "hello"
    assert rec["level"] == "INFO"
    assert rec["email_id"] == "abc123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_logging.py -v`
Expected: FAIL — no `configure_logging`

- [ ] **Step 3: Write minimal implementation**

```python
# newsletter_archive/logging_conf.py
import json, logging, sys

_RESERVED = set(logging.makeLogRecord({}).__dict__.keys()) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        out = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k not in _RESERVED:
                out[k] = v
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_logging.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add newsletter_archive/logging_conf.py tests/test_logging.py
git commit -m "feat: structured JSON logging"
```

---

### Task 4: `retry.py` — retry/backoff decorator

**Files:**
- Create: `newsletter_archive/retry.py`
- Test: `tests/test_retry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_retry.py
import pytest
from newsletter_archive.retry import retry

def test_retries_then_succeeds():
    calls = {"n": 0}
    @retry(tries=3, delay=0, exceptions=(ValueError,))
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("boom")
        return "ok"
    assert flaky() == "ok"
    assert calls["n"] == 3

def test_reraises_after_exhausting():
    @retry(tries=2, delay=0, exceptions=(ValueError,))
    def always_fail():
        raise ValueError("nope")
    with pytest.raises(ValueError):
        always_fail()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_retry.py -v`
Expected: FAIL — no module `retry`

- [ ] **Step 3: Write minimal implementation**

```python
# newsletter_archive/retry.py
import functools, time
from .logging_conf import get_logger

log = get_logger("retry")


def retry(tries: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions=(Exception,)):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            d, last = delay, None
            for attempt in range(1, tries + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last = e
                    log.warning("retry", extra={"fn": fn.__name__, "attempt": attempt, "error": str(e)})
                    if attempt < tries:
                        time.sleep(d)
                        d *= backoff
            raise last
        return wrapper
    return deco
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_retry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add newsletter_archive/retry.py tests/test_retry.py
git commit -m "feat: retry/backoff decorator"
```

---

### Task 5: `models.py` — domain dataclasses

**Files:**
- Create: `newsletter_archive/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from newsletter_archive.models import Brand, Newsletter, Link, Image, Pixel, Audit

def test_newsletter_holds_brand_and_signals():
    b = Brand(key="sephora.com", slug="sephora", display_name="Sephora")
    n = Newsletter(
        id="abc123", brand_key=b.key, subject="Sale", slug="sale-abc123",
        sender_display="Sephora", from_domain="email.sephora.com",
        list_id=None, dkim_d="sephora.com", preheader="hi",
        date_iso="2026-01-01T00:00:00+00:00", date_rec="01/01/2026", date_arch="01/01/2026",
        reading_time="1 min", crm="Salesforce", email_size=1024,
        html_key="html/abc123.html", thumb_url=None,
    )
    assert n.brand_key == "sephora.com"
    assert n.dkim_d == "sephora.com"

def test_audit_defaults():
    a = Audit(newsletter_id="abc123")
    assert a.link_count == 0
    assert a.unsubscribe_found is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — no module `models`

- [ ] **Step 3: Write minimal implementation**

```python
# newsletter_archive/models.py
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Brand:
    key: str                 # canonical key (registrable domain or "name:<display>")
    slug: str
    display_name: str = ""
    category: Optional[str] = None
    homepage_url: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    email_count: int = 0


@dataclass
class Newsletter:
    id: str
    brand_key: str
    subject: str
    slug: str
    sender_display: str = ""
    from_domain: Optional[str] = None
    list_id: Optional[str] = None
    dkim_d: Optional[str] = None
    preheader: str = ""
    date_iso: str = ""
    date_rec: str = ""
    date_arch: str = ""
    reading_time: str = ""
    crm: Optional[str] = None
    email_size: int = 0
    html_key: Optional[str] = None
    thumb_url: Optional[str] = None


@dataclass
class Link:
    newsletter_id: str
    idx: int
    txt: str = ""
    original_url: str = ""
    final_url: str = ""
    domain: str = ""
    is_tracking: bool = False
    is_secure: bool = True
    is_dev: bool = False
    redirect_chain: list = field(default_factory=list)
    audit_date: Optional[str] = None


@dataclass
class Image:
    sha256: str
    url: str
    content_type: str = ""
    bytes: int = 0


@dataclass
class Pixel:
    newsletter_id: str
    url: str = ""
    domain: str = ""
    status: str = ""


@dataclass
class Audit:
    newsletter_id: str
    subject_check: str = ""
    unsubscribe_found: bool = False
    link_count: int = 0
    images_no_alt: int = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add newsletter_archive/models.py tests/test_models.py
git commit -m "feat: domain dataclasses (Brand/Newsletter/Link/Image/Pixel/Audit)"
```

---

### Task 6: `db.py` — schema bootstrap, FTS5, round-trip

**Files:**
- Create: `newsletter_archive/db.py`
- Test: `tests/test_db_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db_schema.py
from newsletter_archive import db
from newsletter_archive.models import Brand, Newsletter

def test_bootstrap_and_brand_newsletter_roundtrip(tmp_path):
    conn = db.connect(str(tmp_path / "t.sqlite"))
    db.bootstrap_schema(conn)
    bid = db.upsert_brand(conn, Brand(key="sephora.com", slug="sephora", display_name="Sephora"))
    db.insert_newsletter(conn, Newsletter(
        id="n1", brand_key="sephora.com", subject="Été soldes", slug="ete-soldes-n1",
        preheader="profitez", date_iso="2026-01-01T00:00:00+00:00",
    ), brand_id=bid, body_text="profitez des soldes d'été")
    rows = db.list_newsletters_for_brand(conn, "sephora.com")
    assert len(rows) == 1 and rows[0]["subject"] == "Été soldes"

def test_fts_diacritics_insensitive(tmp_path):
    conn = db.connect(str(tmp_path / "t.sqlite"))
    db.bootstrap_schema(conn)
    bid = db.upsert_brand(conn, Brand(key="b.com", slug="b", display_name="B"))
    db.insert_newsletter(conn, Newsletter(id="n1", brand_key="b.com", subject="Été", slug="ete-n1"),
                         brand_id=bid, body_text="soldes été chaudes")
    # query without accent must match accented content (remove_diacritics 2)
    ids = db.search(conn, "ete")
    assert "n1" in ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_db_schema.py -v`
Expected: FAIL — no module `db`

- [ ] **Step 3: Write minimal implementation**

```python
# newsletter_archive/db.py
import sqlite3
from typing import List, Optional
from .models import Brand, Newsletter

SCHEMA = """
CREATE TABLE IF NOT EXISTS brands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL, slug TEXT UNIQUE NOT NULL, display_name TEXT,
  category TEXT, homepage_url TEXT, first_seen TEXT, last_seen TEXT,
  email_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS newsletters (
  id TEXT PRIMARY KEY,
  brand_id INTEGER REFERENCES brands(id),
  brand_key TEXT,
  subject TEXT NOT NULL, slug TEXT,
  sender_display TEXT, from_domain TEXT, list_id TEXT, dkim_d TEXT,
  preheader TEXT, date_iso TEXT, date_rec TEXT, date_arch TEXT,
  reading_time TEXT, crm TEXT, email_size INTEGER,
  html_key TEXT, thumb_url TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS images (
  sha256 TEXT PRIMARY KEY, url TEXT NOT NULL, content_type TEXT, bytes INTEGER,
  first_seen TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS newsletter_images (
  newsletter_id TEXT, sha256 TEXT, position INTEGER, original_src TEXT,
  PRIMARY KEY (newsletter_id, position)
);
CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT, newsletter_id TEXT, idx INTEGER,
  txt TEXT, original_url TEXT, final_url TEXT, domain TEXT,
  is_tracking INTEGER, is_secure INTEGER, is_dev INTEGER,
  redirect_chain TEXT, audit_date TEXT
);
CREATE TABLE IF NOT EXISTS pixels (
  id INTEGER PRIMARY KEY AUTOINCREMENT, newsletter_id TEXT, url TEXT, domain TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS audits (
  newsletter_id TEXT PRIMARY KEY, subject_check TEXT, unsubscribe_found INTEGER,
  link_count INTEGER, images_no_alt INTEGER
);
CREATE VIRTUAL TABLE IF NOT EXISTS newsletters_fts USING fts5(
  newsletter_id UNINDEXED, subject, brand_display, preheader, body,
  tokenize='unicode61 remove_diacritics 2'
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def bootstrap_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_brand(conn: sqlite3.Connection, b: Brand) -> int:
    cur = conn.execute(
        """INSERT INTO brands (key, slug, display_name, category, homepage_url, first_seen, last_seen, email_count)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(key) DO UPDATE SET
             display_name=excluded.display_name, last_seen=excluded.last_seen""",
        (b.key, b.slug, b.display_name, b.category, b.homepage_url, b.first_seen, b.last_seen, b.email_count),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM brands WHERE key=?", (b.key,)).fetchone()
    return row["id"]


def insert_newsletter(conn: sqlite3.Connection, n: Newsletter, brand_id: int, body_text: str = "") -> None:
    conn.execute(
        """INSERT OR REPLACE INTO newsletters
           (id, brand_id, brand_key, subject, slug, sender_display, from_domain, list_id, dkim_d,
            preheader, date_iso, date_rec, date_arch, reading_time, crm, email_size, html_key, thumb_url)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (n.id, brand_id, n.brand_key, n.subject, n.slug, n.sender_display, n.from_domain, n.list_id,
         n.dkim_d, n.preheader, n.date_iso, n.date_rec, n.date_arch, n.reading_time, n.crm,
         n.email_size, n.html_key, n.thumb_url),
    )
    brand = conn.execute("SELECT display_name FROM brands WHERE id=?", (brand_id,)).fetchone()
    conn.execute("DELETE FROM newsletters_fts WHERE newsletter_id=?", (n.id,))
    conn.execute(
        "INSERT INTO newsletters_fts (newsletter_id, subject, brand_display, preheader, body) VALUES (?,?,?,?,?)",
        (n.id, n.subject, brand["display_name"] if brand else "", n.preheader, body_text),
    )
    conn.commit()


def list_newsletters_for_brand(conn: sqlite3.Connection, brand_key: str) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM newsletters WHERE brand_key=? ORDER BY date_iso DESC", (brand_key,)
    ).fetchall()


def search(conn: sqlite3.Connection, query: str) -> List[str]:
    rows = conn.execute(
        "SELECT newsletter_id FROM newsletters_fts WHERE newsletters_fts MATCH ? ORDER BY rank",
        (query,),
    ).fetchall()
    return [r["newsletter_id"] for r in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_db_schema.py -v`
Expected: PASS (both tests; the diacritics test proves `remove_diacritics 2` works)

- [ ] **Step 5: Commit**

```bash
git add newsletter_archive/db.py tests/test_db_schema.py
git commit -m "feat: SQLite schema + FTS5 data layer (the contract)"
```

---

### Task 7: `cli.py` — argparse skeleton

**Files:**
- Create: `newsletter_archive/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
import pytest
from newsletter_archive import cli

def test_subcommands_registered():
    parser = cli.build_parser()
    # parsing each subcommand should not error
    for sub in ["ingest", "build", "backfill", "migrate"]:
        ns = parser.parse_args([sub])
        assert ns.command == sub

def test_brand_subcommand_has_actions():
    parser = cli.build_parser()
    ns = parser.parse_args(["brand", "set-category", "sephora.com", "beauty"])
    assert ns.command == "brand" and ns.action == "set-category"
    assert ns.key == "sephora.com" and ns.value == "beauty"

def test_unknown_command_exits():
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["frobnicate"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — no module `cli`

- [ ] **Step 3: Write minimal implementation**

```python
# newsletter_archive/cli.py
import argparse
from .logging_conf import configure_logging, get_logger

log = get_logger("cli")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="archive", description="Newsletter brand archive")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="fetch new emails from Gmail and process them")
    sub.add_parser("build", help="render the static site from SQLite")
    sub.add_parser("backfill", help="dedup existing images into R2")
    m = sub.add_parser("migrate", help="import existing docs/ archives into SQLite")
    m.add_argument("--reingest", action="store_true", help="re-fetch from Gmail for true headers")
    b = sub.add_parser("brand", help="manage brands")
    bsub = b.add_subparsers(dest="action", required=True)
    sc = bsub.add_parser("set-category")
    sc.add_argument("key"); sc.add_argument("value")
    mg = bsub.add_parser("merge")
    mg.add_argument("key"); mg.add_argument("value")
    return p


def main(argv=None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    # Wave 1: handlers are stubs; later waves wire them to pipeline/build/migrate.
    log.info("command", extra={"command": args.command})
    raise SystemExit(
        f"'{args.command}' not implemented yet (Wave 1 skeleton)."
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add newsletter_archive/cli.py tests/test_cli.py
git commit -m "feat: CLI skeleton (ingest/build/backfill/migrate/brand)"
```

---

### Task 8: Full suite green + wave checkpoint

- [ ] **Step 1: Run the whole suite**

Run: `python -m pytest -v`
Expected: ALL PASS (smoke, config, logging, retry, models, db_schema×2, cli×3)

- [ ] **Step 2: Verify the package entrypoint exists**

Run: `archive --help`
Expected: usage text listing `ingest build backfill migrate brand`

- [ ] **Step 3: Commit any final touch-ups**

```bash
git add -A && git commit -m "chore: Wave 1 foundation complete" || echo "nothing to commit"
```

---

## Self-review (done by plan author)
- **Spec coverage (Wave-1 slice):** package ✓ (T1), config externalization ✓ (T2), logging ✓ (T3),
  retry ✓ (T4), models contract ✓ (T5), SQLite schema + FTS5 diacritics ✓ (T6), CLI surface ✓ (T7).
  Brand identity / assets / thumbnails / parser refactor / pages / migration are later waves by design.
- **Placeholder scan:** none — every code step is complete and runnable.
- **Type consistency:** `Newsletter.brand_key`, `Brand.key`, `db.upsert_brand`/`insert_newsletter`/
  `list_newsletters_for_brand`/`search` names are used identically across tasks and tests.

## Next plans (written after Wave 1 lands, against the frozen contracts)
- `…-parser-refactor.md` — move image-write half of `download_images_parallel` to `assets.store`; characterization tests vs current parser output.
- `…-brand-identity.md` — `brands/identify.py` + `esp_domains.py` (spike-validated chain; include `list-manage.com`; iterate all `List-Unsubscribe` hosts).
- `…-assets-thumbnails.md` — `assets/{store,r2,thumbnail}.py`; Playwright render-after-localize; R2 CORS.
- `…-search-index.md` — `build/search_index.py` (search.json + facets).
- `…-pipeline-site-migration.md` — `ingest/pipeline.py`, `build/site.py` + templates, `archive migrate --reingest`.
- `…-deploy.md` — `ingest.yml`/`deploy.yml`, Pages, `noindex`.
