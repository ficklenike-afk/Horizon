import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
import src.ai.analyzer as analyzer_module
from src.ai.analyzer import ContentAnalyzer
from src.ai.prompts import CONTENT_ANALYSIS_SYSTEM
from src.models import ContentItem, SourceType


def _make_item(item_id: str) -> ContentItem:
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=f"Item {item_id}",
        url="https://example.com/item",
        published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )


def test_analyze_batch_does_not_sleep_by_default(monkeypatch):
    analyzer = ContentAnalyzer(SimpleNamespace())
    items = [_make_item("rss:test:1"), _make_item("rss:test:2")]
    sleep_calls = []

    async def fake_analyze_item(item):
        item.ai_score = 8.0

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(analyzer, "_analyze_item", fake_analyze_item)
    monkeypatch.setattr(analyzer_module.asyncio, "sleep", fake_sleep)

    result = asyncio.run(analyzer.analyze_batch(items))

    assert len(result) == 2
    assert sleep_calls == []


def test_analyze_batch_sleeps_between_items_when_throttle_configured(monkeypatch):
    client = SimpleNamespace(config=SimpleNamespace(throttle_sec=1.5))
    analyzer = ContentAnalyzer(client)
    items = [_make_item("rss:test:1"), _make_item("rss:test:2"), _make_item("rss:test:3")]
    sleep_calls = []

    async def fake_analyze_item(item):
        item.ai_score = 8.0

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(analyzer, "_analyze_item", fake_analyze_item)
    monkeypatch.setattr(analyzer_module.asyncio, "sleep", fake_sleep)

    asyncio.run(analyzer.analyze_batch(items))

    assert sleep_calls == [1.5, 1.5]


def test_analyze_batch_concurrent_processing(monkeypatch):
    """Verify that higher concurrency allows overlapping item processing."""
    client = SimpleNamespace(config=SimpleNamespace(analysis_concurrency=3))
    analyzer = ContentAnalyzer(client)
    items = [_make_item(f"rss:test:{i}") for i in range(5)]
    active_count = 0
    max_active = 0

    async def fake_analyze_item(item):
        nonlocal active_count, max_active
        active_count += 1
        max_active = max(max_active, active_count)
        await asyncio.sleep(0.05)  # Small delay to allow overlap
        active_count -= 1

    monkeypatch.setattr(analyzer, "_analyze_item", fake_analyze_item)

    asyncio.run(analyzer.analyze_batch(items))

    assert max_active == 3
    assert all(item.ai_score is None for item in items)  # None because fake_analyze_item doesn't set it


def test_analyze_batch_concurrent_preserves_order(monkeypatch):
    """Verify that analyze_batch preserves input order in results."""
    client = SimpleNamespace(config=SimpleNamespace(analysis_concurrency=3))
    analyzer = ContentAnalyzer(client)
    items = [_make_item(f"rss:test:{i}") for i in range(5)]

    async def fake_analyze_item(item):
        item.ai_score = float(item.id.split(":")[-1]) * 10

    monkeypatch.setattr(analyzer, "_analyze_item", fake_analyze_item)

    result = asyncio.run(analyzer.analyze_batch(items))

    assert [item.id for item in result] == [item.id for item in items]


def test_analyze_item_accepts_valid_result():
    result = {
        "score": 8.5,
        "reason": "Relevant",
        "summary": "A useful update",
        "tags": ["ai", "research"],
    }
    client = SimpleNamespace(complete=lambda **kwargs: None)

    async def complete(**kwargs):
        return json.dumps(result)

    client.complete = complete
    item = _make_item("rss:test:valid")

    asyncio.run(ContentAnalyzer(client)._analyze_item(item))

    assert item.ai_score == 8.5
    assert item.ai_reason == "Relevant"
    assert item.ai_summary == "A useful update"
    assert item.ai_tags == ["ai", "research"]


@pytest.mark.parametrize(
    "result",
    [
        {"score": 11, "reason": "high", "summary": "summary", "tags": []},
        {"score": float("nan"), "reason": "bad", "summary": "summary", "tags": []},
        {"score": 5, "reason": 123, "summary": "summary", "tags": []},
        {"score": 5, "reason": "ok", "summary": "summary", "tags": ["ok", 1]},
        {"score": 5, "reason": "ok", "tags": []},
    ],
)
def test_analyze_item_malformed_json_result_uses_fallback(result):
    async def complete(**kwargs):
        return json.dumps(result)

    item = _make_item("rss:test:invalid")

    asyncio.run(ContentAnalyzer(SimpleNamespace(complete=complete))._analyze_item(item))

    assert item.ai_score == 0.0
    assert item.ai_reason == "Analysis response parse failed"
    assert item.ai_summary == item.title
    assert item.ai_tags == []


class CapturingJerseyClient:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    async def complete(self, system, user, temperature=None, max_tokens=None):
        self.calls.append((system, user))
        return self.response


def _jersey_item(category="design-inspiration"):
    return ContentItem(
        id="rss:jersey-1",
        source_type=SourceType.RSS,
        title="New city-inspired basketball uniform unveiled",
        url="https://example.com/jersey",
        content="The uniform uses a local river pattern and custom numerals.",
        published_at=datetime.now(timezone.utc),
        metadata={"category": category},
    )


def test_analyzer_sends_business_category_and_marks_success():
    client = CapturingJerseyClient(
        '{"score": 8.5, "reason": "原创视觉叙事清楚", '
        '"summary": "一套城市文化篮球服。", '
        '"tags": ["球衣设计", "城市文化", "号码字体"]}'
    )
    analyzer = ContentAnalyzer(client)
    item = _jersey_item()

    asyncio.run(analyzer._analyze_item(item))

    assert "Category: design-inspiration" in client.calls[0][1]
    assert item.metadata["analysis_failed"] is False
    assert item.ai_score == 8.5


def test_analyzer_marks_unparseable_response_as_failed():
    client = CapturingJerseyClient("not-json")
    analyzer = ContentAnalyzer(client)
    item = _jersey_item("market-opportunity")

    asyncio.run(analyzer._analyze_item(item))

    assert item.metadata["analysis_failed"] is True
    assert item.ai_score == 0.0


def test_analyze_batch_marks_exception_as_failed(monkeypatch):
    async def failing_analysis(item):
        raise RuntimeError("client unavailable")

    analyzer = ContentAnalyzer(CapturingJerseyClient("unused"))
    item = _jersey_item()
    monkeypatch.setattr(analyzer, "_analyze_item", failing_analysis)

    asyncio.run(analyzer.analyze_batch([item]))

    assert item.metadata["analysis_failed"] is True
    assert item.ai_score == 0.0


def test_analysis_prompt_is_not_tech_news_prompt():
    assert "篮球球衣套装定制创业者" in CONTENT_ANALYSIS_SYSTEM
    assert "设计灵感" in CONTENT_ANALYSIS_SYSTEM
    assert "市场商机" in CONTENT_ANALYSIS_SYSTEM
    assert "工艺供应链" in CONTENT_ANALYSIS_SYSTEM
    assert "relevance to software engineering" not in CONTENT_ANALYSIS_SYSTEM
