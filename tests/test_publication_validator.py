from datetime import datetime, timezone

import pytest

from src.models import ContentItem, SourceType
from src.services.publication_validator import (
    PublicationValidationError,
    validate_analysis_health,
    validate_markdown,
    validate_selected_items,
)


def _item(category: str = "design-inspiration", index: int = 1) -> ContentItem:
    return ContentItem(
        id=f"rss:{index}",
        source_type=SourceType.RSS,
        title=f"Item {index}",
        url=f"https://example.com/{index}",
        published_at=datetime.now(timezone.utc),
        ai_score=8.0,
        ai_summary="摘要",
        metadata={
            "category": category,
            "title_zh": f"中文标题 {index}",
            "analysis_failed": False,
        },
    )


def _valid_markdown() -> str:
    return (
        "# 篮球球衣商业情报\n"
        "## 设计灵感（1）\n"
        "### [中文标题](https://example.com/1)\n"
        "## 市场商机（0）\n"
        "## 工艺供应链（0）\n"
    )


def test_rejects_empty_or_all_failed_analysis() -> None:
    with pytest.raises(PublicationValidationError, match="No content"):
        validate_analysis_health([])

    items = [_item()]
    items[0].metadata["analysis_failed"] = True
    with pytest.raises(PublicationValidationError, match="AI analysis failed"):
        validate_analysis_health(items)


def test_accepts_analysis_when_at_least_one_item_succeeded() -> None:
    items = [_item(index=1), _item(index=2)]
    items[0].metadata["analysis_failed"] = True

    validate_analysis_health(items)


def test_rejects_empty_or_unclassified_selected_items() -> None:
    with pytest.raises(PublicationValidationError, match="No content passed"):
        validate_selected_items([])

    with pytest.raises(PublicationValidationError, match="unclassified"):
        validate_selected_items([_item("unclassified")])


@pytest.mark.parametrize(
    ("category", "count"),
    [
        ("design-inspiration", 13),
        ("market-opportunity", 7),
        ("supply-chain", 3),
    ],
)
def test_rejects_category_over_limit(category: str, count: int) -> None:
    items = [_item(category, index) for index in range(count)]

    with pytest.raises(PublicationValidationError, match=category):
        validate_selected_items(items)


def test_rejects_more_than_twenty_selected_items() -> None:
    items = (
        [_item("design-inspiration", index) for index in range(1, 14)]
        + [_item("market-opportunity", index) for index in range(14, 21)]
        + [_item("supply-chain", 21)]
    )

    with pytest.raises(PublicationValidationError, match="limit 20"):
        validate_selected_items(items)


def test_rejects_selected_item_without_chinese_title() -> None:
    item = _item()
    item.metadata["title_zh"] = "  "

    with pytest.raises(PublicationValidationError, match="Chinese title"):
        validate_selected_items([item])


def test_rejects_selected_item_with_invalid_url() -> None:
    item = _item()
    item.url = "ftp://example.com/private"  # type: ignore[assignment]

    with pytest.raises(PublicationValidationError, match="invalid URL"):
        validate_selected_items([item])


def test_accepts_valid_selected_items() -> None:
    items = [
        _item("design-inspiration", 1),
        _item("market-opportunity", 2),
        _item("supply-chain", 3),
    ]

    validate_selected_items(items)


def test_rejects_empty_markdown() -> None:
    with pytest.raises(PublicationValidationError, match="empty"):
        validate_markdown(" \n", [])


def test_rejects_secret_or_unresolved_env_before_structure_errors() -> None:
    with pytest.raises(PublicationValidationError, match="secret"):
        validate_markdown("report contains runtime-secret", ["runtime-secret"])

    with pytest.raises(PublicationValidationError, match="environment"):
        validate_markdown("report contains ${MISSING_VALUE}", [])


@pytest.mark.parametrize(
    "escaped_secret",
    [
        r"apify\_api\_secret",
        "apify&#95;api&#95;secret",
        "apify%5Fapi%5Fsecret",
    ],
)
def test_rejects_escaped_runtime_secret(escaped_secret: str) -> None:
    with pytest.raises(PublicationValidationError, match="secret"):
        validate_markdown(
            f"report contains {escaped_secret}",
            ["apify_api_secret"],
        )


def test_rejects_markdown_without_grouped_sections_or_source_link() -> None:
    sections_only = (
        "## 设计灵感（1）\n"
        "## 市场商机（0）\n"
        "## 工艺供应链（0）\n"
    )
    with pytest.raises(PublicationValidationError, match="category section"):
        validate_markdown("# 篮球球衣商业情报", [], language="zh")
    with pytest.raises(PublicationValidationError, match="source link"):
        validate_markdown(sections_only, [])


def test_accepts_english_markdown_without_chinese_sections() -> None:
    markdown = (
        "# Basketball Jersey Intelligence\n"
        "## Design Inspiration\n"
        "- [Original source](https://example.com/jersey)\n"
    )

    validate_markdown(markdown, [], language="en")


def test_accepts_complete_safe_markdown() -> None:
    validate_markdown(_valid_markdown(), ["runtime-secret"])
