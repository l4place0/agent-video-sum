from core.platforms.bilibili import BilibiliPlatform
from core.platforms.youtube import YouTubePlatform
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_bilibili_match():
    p = BilibiliPlatform()
    assert p.match("https://www.bilibili.com/video/BV1xx411c7XW")
    assert p.match("https://bilibili.com/video/BV1abc123")
    assert not p.match("https://youtube.com/watch?v=abc")


def test_bilibili_parse_url():
    p = BilibiliPlatform()
    assert p.parse_url("https://www.bilibili.com/video/BV1xx411c7XW") == "BV1xx411c7XW"


def test_bilibili_parse_invalid():
    p = BilibiliPlatform()
    try:
        p.parse_url("https://youtube.com/watch?v=abc")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_bilibili_part_scope_and_download_metadata(tmp_path):
    platform = BilibiliPlatform()
    view = {
        "cid": 11, "duration": 300, "title": "Course",
        "pages": [
            {"cid": 11, "duration": 100, "part": "Intro"},
            {"cid": 22, "duration": 200, "part": "Lesson"},
        ],
    }
    selected = []

    def response(_client, endpoint, params):
        if endpoint.endswith("/view"):
            return view
        if endpoint.endswith("/playurl"):
            selected.append(params["cid"])
            return {"dash": {"audio": [{"baseUrl": "https://example.invalid/audio"}]}}
        return []

    with patch("core.platforms.bilibili.httpx.Client", return_value=MagicMock()), \
         patch.object(platform, "_api_json", side_effect=response), \
         patch.object(platform, "_download_stream"), \
         patch.object(platform, "extract_audio"):
        with pytest.raises(ValueError, match="select one"):
            platform.resolve_capture("https://www.bilibili.com/video/BV123/")
        with pytest.raises(ValueError, match="outside"):
            platform.resolve_capture("https://www.bilibili.com/video/BV123/?p=3")
        with pytest.raises(ValueError, match="positive integer"):
            platform.resolve_capture("https://www.bilibili.com/video/BV123/?p=abc")
        url, identity = platform.resolve_capture("https://www.bilibili.com/video/BV123/?p=2")
        assert identity == "BV123-p2"
        _audio, metadata, _video = platform._download_public_api(url, Path(tmp_path), False)

    assert selected == [22]
    assert metadata["duration"] == 200
    assert metadata["title"] == "Course - P2 Lesson"


def test_youtube_match():
    p = YouTubePlatform()
    assert p.match("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert p.match("https://youtube.com/watch?v=dQw4w9WgXcQ")
    assert p.match("https://youtu.be/dQw4w9WgXcQ")
    assert p.match("https://www.youtube.com/embed/dQw4w9WgXcQ")
    assert not p.match("https://bilibili.com/video/BV1xx411c7XW")
    assert not p.match("https://example.com")


def test_youtube_parse_url():
    p = YouTubePlatform()
    assert p.parse_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert p.parse_url("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert p.parse_url("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_youtube_parse_invalid():
    p = YouTubePlatform()
    try:
        p.parse_url("https://example.com")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
