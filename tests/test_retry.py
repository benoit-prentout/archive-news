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
