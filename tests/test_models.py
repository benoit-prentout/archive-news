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
