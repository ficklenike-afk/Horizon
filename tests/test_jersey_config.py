import json
import shutil

from src.models import AIProvider
from src.storage.manager import StorageManager


def test_github_config_is_jersey_business_profile(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copy("data/config.github.json", data_dir / "config.json")
    monkeypatch.setenv("TWITTER_ENABLED", "false")

    config = StorageManager(data_dir=str(data_dir)).load_config()

    assert config.ai.provider is AIProvider.DEEPSEEK
    assert config.ai.model == "deepseek-v4-flash"
    assert config.ai.api_key_env == "DEEPSEEK_API_KEY"
    assert config.ai.languages == ["zh"]
    assert config.filtering.ai_score_threshold == 6.5
    assert config.filtering.max_items == 20
    assert config.filtering.category_groups["design"].limit == 12
    assert config.filtering.category_groups["market"].limit == 6
    assert config.filtering.category_groups["supply"].limit == 2
    assert config.sources.hackernews.enabled is False
    assert config.sources.reddit.enabled is True
    assert config.sources.twitter is not None
    assert config.sources.twitter.enabled is False
    assert config.sources.twitter.mode == "apify"
    assert config.sources.twitter.fetch_reply_text is False
    assert config.sources.gdelt is not None
    assert config.sources.gdelt.enabled is True


def test_all_enabled_sources_have_business_categories(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copy("data/config.github.json", data_dir / "config.json")
    monkeypatch.setenv("TWITTER_ENABLED", "true")
    config = StorageManager(data_dir=str(data_dir)).load_config()
    allowed = {"design-inspiration", "market-opportunity", "supply-chain"}

    assert all(source.category in allowed for source in config.sources.rss)
    assert all(
        source.category in allowed
        for source in config.sources.reddit.subreddits
    )
    assert config.sources.twitter.category in allowed
    assert config.sources.gdelt.category in allowed


def test_github_config_preserves_task_6_twitter_lookback_contract():
    with open("data/config.github.json", encoding="utf-8") as config_file:
        raw = json.load(config_file)

    assert raw["sources"]["twitter"]["lookback_hours"] == 72
