BACKOFF_BASE_S = 2
def _backoff_delay(attempt: int) -> float:
    return BACKOFF_BASE_S * (2 ** attempt)

MAX_RETRIES = 3
