"""Resource replacement must preserve other resources and existing notes."""

import json

import pytest

from core.library import FilesystemLibrary


def save(library, video_id, title, force=False):
    return library.save(
        platform="youtube", video_id=video_id, source_url=f"https://example.com/{video_id}",
        metadata={"title": title}, summary=video_id, transcript=f"transcript {video_id}",
        transcript_segments=[], frames=[], providers={}, force=force,
    )


@pytest.mark.parametrize("titles", [("same", "same"), ("a?b", "a*b"), ("x" * 121, "x" * 122)])
@pytest.mark.parametrize("force", [False, True])
def test_colliding_titles_keep_both_notes(tmp_path, titles, force):
    library = FilesystemLibrary(tmp_path)
    first = save(library, "A", titles[0])
    original = first.note_path.read_bytes()
    second = save(library, "B", titles[1], force=force)
    assert first.note_path != second.note_path
    assert first.note_path.read_bytes() == original
    assert library.get_resource(first.resource_id)["note_path"] == str(first.note_path)
    assert "transcript B" in second.note_path.read_text(encoding="utf-8")
    composed = library.compose(first.resource_id, summary="A composed", understanding="```mermaid\ngraph TD\nA-->B\n```")
    assert "transcript A" in composed.note_path.read_text(encoding="utf-8")


def test_force_reuses_legacy_note_after_title_change(tmp_path):
    library = FilesystemLibrary(tmp_path)
    first = save(library, "A", "old title")
    legacy = tmp_path / "assets" / first.resource_id / "resource.json"
    legacy.parent.mkdir()
    first.manifest_path.replace(legacy)
    with pytest.raises(FileExistsError):
        save(library, "A", "new title")
    updated = save(library, "A", "new title", force=True)
    assert updated.note_path == first.note_path
    assert json.loads(updated.manifest_path.read_text(encoding="utf-8"))["title"] == "new title"


def test_force_preserves_unowned_notes_and_rejects_occupied_fallback(tmp_path):
    library = FilesystemLibrary(tmp_path)
    (tmp_path / "same.md").write_text("personal note", encoding="utf-8")
    fallback = tmp_path / "same--youtube-A.md"
    fallback.write_text("another personal note", encoding="utf-8")
    with pytest.raises(FileExistsError):
        save(library, "A", "same", force=True)
    assert (tmp_path / "same.md").read_text(encoding="utf-8") == "personal note"
    assert fallback.read_text(encoding="utf-8") == "another personal note"


def test_force_rejects_preexisting_shared_manifest_note(tmp_path):
    library = FilesystemLibrary(tmp_path)
    first = save(library, "A", "same")
    second = save(library, "B", "other")
    manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["note"] = first.note_path.name
    second.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    original = first.note_path.read_bytes()
    with pytest.raises(FileExistsError):
        save(library, "A", "same", force=True)
    assert first.note_path.read_bytes() == original
