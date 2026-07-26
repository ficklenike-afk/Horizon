import asyncio
from datetime import datetime, timezone

from src.ai.enricher import ContentEnricher
from src.models import ContentItem, SourceType


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
