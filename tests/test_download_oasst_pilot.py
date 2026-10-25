from hashlib import sha256
from io import BytesIO

import pytest

from learning import download_oasst_pilot as source


def test_download_checks_hash_and_reuses_existing_verified_file(tmp_path, monkeypatch):
    body = b"public test source"
    monkeypatch.setattr(source, "FILES", {"README.md": (sha256(body).hexdigest(), 100)})
    calls = []
    def request(url, timeout):
        calls.append(url)
        return BytesIO(body)
    monkeypatch.setattr(source.urllib.request, "urlopen", request)
    source.download(tmp_path)
    source.download(tmp_path)
    assert (tmp_path / "README.md").read_bytes() == body
    assert len(calls) == 1


@pytest.mark.parametrize("body,limit", [(b"bad hash", 100), (b"too long", 3)])
def test_failed_download_never_becomes_an_accepted_source(tmp_path, monkeypatch, body, limit):
    monkeypatch.setattr(source, "FILES", {"README.md": (sha256(b"expected").hexdigest(), limit)})
    monkeypatch.setattr(source.urllib.request, "urlopen", lambda *a, **k: BytesIO(body))
    with pytest.raises(ValueError):
        source.download(tmp_path)
    assert not (tmp_path / "README.md").exists()
    assert not list(tmp_path.glob("*.part"))
