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
