"""Scan workspace files for configured runtime secret values."""

import os
from pathlib import Path

from src.services.publication_validator import contains_secret_value


EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
}


def scan_tree_for_values(root: Path, values: list[str]) -> list[Path]:
    """Return relative paths containing a non-empty value, without exposing it."""
    findings: list[Path] = []
    active_values = [value for value in values if value]
    if not active_values:
        return findings

    for path in root.rglob("*"):
        relative_path = path.relative_to(root)
        if (
            not path.is_file()
            or any(part in EXCLUDED_PARTS for part in relative_path.parts)
        ):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if contains_secret_value(data, active_values):
            findings.append(relative_path)

    return sorted(findings)


def main() -> int:
    values = [
        os.getenv("DEEPSEEK_API_KEY", ""),
        os.getenv("APIFY_TOKEN", ""),
    ]
    findings = scan_tree_for_values(Path.cwd(), values)
    if findings:
        print("Runtime secret value found in tracked workspace files:")
        for path in findings:
            print(f"- {path}")
        return 1
    print("Runtime secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
