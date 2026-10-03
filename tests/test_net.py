"""Unit tests for src/net.py — retry classification and the OS trust-store hook.

No network: every "download" here is a fake callable that raises the same exception types
`requests`/`urllib` raise for real, and `sleep` is injected so no test actually waits.
"""

import email.message
import sys
import types
import urllib.error

import pytest
import requests

from src import net


def _http_error(status, retry_after=None):
    response = requests.Response()
    response.status_code = status
    if retry_after is not None:
        response.headers["Retry-After"] = str(retry_after)
    return requests.HTTPError(f"{status} error", response=response)


def _flaky(failures, value="ok"):
    """A fetch() that raises each exception in `failures` in turn, then returns `value`."""
    remaining = list(failures)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        if remaining:
            raise remaining.pop(0)
        return value

    return fetch, calls


def test_with_retries_recovers_from_transient_connection_errors():
    sleeps = []
    fetch, calls = _flaky([requests.ConnectionError("reset"), requests.ConnectionError("reset")])
    assert net.with_retries(fetch, sleep=sleeps.append) == "ok"
    assert calls["n"] == 3
    assert len(sleeps) == 2
    assert sleeps[1] > sleeps[0]  # exponential backoff, not a fixed delay


def test_with_retries_honours_retry_after_on_rate_limit():
    sleeps = []
    fetch, _ = _flaky([_http_error(429, retry_after=7)])
    assert net.with_retries(fetch, sleep=sleeps.append) == "ok"
    assert sleeps == [7.0]


def test_rate_limit_without_retry_after_backs_off_longer_than_a_dropped_connection():
    rate_limited, connection = [], []
    net.with_retries(_flaky([_http_error(429)])[0], sleep=rate_limited.append)
    net.with_retries(_flaky([requests.ConnectionError("reset")])[0], sleep=connection.append)
    assert rate_limited[0] >= net.RATE_LIMIT_BASE_DELAY_SECS
    assert connection[0] < net.RATE_LIMIT_BASE_DELAY_SECS


def test_with_retries_fails_fast_on_404():
    sleeps = []
    fetch, calls = _flaky([_http_error(404)])
    with pytest.raises(requests.HTTPError):
        net.with_retries(fetch, sleep=sleeps.append)
    assert calls["n"] == 1
    assert sleeps == []


def test_with_retries_never_retries_certificate_errors():
    # requests.SSLError subclasses ConnectionError — the classifier must check it first.
    fetch, calls = _flaky([requests.exceptions.SSLError("CERTIFICATE_VERIFY_FAILED")])
    with pytest.raises(requests.exceptions.SSLError):
        net.with_retries(fetch, sleep=lambda _: None)
    assert calls["n"] == 1


def test_with_retries_reraises_after_exhausting_attempts():
    fetch, calls = _flaky([requests.ConnectionError("down")] * 10)
    with pytest.raises(requests.ConnectionError):
        net.with_retries(fetch, attempts=3, sleep=lambda _: None)
    assert calls["n"] == 3


def test_with_retries_does_not_swallow_bugs_in_fetch():
    fetch, calls = _flaky([KeyError("not a network problem")])
    with pytest.raises(KeyError):
        net.with_retries(fetch, sleep=lambda _: None)
    assert calls["n"] == 1


def test_classify_failure_retries_urllib_5xx_and_honours_its_retry_after():
    headers = email.message.Message()
    headers["Retry-After"] = "3"
    exc = urllib.error.HTTPError("https://example.test", 503, "unavailable", headers, None)
    assert net.classify_failure(exc) == (True, net.CONNECTION_BASE_DELAY_SECS, 3.0)


def test_classify_failure_does_not_retry_urllib_certificate_errors():
    exc = urllib.error.URLError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    assert net.classify_failure(exc)[0] is False


def test_use_os_trust_store_injects_when_truststore_is_available(monkeypatch):
    calls = []
    fake = types.ModuleType("truststore")
    fake.inject_into_ssl = lambda: calls.append("inject")
    monkeypatch.setitem(sys.modules, "truststore", fake)
    assert net.use_os_trust_store() is True
    assert calls == ["inject"]


def test_use_os_trust_store_is_a_noop_without_truststore(monkeypatch):
    monkeypatch.setitem(sys.modules, "truststore", None)  # makes `import truststore` fail
    assert net.use_os_trust_store() is False


def test_write_atomically_replaces_the_file_and_leaves_no_partial_behind(tmp_path):
    from src.net import write_atomically

    target = tmp_path / "events_1.pkl"
    target.write_bytes(b"old")
    write_atomically(target, b"new contents")
    assert target.read_bytes() == b"new contents"
    assert [p.name for p in tmp_path.iterdir()] == ["events_1.pkl"]
