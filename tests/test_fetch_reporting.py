from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from rich.console import Console

from src.models import (
    ContentItem,
    GDELTConfig,
    RedditConfig,
    RedditSubredditConfig,
    RSSSourceConfig,
    SourceType,
    TwitterConfig,
)
from src.orchestrator import (
    FetchReport,
    HorizonOrchestrator,
    SourceFetchOutcome,
    build_source_warnings,
)
from src.scrapers.gdelt import GDELTScraper
from src.scrapers.reddit import RedditScraper
from src.scrapers.rss import RSSScraper
from src.scrapers.twitter import TwitterScraper


SINCE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_item(item_id: str) -> ContentItem:
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=item_id,
        url=f"https://example.com/{item_id}",
        content="content",
        author="tester",
        published_at=SINCE,
    )


def make_orchestrator() -> HorizonOrchestrator:
    orchestrator = object.__new__(HorizonOrchestrator)
    orchestrator.console = Console(file=StringIO())
    orchestrator.last_fetch_report = None
    return orchestrator


def make_sources(**overrides):  # type: ignore[no-untyped-def]
    values = {
        "github": [],
        "hackernews": SimpleNamespace(enabled=False),
        "rss": [],
        "reddit": SimpleNamespace(enabled=False),
        "telegram": SimpleNamespace(enabled=False),
        "twitter": None,
        "openbb": None,
        "ossinsight": SimpleNamespace(enabled=False),
        "gdelt": None,
        "google_news": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class StubScraper:
    def __init__(self, result=None, error: Exception | None = None):  # type: ignore[no-untyped-def]
        self.result = [] if result is None else result
        self.error = error

    async def fetch(self, since):  # type: ignore[no-untyped-def]
        if self.error:
            raise self.error
        return self.result


@pytest.mark.parametrize("analysis_result", ["empty", "all_failed"])
def test_languages_empty_skips_analysis_publication_validation(
    monkeypatch,
    analysis_result: str,
) -> None:
    orchestrator = make_orchestrator()
    orchestrator.config = SimpleNamespace(  # type: ignore[assignment]
        email=None,
        filtering=SimpleNamespace(time_window_hours=24),
        ai=SimpleNamespace(languages=[]),
    )
    orchestrator.email_manager = None
    orchestrator.webhook_notifier = None

    source_item = make_item("source")
    analyzed_items = [] if analysis_result == "empty" else [make_item("failed")]
    if analyzed_items:
        analyzed_items[0].metadata["analysis_failed"] = True

    orchestrator.fetch_all_sources = AsyncMock(return_value=[source_item])  # type: ignore[method-assign]
    orchestrator.merge_cross_source_duplicates = Mock(return_value=[source_item])  # type: ignore[method-assign]
    orchestrator._analyze_content = AsyncMock(return_value=analyzed_items)  # type: ignore[method-assign]
    orchestrator.filter_items = AsyncMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(items=[])
    )
    orchestrator._expand_twitter_discussion = AsyncMock()  # type: ignore[method-assign]
    orchestrator.apply_balanced_digest = Mock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(items=[])
    )
    orchestrator._enrich_important_items = AsyncMock()  # type: ignore[method-assign]

    analysis_validator = Mock()
    monkeypatch.setattr(
        "src.orchestrator.validate_analysis_health",
        analysis_validator,
    )

    asyncio.run(orchestrator.run())

    analysis_validator.assert_not_called()


def test_all_success_empty_has_normal_success_report(monkeypatch) -> None:
    orchestrator = make_orchestrator()
    orchestrator.config = SimpleNamespace(  # type: ignore[assignment]
        sources=make_sources(github=[object()]), extractors={}
    )
    monkeypatch.setattr(
        "src.orchestrator.GitHubScraper",
        lambda config, client: StubScraper(),
    )

    items = asyncio.run(orchestrator.fetch_all_sources(SINCE))

    assert items == []
    assert orchestrator.last_fetch_report is not None
    assert orchestrator.last_fetch_report.status == "success"
    assert orchestrator.last_fetch_report.all_failed is False
    assert orchestrator.last_fetch_report.to_dict()["empty"] == 1


def test_partial_failure_keeps_items_and_source_names(monkeypatch) -> None:
    orchestrator = make_orchestrator()
    kept = make_item("kept")
    orchestrator.config = SimpleNamespace(  # type: ignore[assignment]
        sources=make_sources(
            github=[object()], hackernews=SimpleNamespace(enabled=True)
        ),
        extractors={},
    )
    monkeypatch.setattr(
        "src.orchestrator.GitHubScraper",
        lambda config, client: StubScraper([kept]),
    )
    monkeypatch.setattr(
        "src.orchestrator.HackerNewsScraper",
        lambda config, client: StubScraper(error=ValueError("unavailable")),
    )

    items = asyncio.run(orchestrator.fetch_all_sources(SINCE))

    assert items == [kept]
    assert orchestrator.last_fetch_report is not None
    report = orchestrator.last_fetch_report
    assert [outcome.source_name for outcome in report.outcomes] == ["GitHub", "Hacker News"]
    assert report.status == "partial_failure"
    assert report.failed_count == 1
    source_reports = report.to_dict()["sources"]
    assert isinstance(source_reports, list)
    assert source_reports[1]["error"] == "ValueError: unavailable"


def test_fetch_failure_redacts_runtime_secret_from_outcome_and_console(
    monkeypatch,
) -> None:
    secret = "private-value"
    monkeypatch.setenv("APIFY_TOKEN", secret)
    orchestrator = make_orchestrator()

    outcome = asyncio.run(
        orchestrator._fetch_with_progress(
            "Twitter",
            StubScraper(error=RuntimeError(f"token={secret}")),
            SINCE,
        )
    )

    assert outcome.error is not None
    assert secret not in outcome.error
    assert secret not in orchestrator.console.file.getvalue()


def test_run_redacts_runtime_secret_from_console_and_failure_webhook(
    monkeypatch,
) -> None:
    secret = "private-value"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    orchestrator = make_orchestrator()
    orchestrator.config = SimpleNamespace(  # type: ignore[assignment]
        email=None,
        filtering=SimpleNamespace(time_window_hours=24),
    )
    orchestrator.email_manager = None
    send_failure = AsyncMock()
    orchestrator.webhook_notifier = SimpleNamespace(send_failure=send_failure)  # type: ignore[assignment]

    async def fetch_all_sources(since):  # type: ignore[no-untyped-def]
        raise RuntimeError(f"provider rejected key {secret}")

    monkeypatch.setattr(orchestrator, "fetch_all_sources", fetch_all_sources)

    with pytest.raises(RuntimeError):
        asyncio.run(orchestrator.run())

    error_message = send_failure.await_args.kwargs["error_message"]
    assert secret not in error_message
    assert secret not in orchestrator.console.file.getvalue()


def test_native_run_raises_when_every_attempted_source_failed(monkeypatch) -> None:
    orchestrator = make_orchestrator()
    orchestrator.config = SimpleNamespace(  # type: ignore[assignment]
        email=None,
        filtering=SimpleNamespace(time_window_hours=24),
    )
    orchestrator.email_manager = None
    send_failure = AsyncMock()
    orchestrator.webhook_notifier = SimpleNamespace(send_failure=send_failure)  # type: ignore[assignment]
    report = FetchReport(
        [
            SourceFetchOutcome("GitHub", "failure", error="RuntimeError: down"),
            SourceFetchOutcome("RSS Feeds", "failure", error="TimeoutError: slow"),
        ]
    )

    async def fetch_all_sources(since):  # type: ignore[no-untyped-def]
        orchestrator.last_fetch_report = report
        return []

    monkeypatch.setattr(orchestrator, "fetch_all_sources", fetch_all_sources)

    with pytest.raises(RuntimeError, match="All 2 attempted sources failed.*GitHub.*RSS Feeds"):
        asyncio.run(orchestrator.run())

    send_failure.assert_awaited_once()


def test_native_run_treats_all_success_empty_as_no_content(monkeypatch) -> None:
    orchestrator = make_orchestrator()
    orchestrator.config = SimpleNamespace(  # type: ignore[assignment]
        email=None,
        filtering=SimpleNamespace(time_window_hours=24),
    )
    orchestrator.email_manager = None
    send_failure = AsyncMock()
    orchestrator.webhook_notifier = SimpleNamespace(send_failure=send_failure)  # type: ignore[assignment]

    async def fetch_all_sources(since):  # type: ignore[no-untyped-def]
        orchestrator.last_fetch_report = FetchReport(
            [SourceFetchOutcome("RSS Feeds", "empty")]
        )
        return []

    monkeypatch.setattr(orchestrator, "fetch_all_sources", fetch_all_sources)

    asyncio.run(orchestrator.run())

    send_failure.assert_not_awaited()


def test_twitter_failure_and_empty_results_are_non_sensitive_warnings() -> None:
    failed = FetchReport(
        outcomes=[
            SourceFetchOutcome(
                source_name="Twitter",
                status="failure",
                error="token=private-value",
            ),
            SourceFetchOutcome(
                source_name="RSS Feeds",
                status="success",
                items=[],
            ),
        ]
    )
    empty = FetchReport(
        outcomes=[
            SourceFetchOutcome(
                source_name="Twitter",
                status="empty",
                items=[],
            )
        ]
    )

    failed_warnings = build_source_warnings(failed)
    empty_warnings = build_source_warnings(empty)

    assert failed_warnings == ["Twitter 本次抓取失败，其他来源继续运行。"]
    assert "private-value" not in repr(failed_warnings)
    assert empty_warnings == ["Twitter 本次未抓取到新内容，其他来源继续运行。"]


def test_source_warnings_cover_failures_but_ignore_other_empty_sources() -> None:
    report = FetchReport(
        outcomes=[
            SourceFetchOutcome("RSS Feeds", "failure", error="private detail"),
            SourceFetchOutcome("GitHub", "empty"),
        ]
    )

    warnings = build_source_warnings(report)

    assert warnings == ["RSS Feeds 本次抓取失败，其他来源继续运行。"]
    assert "private detail" not in repr(warnings)
    assert build_source_warnings(None) == []


@pytest.mark.parametrize("source_name", ["RSS Feeds", "Reddit", "GDELT", "Twitter"])
def test_active_scraper_terminal_failures_are_reported_as_failures(
    monkeypatch,
    source_name: str,
) -> None:
    monkeypatch.setenv("APIFY_TOKEN", "apify_api_test-only-value")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request, text="terminal failure")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    if source_name == "RSS Feeds":
        scraper = RSSScraper(
            [RSSSourceConfig(name="Broken feed", url="https://feeds.test/rss")],
            client,
        )
    elif source_name == "Reddit":
        scraper = RedditScraper(
            RedditConfig(
                enabled=True,
                subreddits=[
                    RedditSubredditConfig(
                        subreddit="UniWatch",
                        enabled=True,
                        fetch_limit=1,
                    )
                ],
                users=[],
                fetch_comments=0,
            ),
            client,
        )
    elif source_name == "GDELT":
        scraper = GDELTScraper(
            GDELTConfig(enabled=True, query="basketball jersey"),
            client,
        )
    else:
        scraper = TwitterScraper(
            TwitterConfig(
                enabled=True,
                users=["NBA"],
                apify_token_env="APIFY_TOKEN",
            ),
            client,
        )

    orchestrator = make_orchestrator()
    outcome = asyncio.run(
        orchestrator._fetch_with_progress(source_name, scraper, SINCE)
    )
    asyncio.run(client.aclose())

    assert outcome.status == "failure"
    assert outcome.items == []


def test_rss_partial_sub_source_failure_keeps_items_and_safe_diagnostics() -> None:
    feed = """\
    <rss version="2.0"><channel><title>Test</title>
      <item><guid>kept</guid><title>Kept item</title>
        <link>https://news.test/kept</link>
        <pubDate>Fri, 02 Jan 2026 12:00:00 GMT</pubDate>
      </item>
    </channel></rss>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "healthy.test":
            return httpx.Response(200, request=request, text=feed)
        return httpx.Response(500, request=request, text="private upstream detail")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scraper = RSSScraper(
        [
            RSSSourceConfig(name="Healthy feed", url="https://healthy.test/rss"),
            RSSSourceConfig(name="Broken feed", url="https://broken.test/rss"),
        ],
        client,
    )
    orchestrator = make_orchestrator()

    outcome = asyncio.run(
        orchestrator._fetch_with_progress("RSS Feeds", scraper, SINCE)
    )
    asyncio.run(client.aclose())

    assert outcome.status == "success"
    assert [item.title for item in outcome.items] == ["Kept item"]
    assert outcome.warnings == ["Broken feed failed"]
    assert "private upstream detail" not in repr(outcome.to_dict())


def test_chinese_run_writes_chinese_only_post_front_matter(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    orchestrator = make_orchestrator()
    item = make_item("selected")
    item.ai_score = 8.5
    item.ai_summary = "城市主题篮球球衣采用本地文化纹样。"
    item.ai_reason = "设计叙事清楚。"
    item.ai_tags = ["城市文化"]
    item.metadata.update(
        {
            "category": "design-inspiration",
            "title_zh": "城市文化篮球球衣发布",
            "detailed_summary_zh": "城市主题篮球球衣采用本地文化纹样。",
            "design_breakdown_zh": "配色与号码形成清楚层级。",
            "business_value_zh": "适合校园球队原创设计。",
            "recommended_action_zh": "先制作本地文化纹样草案。",
            "ip_risk_zh": "不要复制球队注册标识。",
            "analysis_failed": False,
        }
    )
    orchestrator.config = SimpleNamespace(  # type: ignore[assignment]
        email=None,
        filtering=SimpleNamespace(time_window_hours=24),
        ai=SimpleNamespace(languages=["zh"]),
        sources=SimpleNamespace(twitter=None),
    )
    orchestrator.storage = SimpleNamespace(  # type: ignore[assignment]
        save_daily_summary=Mock(return_value=tmp_path / "summary.md")
    )
    orchestrator.email_manager = None
    orchestrator.webhook_notifier = None
    orchestrator.fetch_all_sources = AsyncMock(return_value=[item])  # type: ignore[method-assign]
    orchestrator.merge_cross_source_duplicates = Mock(return_value=[item])  # type: ignore[method-assign]
    orchestrator._analyze_content = AsyncMock(return_value=[item])  # type: ignore[method-assign]
    orchestrator.filter_items = AsyncMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(items=[item])
    )
    orchestrator._expand_twitter_discussion = AsyncMock()  # type: ignore[method-assign]
    orchestrator.apply_balanced_digest = Mock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(items=[item])
    )
    orchestrator._enrich_important_items = AsyncMock()  # type: ignore[method-assign]

    asyncio.run(orchestrator.run())

    posts = list((tmp_path / "docs" / "_posts").glob("*-summary-zh.md"))
    assert len(posts) == 1
    post = posts[0].read_text(encoding="utf-8")
    date = posts[0].name.removesuffix("-summary-zh.md")
    assert f'title: "篮球球衣商业情报：{date}"' in post
    assert "Horizon Summary" not in post
    assert "(ZH)" not in post
