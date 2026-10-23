import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "issue_report.py"
SPEC = importlib.util.spec_from_file_location("skill_issue_report", SCRIPT)
assert SPEC and SPEC.loader
sys.path.insert(0, str(SCRIPT.parent))
issue_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(issue_report)


def test_sanitize_redacts_secrets_paths_and_url_queries(tmp_path):
    private = {
        "api_key": "secret-value",
        "path": str(Path.home() / "private" / "model.bin"),
        "url": "https://example.test/video?token=secret&expires=1",
        "nested": [{"authorization": "Bearer private"}],
    }

    sanitized = issue_report.sanitize(private, tmp_path.resolve())
    serialized = json.dumps(sanitized)

    assert "secret-value" not in serialized
    assert "Bearer private" not in serialized
    assert str(Path.home()) not in serialized
    assert "token=secret" not in serialized
    assert sanitized["api_key"] == "<redacted>"


def test_auto_routing_uses_single_repository():
    assert (
        issue_report.route_repository("auto", "onboard")
        == "l4place0/agent-video-sum"
    )
    assert (
        issue_report.route_repository("auto", "danmaku")
        == "l4place0/agent-video-sum"
    )
    assert (
        issue_report.route_repository("skill", "danmaku")
        == "l4place0/agent-video-sum"
    )


def test_issue_report_is_local_private_and_never_uploads(tmp_path):
    output = tmp_path / "report.md"
    fake_status = {
        "event": "bootstrap_status",
        "ready": True,
        "command": str(Path.home() / ".local" / "bin" / "video-sum"),
        "checks": {"cookie": "private-cookie"},
    }
    argv = [
        "issue_report.py",
        "--output",
        str(output),
        "--stage",
        "asr",
        "--summary",
        "failed at https://example.test/x?token=private",
        "--project-dir",
        str(tmp_path),
    ]
    with (
        patch.object(sys, "argv", argv),
        patch.object(
            issue_report.bootstrap, "status_payload", return_value=fake_status
        ),
        patch.object(
            issue_report,
            "run_json",
            return_value={"available": True, "result": {}},
        ),
    ):
        assert issue_report.main() == 0

    content = output.read_text(encoding="utf-8")
    assert "l4place0/agent-video-sum" in content
    assert "private-cookie" not in content
    assert "token=private" not in content
    assert str(Path.home()) not in content
    if os.name != "nt":
        assert output.stat().st_mode & 0o777 == 0o600


def test_posix_lifecycle_wrappers_return_structured_plans(tmp_path):
    root = SCRIPT.parents[1]
    install = subprocess.run(
        [
            "sh",
            str(root / "scripts" / "install.sh"),
            "--version",
            "0.4.0",
            "--install-dir",
            str(tmp_path / "bin"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    onboard = subprocess.run(
        [
            "sh",
            str(root / "scripts" / "onboard.sh"),
            "status",
            "--project-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(install.stdout)["event"] == "bootstrap_plan"
    assert json.loads(onboard.stdout)["event"] == "onboard_status"
