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
