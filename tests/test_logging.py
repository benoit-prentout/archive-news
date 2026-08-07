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
