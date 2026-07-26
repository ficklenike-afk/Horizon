"""Publication safety checks that must pass before report files are written."""

import os
import re
import string
from collections import Counter
from html import unescape
from typing import Iterable
from urllib.parse import unquote, urlparse

from ..models import ContentItem


LIMITS = {
    "design-inspiration": 12,
    "market-opportunity": 6,
    "supply-chain": 2,
}
_UNRESOLVED_ENV = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}")
_REQUIRED_SECTION_PATTERNS = (
    r"^## 设计灵感（\d+）$",
    r"^## 市场商机（\d+）$",
    r"^## 工艺供应链（\d+）$",
)
_SOURCE_LINK = re.compile(r"\[[^\]]+\]\(https?://[^)]+\)")
_RUNTIME_SECRET_ENV_NAMES = ("DEEPSEEK_API_KEY", "APIFY_TOKEN")


class PublicationValidationError(RuntimeError):
    """Raised when generated content is unsafe or structurally incomplete."""


def redact_runtime_secrets(value: object) -> str:
    """Return text with configured runtime secret values replaced."""
    redacted = str(value)
    for env_name in _RUNTIME_SECRET_ENV_NAMES:
        secret = os.getenv(env_name, "")
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def canonicalize_secret_text(value: str | bytes) -> str:
    """Decode common publication escaping without changing letter case."""
    text = value.decode("utf-8", errors="ignore") if isinstance(value, bytes) else value
    for _ in range(3):
        decoded = unquote(unescape(text))
        normalized: list[str] = []
        index = 0
        while index < len(decoded):
            if (
                decoded[index] == "\\"
                and index + 1 < len(decoded)
                and decoded[index + 1] in string.punctuation
            ):
                index += 1
            normalized.append(decoded[index])
            index += 1
        canonical = "".join(normalized)
        if canonical == text:
            return canonical
        text = canonical
    return text


def contains_secret_value(
    content: str | bytes,
    secret_values: Iterable[str],
) -> bool:
    """Detect raw or commonly escaped non-empty secret values."""
    canonical_content = canonicalize_secret_text(content)
    for secret in secret_values:
        if not secret:
            continue
        canonical_secret = canonicalize_secret_text(secret)
        if canonical_secret and canonical_secret in canonical_content:
            return True
    return False


def validate_analysis_health(items: list[ContentItem]) -> None:
    """Require at least one successfully analyzed content item."""
    if not items:
        raise PublicationValidationError("No content was available for AI analysis")
    if all(item.metadata.get("analysis_failed") is True for item in items):
        raise PublicationValidationError("AI analysis failed for every content item")


def validate_selected_items(items: list[ContentItem]) -> None:
    """Validate the final bounded, classified set selected for publication."""
    if not items:
        raise PublicationValidationError("No content passed the publication threshold")
    if len(items) > 20:
        raise PublicationValidationError("Selected item count exceeds limit 20")

    counts = Counter(
        str(item.metadata.get("category", "unclassified")) for item in items
    )
    for category, count in counts.items():
        if category not in LIMITS:
            raise PublicationValidationError(
                f"Selected item has unsupported category: {category}"
            )
        if count > LIMITS[category]:
            raise PublicationValidationError(
                f"Category {category} exceeds limit {LIMITS[category]}"
            )

    for item in items:
        parsed = urlparse(str(item.url))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise PublicationValidationError("Selected item has invalid URL")
        if not str(item.metadata.get("title_zh", "")).strip():
            raise PublicationValidationError("Selected item has no Chinese title")


def validate_markdown(
    markdown: str,
    secret_values: Iterable[str],
    language: str = "zh",
) -> None:
    """Reject unsafe or incomplete generated Markdown before publication."""
    if not markdown.strip():
        raise PublicationValidationError("Generated Markdown is empty")
    if _UNRESOLVED_ENV.search(markdown):
        raise PublicationValidationError(
            "Generated Markdown contains unresolved environment reference"
        )
    if contains_secret_value(markdown, secret_values):
        raise PublicationValidationError(
            "Generated Markdown contains a runtime secret"
        )
    if language.lower().startswith("zh"):
        for pattern in _REQUIRED_SECTION_PATTERNS:
            if re.search(pattern, markdown, flags=re.MULTILINE) is None:
                raise PublicationValidationError(
                    "Generated Markdown is missing a required category section"
                )
    if _SOURCE_LINK.search(markdown) is None:
        raise PublicationValidationError("Generated Markdown contains no source link")
