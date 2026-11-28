"""Tests for the Stellarium fetch step. The network is faked, so these run offline."""

import subprocess

import pytest
import requests

from anser import stellarium_fetch

FAKE_JSON = b'{"id": "modern"}'


class FakeResponse:
    def __init__(self, content=FAKE_JSON, status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


@pytest.fixture
def calls(monkeypatch):
    """Swap requests.get for a fake that records each URL it's asked for."""
    seen = []

    def fake_get(url, timeout):
        seen.append(url)
        return FakeResponse()

    monkeypatch.setattr(stellarium_fetch.requests, "get", fake_get)
    return seen


def test_downloads_when_missing(tmp_path, calls):
    target = tmp_path / "modern" / "index.json"
    result = stellarium_fetch.fetch_index(target)
    assert result == target
    assert target.read_bytes() == FAKE_JSON
    assert len(calls) == 1


def test_uses_cache_when_present(tmp_path, calls):
    target = tmp_path / "index.json"
    target.write_bytes(b"already here")
    stellarium_fetch.fetch_index(target)
    assert calls == []
    assert target.read_bytes() == b"already here"


def test_force_redownloads(tmp_path, calls):
    target = tmp_path / "index.json"
    target.write_bytes(b"stale")
    stellarium_fetch.fetch_index(target, force=True)
    assert len(calls) == 1
    assert target.read_bytes() == FAKE_JSON


def test_http_error_raises_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        stellarium_fetch.requests, "get", lambda url, timeout: FakeResponse(status_code=404)
    )
    target = tmp_path / "index.json"
    with pytest.raises(requests.HTTPError):
        stellarium_fetch.fetch_index(target)
    assert not target.exists()
    assert not target.with_suffix(".part").exists()


def test_crash_before_rename_leaves_no_real_file(tmp_path, calls, monkeypatch):
    def crash(self, other):
        raise OSError("simulated crash mid-save")

    monkeypatch.setattr(stellarium_fetch.Path, "replace", crash)
    target = tmp_path / "index.json"
    with pytest.raises(OSError):
        stellarium_fetch.fetch_index(target)
    assert not target.exists()


def test_url_points_at_pinned_modern_index(tmp_path, calls):
    stellarium_fetch.fetch_index(tmp_path / "index.json")
    assert calls == [
        "https://raw.githubusercontent.com/Stellarium/stellarium/"
        "v26.3/skycultures/modern/index.json"
    ]


def test_default_path_is_gitignored():
    rel = stellarium_fetch.path.relative_to(stellarium_fetch.root)
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", str(rel)],
        cwd=stellarium_fetch.root,
    )
    assert result.returncode == 0, f"{rel} would be committed"
