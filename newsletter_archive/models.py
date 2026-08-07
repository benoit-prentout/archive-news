from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Brand:
    key: str
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
