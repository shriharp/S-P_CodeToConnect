"""Small dependency-free retry policy for public provider requests."""

import time
import urllib.error


class ProviderRequestError(RuntimeError):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def retry_after_seconds(error: urllib.error.HTTPError) -> float | None:
    value = error.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def request_with_backoff(request, *, attempts: int = 2, timeout: int = 15):
    delay = 1.0
    for attempt in range(attempts):
        try:
            return request(timeout=timeout)
        except urllib.error.HTTPError as exc:
            retry_after = retry_after_seconds(exc)
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if not retryable or attempt == attempts - 1:
                raise ProviderRequestError(
                    f"HTTP {exc.code}: {exc.reason}", retry_after
                ) from exc
            time.sleep(retry_after if retry_after is not None else delay)
            delay = min(delay * 2, 30.0)
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt == attempts - 1:
                raise ProviderRequestError(str(exc)) from exc
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
