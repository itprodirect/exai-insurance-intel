#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
MEMORY_FILE = ROOT / "MEMORY.md"
SESSION_DIR = ROOT / "memory"
HEARTBEAT_MD = ROOT / "HEARTBEAT.md"
HEARTBEAT_JSON = ROOT / "heartbeat.json"

SECTION_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)


def split_sections(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()
    return sections


def first_paragraph(block: str) -> str:
    parts = [paragraph.strip() for paragraph in block.split("\n\n") if paragraph.strip()]
    return parts[0] if parts else ""


def bullet_list(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif re.match(r"^\d+\.\s+", line):
            items.append(re.sub(r"^\d+\.\s+", "", line).strip())
    return items


def latest_session_file() -> Path | None:
    if not SESSION_DIR.exists():
        return None
    files = sorted(path for path in SESSION_DIR.glob("*.md") if path.is_file())
    return files[-1] if files else None


def session_payload(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None

    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)
    return {
        "date": path.stem,
        "objective": first_paragraph(sections.get("Objective", "")),
        "changes_made": bullet_list(sections.get("Changes made", "")),
        "validation_run": bullet_list(sections.get("Validation run", "")),
        "open_issues": bullet_list(sections.get("Open issues", "")),
        "decisions_proposed": bullet_list(sections.get("Decisions proposed", "")),
        "next_thin_slice": bullet_list(sections.get("Next thin slice", "")),
    }


def build_payload() -> dict[str, Any]:
    if not MEMORY_FILE.exists():
        raise SystemExit("MEMORY.md not found")

    memory_text = MEMORY_FILE.read_text(encoding="utf-8")
    sections = split_sections(memory_text)
    session = session_payload(latest_session_file())

    return {
        "repo": first_paragraph(sections.get("Repo", "")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": first_paragraph(sections.get("Purpose", "")),
        "strategic_role": first_paragraph(sections.get("Strategic role", "")),
        "current_milestone": first_paragraph(sections.get("Current milestone", "")),
        "durable_decisions": bullet_list(sections.get("Durable decisions", "")),
        "operating_posture": first_paragraph(
            sections.get("Current architecture / operating posture", "")
        ),
        "top_blockers": bullet_list(sections.get("Top blockers", "")),
        "docs_freshness": first_paragraph(sections.get("Docs freshness", "")),
        "setup_friction": first_paragraph(sections.get("Setup friction", "")),
        "validation_path": bullet_list(sections.get("Validation path", "")),
        "key_files_commands": bullet_list(sections.get("Key files / commands", "")),
        "safe_automation_now": bullet_list(sections.get("Safe automation now", "")),
        "wait_until_later": bullet_list(sections.get("Wait until later", "")),
        "update_policy": first_paragraph(sections.get("Update policy", "")),
        "last_session": session,
        "next_thin_slice": session["next_thin_slice"] if session else [],
    }


def write_json(payload: dict[str, Any]) -> None:
    HEARTBEAT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(payload: dict[str, Any]) -> None:
    session = payload["last_session"]
    lines: list[str] = []
    lines.append(f"# HEARTBEAT - {payload['repo']}")
    lines.append("")
    lines.append("_Generated file. Regenerate with `python scripts/generate_heartbeat.py`._")
    lines.append("")
    lines.append(f"_Generated: {payload['generated_at']}_")
    lines.append("")
    lines.append("## Current status")
    lines.append(f"- Purpose: {payload['purpose']}")
    lines.append(f"- Strategic role: {payload['strategic_role']}")
    lines.append(f"- Current milestone: {payload['current_milestone']}")
    lines.append("")
    lines.append("## Operating posture")
    lines.append(f"- {payload['operating_posture']}")
    lines.append("")
    lines.append("## Durable decisions")
    for item in payload["durable_decisions"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Top blockers")
    for item in payload["top_blockers"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Docs + setup")
    lines.append(f"- Docs freshness: {payload['docs_freshness']}")
    lines.append(f"- Setup friction: {payload['setup_friction']}")
    lines.append("")
    lines.append("## Validation path")
    for item in payload["validation_path"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Key files / commands")
    for item in payload["key_files_commands"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Safe automation now")
    for item in payload["safe_automation_now"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Wait until later")
    for item in payload["wait_until_later"]:
        lines.append(f"- {item}")
    lines.append("")
    if session:
        lines.append("## Last session")
        lines.append(f"- Date: {session['date']}")
        lines.append(f"- Objective: {session['objective']}")
        if session["changes_made"]:
            lines.append("- Changes made:")
            for item in session["changes_made"]:
                lines.append(f"  - {item}")
        if session["validation_run"]:
            lines.append("- Validation:")
            for item in session["validation_run"]:
                lines.append(f"  - {item}")
        if session["open_issues"]:
            lines.append("- Open issues:")
            for item in session["open_issues"]:
                lines.append(f"  - {item}")
        if session["decisions_proposed"]:
            lines.append("- Decisions proposed:")
            for item in session["decisions_proposed"]:
                lines.append(f"  - {item}")
        lines.append("")
    lines.append("## Next thin slice")
    for item in payload["next_thin_slice"]:
        lines.append(f"- {item}")
    lines.append("")

    HEARTBEAT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    payload = build_payload()
    write_json(payload)
    write_markdown(payload)


if __name__ == "__main__":
    main()
