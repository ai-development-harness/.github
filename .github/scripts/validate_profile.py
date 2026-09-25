#!/usr/bin/env python3
"""Проверяет целостность публичного профиля GitHub-организации."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "profile" / "README.md"

REQUIRED_SNIPPETS = (
    "PROJECT INIT",
    "STEP RUN STEP-001",
    "HARNESS STATUS",
    "HARNESS RESUME",
    "HARNESS UPDATE CHECK",
    "HARNESS UPDATE APPLY",
    "GIT CHECK > COMMIT > PUSH > PR",
    ".harness/command-transitions.json",
    ".harness/manifest.yaml",
    ".harness/local/execution/execution-status.lock",
    ".harness/local/update-journal/",
)

FORBIDDEN_SNIPPETS = (
    ".project/",
    "docs/harness/",
    "`INIT PROJECT`",
    "`STATUS PROJECT`",
    "`NEXT STEP`",
    "`RUN STEP-",
    "`PLAN STEP-",
    "`IMPLEMENT STEP-",
    "`REVIEW STEP-",
    "`QUICK FIX:",
)

MARKDOWN_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
HTML_LINK_RE = re.compile(r"""(?:src|href)=["']([^"']+)["']""", re.IGNORECASE)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def resolve_local_target(source: Path, raw_target: str) -> Path | None:
    target = raw_target.strip()
    if not target or target.startswith(("#", "http://", "https://", "mailto:", "tel:")):
        return None

    if " " in target and not target.startswith("<"):
        target = target.split(" ", 1)[0]

    target = target.strip("<>")
    target = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not target:
        return None

    return (source.parent / target).resolve()


def main() -> int:
    errors: list[str] = []

    if not PROFILE.is_file():
        fail("profile/README.md отсутствует")
        return 1

    text = PROFILE.read_text(encoding="utf-8")

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            errors.append(f"profile/README.md: отсутствует обязательный фрагмент: {snippet}")

    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            errors.append(f"profile/README.md: найден устаревший фрагмент: {snippet}")

    markdown_files = sorted(ROOT.rglob("*.md"))
    if not markdown_files:
        errors.append("В репозитории не найдено Markdown-файлов")

    for md_file in markdown_files:
        md_text = md_file.read_text(encoding="utf-8")
        targets = MARKDOWN_LINK_RE.findall(md_text)
        targets.extend(HTML_LINK_RE.findall(md_text))

        for raw_target in targets:
            resolved = resolve_local_target(md_file, raw_target)
            if resolved is None:
                continue
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(
                    f"{md_file.relative_to(ROOT)}: локальная ссылка выходит за пределы репозитория: {raw_target}"
                )
                continue
            if not resolved.exists():
                errors.append(
                    f"{md_file.relative_to(ROOT)}: битая локальная ссылка: {raw_target}"
                )

    if errors:
        for error in errors:
            fail(error)
        return 1

    print(
        f"Profile integrity: PASS "
        f"({len(markdown_files)} Markdown files, required command surface present)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
