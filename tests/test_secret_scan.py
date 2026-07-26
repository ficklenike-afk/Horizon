from pathlib import Path

from scripts.check_runtime_secrets import main, scan_tree_for_values


def test_secret_scan_reports_relative_path_without_echoing_value(tmp_path: Path) -> None:
    secret = "runtime-secret-value"
    (tmp_path / "safe.txt").write_text("public", encoding="utf-8")
    leaked = tmp_path / "nested" / "leaked.txt"
    leaked.parent.mkdir()
    leaked.write_text(secret, encoding="utf-8")

    findings = scan_tree_for_values(tmp_path, [secret])

    assert findings == [Path("nested/leaked.txt")]
    assert secret not in repr(findings)


def test_secret_scan_detects_escaped_secret_forms(tmp_path: Path) -> None:
    secret = "apify_api_secret"
    escaped_forms = {
        "markdown.txt": r"apify\_api\_secret",
        "html.txt": "apify&#95;api&#95;secret",
        "percent.txt": "apify%5Fapi%5Fsecret",
    }
    for filename, escaped_secret in escaped_forms.items():
        (tmp_path / filename).write_text(escaped_secret, encoding="utf-8")

    findings = scan_tree_for_values(tmp_path, [secret])

    assert findings == [
        Path("html.txt"),
        Path("markdown.txt"),
        Path("percent.txt"),
    ]


def test_secret_scan_ignores_empty_values_and_tool_directories(tmp_path: Path) -> None:
    secret = "runtime-secret-value"
    excluded_directories = [
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
    ]
    for directory in excluded_directories:
        leaked = tmp_path / directory / "leaked.txt"
        leaked.parent.mkdir()
        leaked.write_text(secret, encoding="utf-8")

    assert scan_tree_for_values(tmp_path, ["", secret]) == []


def test_secret_scan_checks_generic_cache_directory(tmp_path: Path) -> None:
    secret = "runtime-secret-value"
    leaked = tmp_path / "cache" / "leak.txt"
    leaked.parent.mkdir()
    leaked.write_text(secret, encoding="utf-8")

    assert scan_tree_for_values(tmp_path, [secret]) == [Path("cache/leak.txt")]


def test_secret_scan_cli_redacts_secret_embedded_in_finding_path(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    secret = "runtime-secret-value"
    leaked = (
        tmp_path
        / f"directory-{secret}"
        / f"leak-{secret}.txt"
    )
    leaked.parent.mkdir()
    leaked.write_text(secret, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APIFY_TOKEN", secret)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Runtime secret value found" in output
    assert "[REDACTED]" in output
    assert secret not in output
