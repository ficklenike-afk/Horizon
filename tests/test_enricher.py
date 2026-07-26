import asyncio
from datetime import datetime, timezone

from src.ai.enricher import ContentEnricher
from src.models import ContentItem, SourceType
from src.services.publication_validator import validate_selected_items


class FakeEnrichmentClient:
    def __init__(self, response: str):
        self.response = response

    async def complete(self, system, user, temperature=None, max_tokens=None):
        return self.response


def _enrichment_item():
    return ContentItem(
        id="rss:jersey-enrichment-1",
        source_type=SourceType.RSS,
        title="New city-inspired basketball uniform unveiled",
        url="https://example.com/jersey-enrichment",
        content="The uniform uses a local river pattern and custom numerals.",
        published_at=datetime.now(timezone.utc),
        metadata={"category": "design-inspiration"},
    )


def _analyzed_item(index: int = 1) -> ContentItem:
    item = _enrichment_item()
    item.id = f"rss:jersey-enrichment-{index}"
    item.title = f"English raw jersey title {index}"
    item.url = f"https://example.com/jersey-enrichment-{index}"
    item.ai_score = 8.5
    item.ai_summary = f"城市主题球衣采用本地文化纹样 {index}"
    item.ai_reason = "设计叙事清楚，适合校园球队提炼原创方法"
    item.ai_tags = ["球衣设计", "城市文化"]
    return item


async def _no_concepts(item, content):
    return []


def test_enricher_stores_jersey_business_fields(monkeypatch):
    response = """{
      "title_zh": "城市河流纹样篮球服发布",
      "whats_new_zh": "新球衣以城市河流为主视觉。",
      "design_breakdown_zh": "蓝绿渐变、无衬线号码和斜向水纹构成速度感。",
      "business_value_zh": "适合借鉴到校园和城市赛事主题套装。",
      "recommended_action_zh": "建立三套本地文化纹样草案并进行原创性筛查。",
      "ip_risk_zh": "不得复制球队徽标和独特水纹组合。",
      "background_zh": "城市版球衣常用地方文化建立身份认同。",
      "community_discussion_zh": "",
      "sources": []
    }"""
    client = FakeEnrichmentClient(response)
    enricher = ContentEnricher(client)
    item = _enrichment_item()
    item.ai_score = 8.5
    item.ai_reason = "设计叙事清楚"
    item.ai_summary = "城市主题球衣"
    item.ai_tags = ["球衣设计", "城市文化"]

    async def no_concepts(item, content):
        return []

    monkeypatch.setattr(enricher, "_extract_concepts", no_concepts)
    asyncio.run(enricher._enrich_item(item))

    assert item.metadata["title_zh"] == "城市河流纹样篮球服发布"
    assert "蓝绿渐变" in item.metadata["design_breakdown_zh"]
    assert "校园" in item.metadata["business_value_zh"]
    assert "建立三套" in item.metadata["recommended_action_zh"]
    assert "不得复制" in item.metadata["ip_risk_zh"]
    assert "新球衣" in item.metadata["detailed_summary_zh"]


def test_malformed_enrichment_and_translation_use_chinese_analysis_fallback(
    monkeypatch,
):
    client = FakeEnrichmentClient("not valid json")
    enricher = ContentEnricher(client)
    item = _analyzed_item()
    monkeypatch.setattr(enricher, "_extract_concepts", _no_concepts)

    asyncio.run(enricher.enrich_batch([item]))

    assert item.metadata["title_zh"]
    assert item.title not in item.metadata["title_zh"]
    assert "城市主题球衣" in item.metadata["title_zh"]
    assert "设计叙事清楚" in item.metadata["detailed_summary_zh"]
    validate_selected_items([item])


def test_structurally_incomplete_enrichment_uses_category_safe_chinese_fallback(
    monkeypatch,
):
    client = FakeEnrichmentClient('{"title_zh": "", "sources": []}')
    enricher = ContentEnricher(client)
    item = _analyzed_item()
    item.ai_summary = ""
    item.ai_reason = ""
    monkeypatch.setattr(enricher, "_extract_concepts", _no_concepts)

    asyncio.run(enricher.enrich_batch([item]))

    assert item.metadata["title_zh"] == "篮球球衣设计情报"
    assert item.title not in item.metadata["title_zh"]
    assert "设计灵感" in item.metadata["detailed_summary_zh"]
    validate_selected_items([item])


def test_one_enrichment_and_translation_exception_does_not_block_other_item(
    monkeypatch,
):
    complete_response = """{
      "title_zh": "城市河流纹样篮球服发布",
      "whats_new_zh": "新球衣采用城市河流纹样。",
      "business_value_zh": "可用于校园球队的原创设计方法。",
      "recommended_action_zh": "先制作原创纹样草案。",
      "ip_risk_zh": "不得复制球队标识。",
      "sources": []
    }"""

    class ItemAwareClient:
        async def complete(self, system, user, temperature=None, max_tokens=None):
            if "English raw jersey title 1" in user:
                raise RuntimeError("one item failed")
            return complete_response

    enricher = ContentEnricher(ItemAwareClient())
    failed = _analyzed_item(1)
    succeeded = _analyzed_item(2)
    monkeypatch.setattr(enricher, "_extract_concepts", _no_concepts)

    asyncio.run(enricher.enrich_batch([failed, succeeded]))

    assert failed.metadata["title_zh"]
    assert failed.metadata["detailed_summary_zh"]
    assert succeeded.metadata["title_zh"] == "城市河流纹样篮球服发布"
    validate_selected_items([failed, succeeded])
