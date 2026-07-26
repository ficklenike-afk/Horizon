"""Content enrichment using AI (second-pass analysis).

For items that pass the score threshold, this module:
1. Searches the web for relevant context (via DuckDuckGo)
2. Feeds search results + item content to AI to generate grounded background knowledge
"""

import asyncio
import json
import re
import sys
import os
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
from ddgs import DDGS

from .client import AIClient
from .prompts import (
    CONCEPT_EXTRACTION_SYSTEM, CONCEPT_EXTRACTION_USER,
    CONTENT_ENRICHMENT_SYSTEM, CONTENT_ENRICHMENT_USER,
)
from .utils import parse_json_response
from ..models import ContentItem


_CHINESE_TEXT = re.compile(r"[\u3400-\u9fff]")
_REQUIRED_ENRICHMENT_FIELDS = (
    "title_zh",
    "whats_new_zh",
    "business_value_zh",
)
_CATEGORY_FALLBACKS = {
    "design-inspiration": (
        "篮球球衣设计情报",
        "该条目属于设计灵感，建议结合原始来源核对配色、版型、字体、号码与原创性风险。",
    ),
    "market-opportunity": (
        "篮球球衣市场商机",
        "该条目属于市场商机，建议结合原始来源核对客户场景、时间窗口、需求信号与跟进行动。",
    ),
    "supply-chain": (
        "篮球球衣工艺供应链情报",
        "该条目属于工艺供应链，建议结合原始来源核对材料、质量、成本、起订量、交期与打样条件。",
    ),
}
_DEFAULT_FALLBACK = (
    "篮球球衣商业情报",
    "该条目属于篮球球衣商业情报，建议结合原始来源核对事实、适用场景与后续行动。",
)


class ContentEnricher:
    """Enriches high-scoring content items with background knowledge."""

    def __init__(self, ai_client: AIClient):
        self.client = ai_client

    def _get_concurrency(self) -> int:
        """Return the configured enrichment concurrency, clamped to 1 or above."""
        config = getattr(self.client, "config", None)
        concurrency = getattr(config, "enrichment_concurrency", 1)
        return max(concurrency, 1)

    async def enrich_batch(self, items: List[ContentItem]) -> None:
        """Enrich items in-place with background knowledge.

        Args:
            items: Content items to enrich (modified in-place)
        """
        concurrency = self._get_concurrency()
        semaphore = asyncio.Semaphore(concurrency)

        async def _process(item: ContentItem, progress_task) -> None:
            async with semaphore:
                try:
                    await self._enrich_item(item)
                except Exception as e:
                    print(f"Error enriching item {item.id}: {e}, falling back to translation")
                    await self._translate_item(item)
                finally:
                    self._ensure_chinese_fallback(item)
            progress.advance(progress_task)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Enriching", total=len(items))
            coros = [
                _process(item, task) for item in items
            ]
            await asyncio.gather(*coros)

    async def _web_search(self, query: str, max_results: int = 3) -> list:
        """Search the web for context via DuckDuckGo.

        Returns:
            List of dicts with keys: title, url, body
        """
        try:
            # Suppress primp "Impersonate ... does not exist" stderr warning
            stderr = sys.stderr
            sys.stderr = open(os.devnull, "w")
            try:
                ddgs = DDGS()
                results = await asyncio.to_thread(ddgs.text, query, max_results=max_results)
            finally:
                sys.stderr.close()
                sys.stderr = stderr
        except Exception:
            return []

        return [
            {"title": r.get("title", ""), "url": r.get("href", ""), "body": r.get("body", "")}
            for r in (results or [])
        ]

    @staticmethod
    def _parse_json_response(response: str) -> Optional[dict]:
        """Try multiple strategies to extract a JSON object from an AI response.

        Returns the parsed dict, or None if all strategies fail.
        """
        return parse_json_response(response)

    @staticmethod
    def _has_required_enrichment_shape(result: object) -> bool:
        return isinstance(result, dict) and all(
            isinstance(result.get(field), str) and result[field].strip()
            for field in _REQUIRED_ENRICHMENT_FIELDS
        )

    @staticmethod
    def _chinese_value(value: object) -> str:
        text = str(value or "").strip()
        return text if _CHINESE_TEXT.search(text) else ""

    def _ensure_chinese_fallback(self, item: ContentItem) -> None:
        category = str(item.metadata.get("category") or "")
        fallback_title, fallback_summary = _CATEGORY_FALLBACKS.get(
            category,
            _DEFAULT_FALLBACK,
        )

        title = self._chinese_value(item.metadata.get("title_zh"))
        if not title:
            title = self._chinese_value(item.ai_summary)
        if not title:
            title = self._chinese_value(item.ai_reason)
        item.metadata["title_zh"] = title[:60] if title else fallback_title

        summary_parts = []
        for value in (
            item.metadata.get("detailed_summary_zh"),
            item.ai_summary,
            item.ai_reason,
        ):
            text = self._chinese_value(value)
            if text and text not in summary_parts:
                summary_parts.append(text)
        detailed_summary = "；".join(summary_parts) if summary_parts else fallback_summary
        item.metadata["detailed_summary_zh"] = detailed_summary
        item.metadata["detailed_summary"] = detailed_summary

    async def _extract_concepts(self, item: ContentItem, content_text: str) -> List[str]:
        """Ask AI to identify concepts that need explanation.

        Args:
            item: Content item
            content_text: Extracted content text

        Returns:
            List of search queries for concepts that need explanation
        """
        user_prompt = CONCEPT_EXTRACTION_USER.format(
            title=item.title,
            summary=item.ai_summary or item.title,
            tags=", ".join(item.ai_tags) if item.ai_tags else "",
            content=content_text[:1000],
        )

        try:
            response = await self.client.complete(
                system=CONCEPT_EXTRACTION_SYSTEM,
                user=user_prompt,
            )
            result = self._parse_json_response(response)
            if result is None:
                return []
            queries = result.get("queries", [])
            return queries[:3]
        except Exception:
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=10)
    )
    async def _enrich_item(self, item: ContentItem) -> None:
        """Enrich a single item with background knowledge.

        Steps:
        1. Ask AI which concepts in the news need explanation
        2. Search the web for those concepts
        3. Ask AI to generate background based on search results

        Args:
            item: Content item to enrich (modified in-place via metadata)
        """
        # Extract content text and comments separately
        content_text = ""
        comments_text = ""
        if item.content:
            if "--- Top Comments ---" in item.content:
                main, comments_part = item.content.split("--- Top Comments ---", 1)
                content_text = main.strip()[:4000]
                comments_text = comments_part.strip()[:2000]
            else:
                content_text = item.content[:4000]

        # Step 1: AI identifies concepts to explain
        queries = await self._extract_concepts(item, content_text)

        # Step 2: Search web for each concept
        all_results = []
        web_sections = []
        for query in queries:
            results = await self._web_search(query)
            all_results.extend(results)
            if results:
                lines = [f"- [{r['title']}]({r['url']}): {r['body']}" for r in results]
                web_sections.append(f"**{query}:**\n" + "\n".join(lines))
        web_context = "\n\n".join(web_sections) if web_sections else ""

        # Index of available URLs for citation validation
        available_urls = {r["url"]: r["title"] for r in all_results if r.get("url")}

        # Step 3: AI generates background grounded in search results
        user_prompt = CONTENT_ENRICHMENT_USER.format(
            category=item.metadata.get("category", "unclassified"),
            title=item.title,
            url=str(item.url),
            summary=item.ai_summary or item.title,
            score=item.ai_score or 0,
            reason=item.ai_reason or "",
            tags=", ".join(item.ai_tags) if item.ai_tags else "",
            content=content_text,
            comments_section=f"\n**Community Comments:**\n{comments_text}" if comments_text else "",
            web_context=web_context or "No web search results available.",
        )

        response = await self.client.complete(
            system=CONTENT_ENRICHMENT_SYSTEM,
            user=user_prompt,
        )

        # Parse JSON response with robust fallback
        result = self._parse_json_response(response)
        if result is None or not self._has_required_enrichment_shape(result):
            # Gracefully degrade: fall back to a lightweight translation
            # instead of dropping the item untranslated.
            print(
                f"Warning: incomplete enrichment response for {item.id}, "
                "falling back to translation"
            )
            await self._translate_item(item)
            return

        title_zh = result.get("title_zh", "")
        if title_zh:
            item.metadata["title_zh"] = str(title_zh)

        for field in (
            "design_breakdown_zh",
            "business_value_zh",
            "recommended_action_zh",
            "ip_risk_zh",
            "background_zh",
            "community_discussion_zh",
        ):
            value = result.get(field, "")
            if value:
                item.metadata[field] = str(value)

        summary_parts = [
            str(result.get("whats_new_zh", "")).strip(),
            str(result.get("business_value_zh", "")).strip(),
        ]
        item.metadata["detailed_summary_zh"] = " ".join(
            part for part in summary_parts if part
        )
        item.metadata["detailed_summary"] = item.metadata["detailed_summary_zh"]
        item.metadata["background"] = item.metadata.get("background_zh", "")
        item.metadata["community_discussion"] = item.metadata.get(
            "community_discussion_zh", ""
        )

        # Store citation sources — only URLs that actually came from our search results
        if result.get("sources") and available_urls:
            valid = [
                {"url": u, "title": available_urls[u]}
                for u in result["sources"]
                if u in available_urls
            ]
            if valid:
                item.metadata["sources"] = valid

    async def _translate_item(self, item: ContentItem) -> None:
        """Lightweight translation fallback: when full enrichment fails, at least
        translate the title and summary to Chinese so the item is not dropped."""
        try:
            response = await self.client.complete(
                system="You are a translator. Translate to Simplified Chinese. Return only valid JSON, no other text.",
                user=(
                    f'Title: {item.title}\n'
                    f'Summary: {item.ai_summary or item.title}\n\n'
                    'Return JSON:\n'
                    '{"title_zh": "<中文标题>", "summary_zh": "<用中文写1-2句摘要>"}'
                ),
            )
            result = self._parse_json_response(response)
            if result:
                if result.get("title_zh"):
                    item.metadata["title_zh"] = result["title_zh"]
                if result.get("summary_zh"):
                    item.metadata["detailed_summary_zh"] = result["summary_zh"]
        except Exception:
            pass
