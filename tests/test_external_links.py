"""Tests for tools/check_external_links.py (no test reaches the network)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "check_external_links.py"

_spec = importlib.util.spec_from_file_location("check_external_links", TOOL)
links = importlib.util.module_from_spec(_spec)
# dataclasses resolve their module through sys.modules while the file loads.
sys.modules[_spec.name] = links
_spec.loader.exec_module(links)

BT = chr(96)
FENCE = BT * 3


def _fetch_ok(url, *, timeout=10.0):
    return links.FetchResult(status=200, final_url=url)


def _always(result):
    return lambda url, *, timeout=10.0: result


def test_fenced_code_urls_are_ignored():
    text = (
        "Prose with https://real.example.org/doc\n"
        "\n"
        + FENCE + "bash\n"
        "http_proxy=http://127.0.0.1:9 python3 -m pytest\n"
        "see https://example.com too\n"
        + FENCE + "\n"
    )
    assert links.external_urls(text) == ["https://real.example.org/doc"]


def test_inline_code_urls_are_ignored():
    text = (
        f"Run with {BT}https://inside.example.org/x{BT} "
        "or see https://outside.example.org/y\n"
    )
    assert links.external_urls(text) == ["https://outside.example.org/y"]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9",
        "http://localhost:8000/docs",
        "https://example.com",
        "https://www.example.org/page",
        "https://example.net",
    ],
)
def test_loopback_and_reserved_hosts_are_never_fetched(url):
    assert links.is_checkable(url) is False


def test_ordinary_hosts_are_checkable():
    assert links.is_checkable("https://docs.python.org/3/") is True


def test_a_markdown_link_with_parentheses_keeps_its_path():
    # README has a shields.io badge whose path contains (2018); the link's
    # own closing bracket must go, the path's parentheses must stay.
    text = (
        "[method](https://img.shields.io/badge/method-"
        "L%C3%B3pez%20de%20Prado%20(2018)-purple)\n"
    )
    assert links.external_urls(text) == [
        "https://img.shields.io/badge/method-L%C3%B3pez%20de%20Prado%20(2018)-purple"
    ]


@pytest.mark.parametrize(
    "result, expected",
    [
        (links.FetchResult(status=200), links.OK),
        (links.FetchResult(status=204), links.OK),
        (links.FetchResult(status=301), links.REDIRECTED),
        (links.FetchResult(status=404), links.BROKEN),
        (links.FetchResult(status=410), links.BROKEN),
        (links.FetchResult(status=403), links.UNVERIFIED),
        (links.FetchResult(status=429), links.UNVERIFIED),
        (links.FetchResult(status=503), links.UNVERIFIED),
        (links.FetchResult(transport="dns", detail="no such host"), links.BROKEN),
        (links.FetchResult(transport="timeout", detail="timed out"), links.UNVERIFIED),
    ],
)
def test_classification(result, expected):
    outcome, detail = links.classify(result, "https://docs.python.org/3/")
    assert outcome == expected
    assert detail


def test_a_redirect_is_reported_with_its_destination():
    result = links.FetchResult(status=200, final_url="https://new.example.test/x")
    outcome, detail = links.classify(result, "https://old.example.test/x")
    assert outcome == links.REDIRECTED
    assert "https://new.example.test/x" in detail


def test_head_404_is_confirmed_with_get(monkeypatch):
    # www.workbuddy.ai answered 404 to HEAD and 200 to GET for the same path,
    # which would have been reported as a dead link.
    seen = []

    def fake_request(url, method, timeout):
        seen.append(method)
        if method == "HEAD":
            return links.FetchResult(status=404)
        return links.FetchResult(status=200, final_url=url)

    monkeypatch.setattr(links, "_request", fake_request)
    result = links.fetch_url("https://www.workbuddy.ai/docs/cli/installation")

    assert seen == ["HEAD", "GET"]
    assert result.status == 200


def test_a_server_error_is_retried_then_given_up_on():
    calls = []
    sleeps = []

    def fetch(url, *, timeout=10.0):
        calls.append(url)
        return links.FetchResult(status=503)

    outcome, _ = links.check_url(
        "https://flaky.example.test/x", fetch=fetch, retries=2, sleep=sleeps.append
    )

    assert outcome == links.UNVERIFIED
    assert len(calls) == 3
    assert sleeps == [2.0, 4.0]


def test_a_missing_host_is_not_retried():
    calls = []

    def fetch(url, *, timeout=10.0):
        calls.append(url)
        return links.FetchResult(transport="dns", detail="no such host")

    outcome, detail = links.check_url(
        "https://gone.example.test/x", fetch=fetch, retries=2, sleep=lambda _: None
    )

    assert outcome == links.BROKEN
    assert "does not resolve" in detail
    assert len(calls) == 1


def test_allowlisted_host_is_accepted_and_still_reported(tmp_path):
    (tmp_path / "README.md").write_text(
        "[paper](https://papers.example.test/a)\n", "utf-8"
    )

    results = links.check(
        tmp_path,
        fetch=_always(links.FetchResult(status=403)),
        retries=0,
        allowlist={"papers.example.test": "bot protection"},
        sleep=lambda _: None,
    )

    assert [r.outcome for r in results] == [links.ACCEPTED]
    assert "bot protection" in results[0].detail


def test_allowlist_does_not_excuse_a_404(tmp_path):
    (tmp_path / "README.md").write_text(
        "[gone](https://papers.example.test/a)\n", "utf-8"
    )

    results = links.check(
        tmp_path,
        fetch=_always(links.FetchResult(status=404)),
        retries=0,
        allowlist={"papers.example.test": "bot protection"},
        sleep=lambda _: None,
    )

    assert [r.outcome for r in results] == [links.BROKEN]


def test_allowlist_requires_a_reason(tmp_path):
    path = tmp_path / "allow.txt"
    path.write_text("papers.example.test\n", "utf-8")

    with pytest.raises(ValueError, match="needs a reason"):
        links.load_allowlist(path)


def test_sources_are_collected_and_each_url_is_fetched_once(tmp_path):
    (tmp_path / "README.md").write_text("see https://docs.example.test/a\n", "utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("again https://docs.example.test/a\n", "utf-8")
    calls = []

    def fetch(url, *, timeout=10.0):
        calls.append(url)
        return links.FetchResult(status=200, final_url=url)

    results = links.check(tmp_path, fetch=fetch, retries=0, sleep=lambda _: None)

    assert len(calls) == 1
    assert results[0].sources == ("README.md", "docs/guide.md")


def test_tool_cache_directories_are_not_scanned(tmp_path):
    (tmp_path / "README.md").write_text("clean\n", "utf-8")
    cache = tmp_path / ".pytest_cache"
    cache.mkdir()
    (cache / "README.md").write_text(
        "[x](https://stale.example.test/x)\n", "utf-8"
    )

    assert links.check(tmp_path, fetch=_fetch_ok, retries=0, sleep=lambda _: None) == []


def test_main_returns_one_when_a_link_is_broken(tmp_path, monkeypatch, capsys):
    (tmp_path / "README.md").write_text(
        "[gone](https://gone.example.test/x)\n", "utf-8"
    )
    monkeypatch.setattr(
        links,
        "check",
        lambda *args, **kwargs: [
            links.LinkResult(
                url="https://gone.example.test/x",
                outcome=links.BROKEN,
                detail="HTTP 404: gone",
                sources=("README.md",),
            )
        ],
    )

    code = links.main(["--root", str(tmp_path), "--allowlist", str(tmp_path / "none")])

    assert code == 1
    assert "[BROKEN]" in capsys.readouterr().out


def test_main_returns_zero_when_everything_resolves(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text("clean\n", "utf-8")
    monkeypatch.setattr(
        links,
        "check",
        lambda *args, **kwargs: [
            links.LinkResult(
                url="https://docs.python.org/3/", outcome=links.OK, detail="HTTP 200"
            )
        ],
    )

    code = links.main(["--root", str(tmp_path), "--allowlist", str(tmp_path / "none")])

    assert code == 0
