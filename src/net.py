"""Network plumbing shared by every module that downloads data (`data_loader`, `market_value`).

Three problems this project has actually hit, solved once here rather than per caller:

1. **TLS verification behind an HTTPS-intercepting antivirus.** Avast re-signs every HTTPS
   certificate with its own root, which Windows trusts but Python's bundled `certifi` doesn't —
   and Avast rotates that root, so the old "append the cert to certifi's bundle" fix silently
   broke again months later (see docs/ML_TOOLING.md). `use_os_trust_store` routes verification
   through the operating system's own certificate store instead, which follows those rotations
   (and any corporate proxy's root) automatically.
2. **Transient failures on long bulk pulls.** StatsBomb's open data is served file-by-file from
   `raw.githubusercontent.com`: a multi-thousand-match pull has hit a one-off `IncompleteRead`
   and, separately, `429 Too Many Requests`. `with_retries` retries exactly those failure
   classes with exponential backoff (honouring `Retry-After`), and fails fast on everything else
   — a 404 (e.g. a match with no 360 file) or a certificate error will not fix itself by waiting.
3. **Half-written cache files.** A run killed mid-write would leave a truncated file that every
   later run trusts; `write_atomically` makes each cache write all-or-nothing.

Deliberately no import of `requests` at module level: the deployed Streamlit app imports
`data_loader` (via `similarity`) but never downloads anything, so this module must stay cheap and
dependency-free to import.
"""

import http.client
import os
import random
import time
import urllib.error
from pathlib import Path

# Status codes worth waiting out: rate limiting and the usual "server/CDN hiccup" family.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
# Rate limits clear on a scale of tens of seconds to minutes, not the ~seconds a dropped
# connection needs — so a 429 starts from a much longer base delay than a connection error.
CONNECTION_BASE_DELAY_SECS = 2.0
RATE_LIMIT_BASE_DELAY_SECS = 30.0
MAX_DELAY_SECS = 300.0
DEFAULT_ATTEMPTS = 5


def write_atomically(path, data):
    """Write `data` (bytes) to `path` so an interrupted run never leaves a half-written file.

    Both download caches trust a file just for existing, so a truncated one (a run killed
    mid-write) would break every later run that reads it. Writing to a temporary sibling and then
    renaming it over `path` (`os.replace`, atomic on one filesystem) means `path` is either the
    old file, absent, or complete.

    Args:
        path (str | Path): destination file.
        data (bytes): the full contents.
    """
    path = Path(path)
    temp_path = path.with_name(path.name + ".partial")
    temp_path.write_bytes(data)
    os.replace(temp_path, path)


def use_os_trust_store():
    """Verify TLS certificates against the operating system's store instead of `certifi`'s.

    Uses the `truststore` package when it's installed (an ingestion/dev dependency, see
    requirements-dev.txt) and is a silent no-op otherwise — the deployed app makes no network
    calls, so it doesn't ship `truststore` at all. Safe to call more than once: it just re-points
    `ssl.SSLContext` (and urllib3/requests' own cached references) at the same class.

    Returns:
        bool: True if the OS trust store is now in use, False if `truststore` isn't available.
    """
    try:
        import truststore
    except ImportError:
        return False
    truststore.inject_into_ssl()
    return True


def _status_and_retry_after(exc):
    """Extract `(status_code, retry_after_secs)` from an HTTP error raised by `requests` or
    `urllib`, or `(None, None)` for anything that isn't an HTTP status error."""
    # urllib's HTTPError must be checked first: it proxies unknown attribute lookups to its
    # underlying response file, so a `getattr(exc, "response", None)` on one without a body
    # raises KeyError instead of returning the default (caught by tests/test_net.py).
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code, _parse_retry_after(exc.headers.get("Retry-After") if exc.headers else None)
    response = getattr(exc, "response", None)  # requests.HTTPError
    if response is not None and getattr(response, "status_code", None) is not None:
        return response.status_code, _parse_retry_after(response.headers.get("Retry-After"))
    return None, None


def _parse_retry_after(value):
    """`Retry-After` in seconds, or None. The HTTP-date form is rare for these hosts and is
    ignored (falls back to exponential backoff) rather than parsed."""
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def classify_failure(exc):
    """Decide whether a failed download is worth retrying, and from what base delay.

    Args:
        exc (BaseException): the exception a download raised.

    Returns:
        tuple: `(retryable, base_delay_secs, retry_after_secs)`. `retry_after_secs` is the
        server's own `Retry-After` hint when it sent one, else None.
    """
    status, retry_after = _status_and_retry_after(exc)
    if status is not None:
        if status not in RETRYABLE_STATUS_CODES:
            return False, None, None
        base = RATE_LIMIT_BASE_DELAY_SECS if status == 429 else CONNECTION_BASE_DELAY_SECS
        return True, base, retry_after

    try:
        import requests
    except ImportError:  # pragma: no cover - requests ships with statsbombpy and streamlit
        requests = None
    if requests is not None:
        # SSLError subclasses ConnectionError in requests, but a certificate problem is
        # configuration, not a network hiccup — check it first and never retry it.
        if isinstance(exc, requests.exceptions.SSLError):
            return False, None, None
        if isinstance(
            exc,
            (
                requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
                requests.exceptions.Timeout,
            ),
        ):
            return True, CONNECTION_BASE_DELAY_SECS, None

    if isinstance(exc, urllib.error.URLError) and "CERTIFICATE_VERIFY_FAILED" in str(exc.reason):
        return False, None, None
    if isinstance(exc, (http.client.IncompleteRead, ConnectionError, TimeoutError, urllib.error.URLError)):
        return True, CONNECTION_BASE_DELAY_SECS, None
    return False, None, None


def with_retries(fetch, describe="download", attempts=DEFAULT_ATTEMPTS, sleep=time.sleep):
    """Call `fetch()`, retrying transient network failures with exponential backoff.

    Delay before retry n is `base * 2**(n-1)` plus up to 1s of jitter, capped at
    `MAX_DELAY_SECS` — or the server's `Retry-After` when it sent one. Non-transient failures
    (404, 403, certificate errors, bugs in `fetch` itself) are re-raised immediately.

    Args:
        fetch (callable): zero-argument function performing one download attempt.
        describe (str): short label for progress messages (e.g. `"events 3869685"`).
        attempts (int): total attempts including the first, >= 1.
        sleep (callable): injected for tests; defaults to `time.sleep`.

    Returns:
        Whatever `fetch()` returns on its first successful attempt.

    Raises:
        The last exception, once attempts are exhausted or on a non-transient failure.
    """
    for attempt in range(1, attempts + 1):
        try:
            return fetch()
        except Exception as exc:  # noqa: BLE001 - classified below, re-raised if not transient
            retryable, base_delay, retry_after = classify_failure(exc)
            if not retryable or attempt == attempts:
                raise
            if retry_after is not None:
                delay = min(retry_after, MAX_DELAY_SECS)
            else:
                delay = min(base_delay * 2 ** (attempt - 1) + random.uniform(0, 1), MAX_DELAY_SECS)
            print(
                f"      [retry {attempt}/{attempts - 1}] {describe}: "
                f"{type(exc).__name__} — waiting {delay:.0f}s"
            )
            sleep(delay)
