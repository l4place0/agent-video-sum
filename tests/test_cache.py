import json
import time
from unittest.mock import patch

from core.cache import CacheStore, derived_key, media_key


def test_stable_media_key_ignores_signed_url():
    first = media_key("bilibili", "BV123", quality="720p")
    second = media_key("bilibili", "BV123", quality="720p")
    assert first == second
    assert len(first) == 64


def test_cache_put_get_and_materialize(tmp_path):
    store = CacheStore(tmp_path / "cache")
    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")
    key = derived_key("parent", "audio", codec="pcm")

    stored = store.put_path(key, "audio", source)
    found = store.get(key)
    target = tmp_path / "work" / "audio.wav"

    assert stored.key == key
    assert found is not None
    assert store.materialize_file(found, target).read_bytes() == b"audio"
    assert store.status()["by_kind"] == {"audio": 1}


def test_cache_json_and_prune_expired(tmp_path):
    store = CacheStore(tmp_path / "cache")
    key = derived_key("parent", "transcript", model="small")
    store.put_json(key, "transcript", {"text": "hello"}, ttl_seconds=-1)

    assert store.read_json(key) is None
    result = store.prune()
    assert result["deleted"] == 0


def test_cache_list_serializes_entries(tmp_path):
    store = CacheStore(tmp_path / "cache")
    key = derived_key("parent", "metadata")
    store.put_json(key, "metadata", {"title": "test"})

    payload = json.dumps(store.list()[0].to_dict())
    assert key in payload
    assert store.list()[0].last_access <= time.time()


def test_expired_read_removes_object_before_forgetting_it(tmp_path):
    store = CacheStore(tmp_path / "cache")
    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")
    entry = store.put_path("expired-object", "audio", source, ttl_seconds=60)

    with patch("core.cache.time.time", return_value=entry.expiry + 1):
        assert store.get(entry.key) is None

    assert not entry.path.exists()
    assert store.status()["size"] == 0
    assert store.clear() == {"deleted": 0, "freed": 0}


def test_expired_removal_failure_remains_available_for_cleanup(tmp_path):
    store = CacheStore(tmp_path / "cache")
    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")
    entry = store.put_path("locked-object", "audio", source, ttl_seconds=60)

    with patch("core.cache.time.time", return_value=entry.expiry + 1), patch(
        "core.cache.shutil.rmtree", side_effect=PermissionError("locked")
    ):
        assert store.get(entry.key) is None

    assert store.status()["count"] == 1
    assert store.clear()["deleted"] == 1
    assert not entry.path.exists()
