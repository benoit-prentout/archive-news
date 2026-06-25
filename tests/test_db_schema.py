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
    ids = db.search(conn, "ete")
    assert "n1" in ids
