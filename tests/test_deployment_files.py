import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "daily-summary.yml"
CONFIG_PATH = ROOT / "docs" / "_config.yml"
INDEX_PATH = ROOT / "docs" / "index.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _step(workflow: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^      - name: {re.escape(name)}\n"
        rf"(.*?)(?=^      - name: |\Z)",
        workflow,
    )
    assert match is not None, f"missing workflow step: {name}"
    return match.group(0)


def _assert_required_step_order(workflow: str) -> None:
    required_order = (
        "Determine Twitter schedule",
        "Prepare production config",
        "Run Horizon",
        "Check that runtime secrets were not written",
        "Deploy to GitHub Pages",
    )
    positions = [workflow.index(_step(workflow, name)) for name in required_order]
    assert positions == sorted(positions), (
        "required workflow step order: " + " < ".join(required_order)
    )


def test_workflow_has_required_step_order():
    _assert_required_step_order(_read(WORKFLOW_PATH))


def test_required_step_order_rejects_run_before_production_config():
    workflow = _read(WORKFLOW_PATH)
    prepare = _step(workflow, "Prepare production config")
    run_horizon = _step(workflow, "Run Horizon")
    malformed = workflow.replace(prepare, "__PREPARE_STEP__", 1)
    malformed = malformed.replace(run_horizon, prepare, 1)
    malformed = malformed.replace("__PREPARE_STEP__", run_horizon, 1)

    with pytest.raises(AssertionError, match="required workflow step order"):
        _assert_required_step_order(malformed)


def test_workflow_has_exact_daily_and_manual_triggers():
    workflow = _read(WORKFLOW_PATH)

    assert workflow.startswith("name: Daily Horizon Jersey Intelligence\n\n")
    trigger_block = """\
on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:
    inputs:
      force_twitter:
        description: Run Twitter once for deployment verification
        required: false
        default: false
        type: boolean
"""
    assert trigger_block in workflow
    assert len(re.findall(r"(?m)^\s+- cron:", workflow)) == 1


def test_workflow_uses_approved_action_versions():
    workflow = _read(WORKFLOW_PATH)

    assert re.findall(r"(?m)^\s+uses:\s*(\S+)", workflow) == [
        "actions/checkout@v6",
        "actions/setup-python@v5",
        "astral-sh/setup-uv@v6",
        "peaceiris/actions-gh-pages@v4",
    ]
    install_uv = _step(workflow, "Install uv")
    assert re.search(r'(?m)^          version: "0\.11\.26"$', install_uv)


def test_twitter_schedule_is_beijing_monday_wednesday_friday_or_forced():
    workflow = _read(WORKFLOW_PATH)
    step = _step(workflow, "Determine Twitter schedule")

    expected_step = """\
      - name: Determine Twitter schedule
        env:
          FORCE_TWITTER: ${{ inputs.force_twitter }}
        shell: bash
        run: |
          weekday="$(TZ=Asia/Shanghai date +%u)"
          if [[ "$FORCE_TWITTER" == "true" || "$weekday" == "1" || "$weekday" == "3" || "$weekday" == "5" ]]; then
            echo "TWITTER_ENABLED=true" >> "$GITHUB_ENV"
          else
            echo "TWITTER_ENABLED=false" >> "$GITHUB_ENV"
          fi
"""
    assert step.rstrip() == expected_step.rstrip()
    assert workflow.count("TWITTER_ENABLED=true") == 1
    assert workflow.count("TWITTER_ENABLED=false") == 1


def test_horizon_uses_production_config_secret_env_and_24_hour_window():
    workflow = _read(WORKFLOW_PATH)
    prepare = _step(workflow, "Prepare production config")
    run_horizon = _step(workflow, "Run Horizon")

    assert re.search(
        r"(?m)^        run: cp data/config\.github\.json data/config\.json$",
        prepare,
    )
    assert re.search(r"(?m)^          TZ: Asia/Shanghai$", run_horizon)
    assert re.search(
        r"(?m)^          DEEPSEEK_API_KEY: \$\{\{ secrets\.DEEPSEEK_API_KEY \}\}$",
        run_horizon,
    )
    assert re.search(
        r"(?m)^          APIFY_TOKEN: \$\{\{ secrets\.APIFY_TOKEN \}\}$",
        run_horizon,
    )
    assert re.search(r"(?m)^        run: uv run horizon --hours 24$", run_horizon)

    secret_assignments = re.findall(
        r"(?m)^\s+(DEEPSEEK_API_KEY|APIFY_TOKEN):\s*(.+)$",
        workflow,
    )
    assert secret_assignments == [
        ("DEEPSEEK_API_KEY", "${{ secrets.DEEPSEEK_API_KEY }}"),
        ("APIFY_TOKEN", "${{ secrets.APIFY_TOKEN }}"),
        ("DEEPSEEK_API_KEY", "${{ secrets.DEEPSEEK_API_KEY }}"),
        ("APIFY_TOKEN", "${{ secrets.APIFY_TOKEN }}"),
    ]
    assert not re.search(
        r"(?m)^\s+(?:OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY|"
        r"LWN_KEY|HORIZON_WEBHOOK_URL):",
        workflow,
    )


def test_runtime_secret_scan_precedes_pages_deployment():
    workflow = _read(WORKFLOW_PATH)
    scan = _step(workflow, "Check that runtime secrets were not written")
    deploy = _step(workflow, "Deploy to GitHub Pages")

    assert workflow.index(scan) < workflow.index(deploy)
    assert re.search(
        r"(?m)^        run: uv run python scripts/check_runtime_secrets\.py$",
        scan,
    )
    assert "DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}" in scan
    assert "APIFY_TOKEN: ${{ secrets.APIFY_TOKEN }}" in scan


def test_pages_deployment_keeps_upstream_publication_behavior():
    workflow = _read(WORKFLOW_PATH)
    deploy = _step(workflow, "Deploy to GitHub Pages")

    assert "uses: peaceiris/actions-gh-pages@v4" in deploy
    expected_settings = {
        "github_token": "${{ secrets.GITHUB_TOKEN }}",
        "publish_dir": "./docs",
        "keep_files": "true",
        "commit_message": '"Daily jersey intelligence: ${{ env.DATE }}"',
        "publish_branch": "gh-pages",
        "enable_jekyll": "true",
    }
    parsed_settings = dict(
        re.findall(r"(?m)^          ([a-z_]+):\s*(.+?)\s*$", deploy)
    )
    assert parsed_settings == expected_settings


def test_jekyll_config_has_chinese_branding_and_preserves_feed_defaults():
    config = _read(CONFIG_PATH)

    assert re.search(r"(?m)^theme: jekyll-theme-cayman$", config)
    assert re.search(r"(?m)^title: Horizon 篮球球衣商业情报$", config)
    assert re.search(
        r"(?m)^description: 每日汇总篮球球衣的设计灵感、市场商机与工艺供应链情报$",
        config,
    )
    assert re.search(r'(?m)^baseurl: "/Horizon"', config)
    assert re.search(r"(?ms)^plugins:\n  - jekyll-feed\nfeed:\n  path: feed\.xml$", config)
    assert re.search(
        r'(?ms)^defaults:\n  - scope:\n      path: ""\n      type: "posts"\n'
        r'    values:\n      layout: "default"$',
        config,
    )


def test_home_page_is_chinese_and_states_editorial_mix_and_empty_state():
    index = _read(INDEX_PATH)

    for expected in (
        "# Horizon 篮球球衣商业情报",
        "设计灵感 60%",
        "市场商机 30%",
        "工艺供应链 10%",
        "每天北京时间 08:00 左右更新",
        "首份每日简报正在生成中，请稍后再来查看。",
    ):
        assert expected in index

    for forbidden in (
        "Daily Digest",
        "Welcome to",
        "Documentation",
        "Configuration Guide",
        "Source Scrapers",
        "Scoring System",
        "No posts yet",
    ):
        assert forbidden not in index
