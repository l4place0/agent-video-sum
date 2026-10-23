#!/usr/bin/env python3
"""Create a local, sanitized Agent Video Sum diagnostic report."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bootstrap


SENSITIVE_KEY = re.compile(
    r"(?:authorization|cookie|password|secret|token|api[_-]?key)",
    re.IGNORECASE,
)
URL = re.compile(r"https?://[^\s\]\[<>\"']+")
SKILL_STAGES = {"bootstrap", "install", "onboard", "skill", "prompt"}
CLI_REPOSITORY = "l4place0/agent-video-sum"
SKILL_REPOSITORY = CLI_REPOSITORY


def scrub_string(value: str, project_dir: Path) -> str:
    cleaned = value
    for source, replacement in (
        (str(Path.home()), "<home>"),
        (str(project_dir), "<project>"),
    ):
        if source:
            cleaned = cleaned.replace(source, replacement)

    def scrub_url(match: re.Match[str]) -> str:
        raw = match.group(0)
        try:
            parsed = urllib.parse.urlsplit(raw)
        except ValueError:
            return "<redacted-url>"
        query = "<redacted>" if parsed.query else ""
        return urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, query, "")
        )

    return URL.sub(scrub_url, cleaned)


def sanitize(value: Any, project_dir: Path) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "<redacted>"
                if SENSITIVE_KEY.search(str(key))
                else sanitize(item, project_dir)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item, project_dir) for item in value]
    if isinstance(value, str):
        return scrub_string(value, project_dir)
    return value


def run_json(command: list[str], cwd: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    payload: Any = None
    for line in reversed(result.stdout.splitlines()):
        try:
            payload = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    return {
        "available": result.returncode == 0,
        "returncode": result.returncode,
        "result": payload if payload is not None else result.stdout[-4000:],
        "stderr": result.stderr[-2000:],
    }


def route_repository(component: str, stage: str) -> str:
    """Return the repository for a report.

    The CLI and the Skill now live in one repository, so every component and
    stage routes to the same destination. The signature is kept so callers and
    the ``--component``/``--stage`` flags stay stable.
    """
    return SKILL_REPOSITORY if stage in SKILL_STAGES else CLI_REPOSITORY


def report_markdown(payload: dict[str, Any]) -> str:
    diagnostics = json.dumps(
        payload["diagnostics"], ensure_ascii=False, indent=2
    )
    context = payload["context"]
    return f"""# Agent Video Sum issue report

- Generated: `{payload['generated_at']}`
- Routed repository: `{payload['repository']}`
- Suggested Issue URL: {payload['issue_url']}
- OS: `{payload['os']}`
- Architecture: `{payload['architecture']}`

## Observed context

- Stage: `{context['stage'] or 'Unknown'}`
- Error code: `{context['error_code'] or 'Unknown'}`
- Summary: {context['summary'] or 'Not provided'}
- User impact: {context['impact'] or 'Not provided'}

## Sanitized diagnostics

```json
{diagnostics}
```

> Review this local report before sharing. It omits environment variables,
> configuration files, credentials, transcripts, media, frames, comments, and
> danmaku. No GitHub Issue was searched, created, or uploaded automatically.
"""


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(f"agent-video-sum-issue-{stamp}.md"),
    )
    parser.add_argument(
        "--component", choices=("auto", "cli", "skill"), default="auto"
    )
    parser.add_argument("--stage", default="")
    parser.add_argument("--error-code", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument("--impact", default="")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=bootstrap.default_install_dir(),
    )
    args = parser.parse_args()

    project_dir = args.project_dir.expanduser().resolve()
    install_dir = args.install_dir.expanduser().resolve()
    status = bootstrap.status_payload(install_dir)
    command = str(status.get("command") or "")
    diagnostics: dict[str, Any] = {"bootstrap_status": status}
    if command:
        diagnostics["version"] = run_json([command, "--version"], project_dir)
        diagnostics["doctor"] = run_json([command, "doctor"], project_dir)
        diagnostics["asr_profiles"] = run_json(
            [command, "asr", "profiles"], project_dir
        )

    repository = route_repository(args.component, args.stage)
    payload = sanitize(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repository": repository,
            "issue_url": (
                f"https://github.com/{repository}/issues/new/choose"
            ),
            "os": platform.system(),
            "architecture": platform.machine(),
            "context": {
                "stage": args.stage,
                "error_code": args.error_code,
                "summary": args.summary,
                "impact": args.impact,
            },
            "diagnostics": diagnostics,
        },
        project_dir,
    )
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report_markdown(payload), encoding="utf-8")
    if os.name != "nt":
        output.chmod(0o600)
    print(
        json.dumps(
            {
                "schema_version": 1,
                "event": "issue_report_created",
                "output": str(output),
                "repository": repository,
                "issue_url": payload["issue_url"],
                "uploaded": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
