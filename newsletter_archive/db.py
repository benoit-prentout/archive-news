import sqlite3
from typing import List
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
  newsletter_id TEXT REFERENCES newsletters(id) ON DELETE CASCADE, sha256 TEXT, position INTEGER, original_src TEXT,
  PRIMARY KEY (newsletter_id, position)
);
CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT, newsletter_id TEXT REFERENCES newsletters(id) ON DELETE CASCADE, idx INTEGER,
  txt TEXT, original_url TEXT, final_url TEXT, domain TEXT,
  is_tracking INTEGER, is_secure INTEGER, is_dev INTEGER,
  redirect_chain TEXT, audit_date TEXT
);
CREATE TABLE IF NOT EXISTS pixels (
  id INTEGER PRIMARY KEY AUTOINCREMENT, newsletter_id TEXT REFERENCES newsletters(id) ON DELETE CASCADE, url TEXT, domain TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS audits (
  newsletter_id TEXT PRIMARY KEY REFERENCES newsletters(id) ON DELETE CASCADE, subject_check TEXT, unsubscribe_found INTEGER,
  link_count INTEGER, images_no_alt INTEGER
);
CREATE VIRTUAL TABLE IF NOT EXISTS newsletters_fts USING fts5(
  newsletter_id UNINDEXED, subject, brand_display, preheader, body,
  tokenize='unicode61 remove_diacritics 2'
);
CREATE INDEX IF NOT EXISTS idx_newsletters_brand_key
  ON newsletters(brand_key, date_iso DESC);
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
    conn.execute(
        # NOTE: slug, category, first_seen are intentionally immutable after first insert
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
    # `with conn:` commits on success / rolls back on error, keeping the newsletter row
    # and its FTS row atomic (no searchable-gap if the process dies mid-write).
    with conn:
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
