# Horizon Basketball Jersey Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Horizon 改造成每天北京时间 08:00 发布中文篮球球衣设计、市场商机和供应链情报的公开 GitHub Pages 系统。

**Architecture:** 保留 Horizon 的抓取、去重、AI 分析和 Pages 发布流水线，在专业版分支中替换行业评分/补充提示词、增加类别化中文渲染、Twitter 独立回看窗口和发布前验证。运行环境为 GitHub Actions；DeepSeek V4 Flash 负责 AI，Apify 每周一、三、五抓取 X/Twitter，其他来源每天运行。

**Tech Stack:** Python 3.12、Pydantic 2、httpx、DeepSeek OpenAI-compatible API、Apify Scweet Actor、pytest、uv、GitHub Actions、Jekyll/GitHub Pages。

## Global Constraints

- 公开仓库名称沿用 `Horizon`，保留 `Thysrael/Horizon` 为 `upstream`。
- 每天北京时间 08:00 运行；GitHub Actions cron 为 `0 0 * * *`。
- 只生成简体中文日报。
- AI 为 `provider=deepseek`、`model=deepseek-v4-flash`、`api_key_env=DEEPSEEK_API_KEY`。
- X/Twitter 使用 Apify，周一、三、五启用，独立回看 72 小时，不抓回复。
- 每日最多 20 条：设计灵感 12 条、市场商机 6 条、工艺供应链 2 条。
- 评分阈值固定为 6.5；内容不足时不使用低质量条目填充。
- `DEEPSEEK_API_KEY` 和 `APIFY_TOKEN` 只能存在于 GitHub Secrets/运行时环境，不能写入仓库、日志或网页。
- 第一版不实现飞书、邮件、Webhook、Instagram、小红书、Pinterest、Behance、本地部署或自动客户联系。
- 所有功能改动遵循测试驱动开发；每个任务完成后运行目标测试并提交。

---

## File Structure Map

### 配置与部署

- `data/config.github.json`：生产环境的 DeepSeek、信息源、分类和 12/6/2 配额。
- `.github/workflows/daily-summary.yml`：08:00 定时、北京时间星期判断、Secret 注入和 Pages 发布。
- `docs/_config.yml`：篮球球衣情报站点名称与 Jekyll 配置。
- `docs/index.md`：中文首页和日报归档入口。

### 专业 AI 流水线

- `src/ai/prompts.py`：篮球球衣行业评分、概念提取和中文 enrichment 提示词。
- `src/ai/analyzer.py`：把来源类别传给评分模型，并记录分析健康状态。
- `src/ai/enricher.py`：保存设计拆解、商业价值、行动建议和 IP 风险字段。
- `src/ai/summarizer.py`：按三类分组，生成趋势信号、今日行动建议和专业条目。

### 抓取与安全

- `src/models.py`：为 Twitter 增加 `lookback_hours` 配置。
- `src/scrapers/twitter.py`：计算 Twitter 独立回看窗口。
- `src/services/publication_validator.py`：验证 AI 健康度、配额、链接、中文字段和秘密泄露。
- `scripts/check_runtime_secrets.py`：扫描工作树，确认运行时 Secret 值未落盘。
- `src/orchestrator.py`：在写文件和发布前调用验证器，并把来源失败写成非敏感提示。

### 测试

- `tests/test_jersey_config.py`：生产配置。
- `tests/test_analyzer.py`：类别传递、专业提示词、分析失败标记。
- `tests/test_enricher.py`：专业中文元数据。
- `tests/test_summarizer.py`：分组日报、趋势、行动建议和 IP 提醒。
- `tests/test_twitter.py`：72 小时独立回看。
- `tests/test_publication_validator.py`：发布前拦截规则。
- `tests/test_secret_scan.py`：运行时秘密落盘扫描。
- `tests/test_deployment_files.py`：cron、星期、环境变量、Pages 和中文品牌。

---

### Task 1: Fork、隔离工作区与基线

**Files:**
- Create in fork: `docs/superpowers/specs/2026-07-26-horizon-basketball-jersey-intelligence-design.md`
- Create in fork: `docs/superpowers/plans/2026-07-26-horizon-basketball-jersey-intelligence.md`

**Interfaces:**
- Consumes: GitHub 登录态、上游仓库 `Thysrael/Horizon`。
- Produces: 用户公开 fork、本地隔离 worktree、通过的上游测试基线。

- [ ] **Step 1: 在执行会话中加载隔离工作区技能**

使用 `using-git-worktrees`，不要直接在 Obsidian Vault 根目录实现代码。目标分支固定为：

```text
feat/basketball-jersey-intelligence
```

- [ ] **Step 2: 创建并克隆公开 fork**

优先使用已登录的 GitHub 工具或浏览器完成 fork；若 `gh` 可用，运行：

```powershell
gh auth status
gh repo fork Thysrael/Horizon --clone --remote --default-branch-only
Set-Location Horizon
git remote -v
```

预期：`origin` 指向用户的 `Horizon`，`upstream` 指向 `Thysrael/Horizon`。

- [ ] **Step 3: 建立功能分支/工作树**

由 `using-git-worktrees` 选择安全目录后创建：

```powershell
git fetch upstream main
git worktree add ..\Horizon-jersey-intelligence -b feat/basketball-jersey-intelligence upstream/main
Set-Location ..\Horizon-jersey-intelligence
```

预期：`git status --short --branch` 显示干净的 `feat/basketball-jersey-intelligence`。

- [ ] **Step 4: 安装开发依赖并验证基线**

```powershell
uv sync --extra dev
uv run pytest -q
```

预期：现有测试全部通过，零失败。

- [ ] **Step 5: 将已批准的设计和计划加入 fork**

从已批准的 Obsidian 文档复制到 fork，并逐文件核对 SHA-256：

```powershell
$approvedRoot = 'C:\Users\34550\Documents\Obsidian Vault\CHIYARD炽野\docs\superpowers'
New-Item -ItemType Directory -Force -Path 'docs\superpowers\specs', 'docs\superpowers\plans'
Copy-Item -LiteralPath "$approvedRoot\specs\2026-07-26-horizon-basketball-jersey-intelligence-design.md" -Destination 'docs\superpowers\specs\2026-07-26-horizon-basketball-jersey-intelligence-design.md'
Copy-Item -LiteralPath "$approvedRoot\plans\2026-07-26-horizon-basketball-jersey-intelligence.md" -Destination 'docs\superpowers\plans\2026-07-26-horizon-basketball-jersey-intelligence.md'
Get-FileHash -Algorithm SHA256 -LiteralPath "$approvedRoot\specs\2026-07-26-horizon-basketball-jersey-intelligence-design.md", 'docs\superpowers\specs\2026-07-26-horizon-basketball-jersey-intelligence-design.md'
Get-FileHash -Algorithm SHA256 -LiteralPath "$approvedRoot\plans\2026-07-26-horizon-basketball-jersey-intelligence.md", 'docs\superpowers\plans\2026-07-26-horizon-basketball-jersey-intelligence.md'
git add docs/superpowers/specs/2026-07-26-horizon-basketball-jersey-intelligence-design.md docs/superpowers/plans/2026-07-26-horizon-basketball-jersey-intelligence.md
git commit -m "docs: add basketball jersey intelligence design"
```

预期：每组源文件与目标文件的哈希值一致。

---

### Task 2: 生产配置、信息源和 12/6/2 配额

**Files:**
- Modify: `data/config.github.json`
- Create: `tests/test_jersey_config.py`

**Interfaces:**
- Consumes: Horizon `Config`、`StorageManager` 和 `${VAR_NAME}` 环境变量展开。
- Produces: 可被 Actions 直接复制为 `data/config.json` 的完整生产配置。

- [ ] **Step 1: 写生产配置失败测试**

创建 `tests/test_jersey_config.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
uv run pytest tests/test_jersey_config.py -v
```

预期：因原 `config.github.json` 仍含科技信息源、双语输出和旧配额而失败。

- [ ] **Step 3: 写入完整生产配置**

用以下结构替换 `data/config.github.json`。Google News RSS URL 保留 Unicode 查询，Pydantic `HttpUrl` 会在运行时规范化：

```json
{
  "version": "1.0",
  "ai": {
    "provider": "deepseek",
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com",
    "api_key_env": "DEEPSEEK_API_KEY",
    "temperature": 0.2,
    "max_tokens": 4096,
    "throttle_sec": 0,
    "languages": ["zh"],
    "analysis_concurrency": 3,
    "enrichment_concurrency": 2
  },
  "sources": {
    "github": [],
    "hackernews": {
      "enabled": false,
      "fetch_top_stories": 20,
      "min_score": 100,
      "category": "design-inspiration"
    },
    "rss": [
      {
        "name": "Global Basketball Jersey Design",
        "url": "https://news.google.com/rss/search?q=%22basketball+jersey%22+(design+OR+unveil+OR+%22City+Edition%22+OR+throwback)&hl=en-US&gl=US&ceid=US:en",
        "enabled": true,
        "category": "design-inspiration"
      },
      {
        "name": "Basketball Uniform Media",
        "url": "https://news.google.com/rss/search?q=(site%3Abasketballjerseyarchive.com+OR+site%3Auni-watch.com+OR+site%3Anews.sportslogos.net+OR+site%3Auniswag.com)+basketball&hl=en-US&gl=US&ceid=US:en",
        "enabled": true,
        "category": "design-inspiration"
      },
      {
        "name": "中文篮球球衣设计",
        "url": "https://news.google.com/rss/search?q=篮球球衣+(设计+OR+配色+OR+字体+OR+号码+OR+复古)&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "enabled": true,
        "category": "design-inspiration"
      },
      {
        "name": "篮球服采购商机",
        "url": "https://news.google.com/rss/search?q=(篮球服定制+OR+篮球队服采购+OR+比赛服招标)&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "enabled": true,
        "category": "market-opportunity"
      },
      {
        "name": "校园篮球商机",
        "url": "https://news.google.com/rss/search?q=(校园篮球赛+OR+班级篮球赛+OR+大学生篮球赛事)&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "enabled": true,
        "category": "market-opportunity"
      },
      {
        "name": "企业篮球商机",
        "url": "https://news.google.com/rss/search?q=(企业篮球赛+OR+员工运动会+OR+企业团建篮球)&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "enabled": true,
        "category": "market-opportunity"
      },
      {
        "name": "俱乐部赛事商机",
        "url": "https://news.google.com/rss/search?q=(业余篮球联赛+OR+篮球俱乐部+OR+篮球训练营+OR+赛事承办)&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "enabled": true,
        "category": "market-opportunity"
      },
      {
        "name": "篮球服材料工艺",
        "url": "https://news.google.com/rss/search?q=(篮球服面料+OR+吸湿速干+OR+透气网眼+OR+环保纤维)&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "enabled": true,
        "category": "supply-chain"
      },
      {
        "name": "运动服供应链",
        "url": "https://news.google.com/rss/search?q=(热升华+OR+数码印花+OR+刺绣+OR+小单快反)+运动服&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "enabled": true,
        "category": "supply-chain"
      }
    ],
    "reddit": {
      "enabled": true,
      "subreddits": [
        {
          "subreddit": "UniWatch",
          "enabled": true,
          "sort": "hot",
          "time_filter": "day",
          "fetch_limit": 15,
          "min_score": 5,
          "category": "design-inspiration"
        },
        {
          "subreddit": "basketballjerseys",
          "enabled": true,
          "sort": "hot",
          "time_filter": "day",
          "fetch_limit": 15,
          "min_score": 5,
          "category": "design-inspiration"
        }
      ],
      "users": [],
      "fetch_comments": 5
    },
    "telegram": {
      "enabled": false,
      "channels": []
    },
    "twitter": {
      "enabled": "${TWITTER_ENABLED}",
      "mode": "apify",
      "users": [
        "NBA",
        "nikebasketball",
        "Jumpman23",
        "adidasHoops",
        "UniWatch",
        "sportslogosnet",
        "SLAMonline"
      ],
      "fetch_limit": 100,
      "category": "design-inspiration",
      "fetch_reply_text": false,
      "max_replies_per_tweet": 0,
      "max_tweets_to_expand": 0,
      "reply_min_likes": 0,
      "lookback_hours": 72,
      "apify_token_env": "APIFY_TOKEN",
      "actor_id": "altimis~scweet"
    },
    "openbb": {
      "enabled": false,
      "watchlists": []
    },
    "ossinsight": {
      "enabled": false,
      "period": "past_24_hours",
      "languages": ["All"],
      "keywords": [],
      "min_stars": 10,
      "max_items": 30,
      "category": "design-inspiration"
    },
    "gdelt": {
      "enabled": true,
      "query": "(\"basketball jersey\" OR \"basketball uniform\") AND (design OR unveil OR branding)",
      "mode": "ArtList",
      "max_records": 25,
      "timespan": "24h",
      "language": "english",
      "country": null,
      "category": "design-inspiration"
    },
    "google_news": {
      "enabled": false,
      "query": "basketball jersey",
      "language": "zh",
      "country": "CN",
      "ceid": "CN:zh-Hans",
      "max_results": 20,
      "category": "design-inspiration"
    }
  },
  "filtering": {
    "ai_score_threshold": 6.5,
    "time_window_hours": 24,
    "max_items": 20,
    "category_groups": {
      "design": {
        "name": "设计灵感",
        "limit": 12,
        "categories": ["design-inspiration"]
      },
      "market": {
        "name": "市场商机",
        "limit": 6,
        "categories": ["market-opportunity"]
      },
      "supply": {
        "name": "工艺供应链",
        "limit": 2,
        "categories": ["supply-chain"]
      }
    },
    "default_group": "unclassified",
    "default_group_limit": 1
  }
}
```

- [ ] **Step 4: 运行配置测试**

```powershell
uv run pytest tests/test_jersey_config.py tests/test_storage.py tests/test_category_wiring.py -v
```

预期：全部通过。

- [ ] **Step 5: 提交**

```powershell
git add data/config.github.json tests/test_jersey_config.py
git commit -m "feat: configure basketball jersey intelligence sources"
```

---

### Task 3: 类别感知的篮球球衣专业评分

**Files:**
- Modify: `src/ai/prompts.py`
- Modify: `src/ai/analyzer.py`
- Modify: `tests/test_analyzer.py`

**Interfaces:**
- Consumes: `ContentItem.metadata["category"]`。
- Produces: `CONTENT_ANALYSIS_USER` 的 `{category}` 输入，以及 `metadata["analysis_failed"]: bool`。

- [ ] **Step 1: 写失败测试**

在 `tests/test_analyzer.py` 追加：

```python
import asyncio
from datetime import datetime, timezone

from src.ai.analyzer import ContentAnalyzer
from src.ai.prompts import CONTENT_ANALYSIS_SYSTEM
from src.models import ContentItem, SourceType


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


def test_analysis_prompt_is_not_tech_news_prompt():
    assert "篮球球衣套装定制创业者" in CONTENT_ANALYSIS_SYSTEM
    assert "设计灵感" in CONTENT_ANALYSIS_SYSTEM
    assert "市场商机" in CONTENT_ANALYSIS_SYSTEM
    assert "工艺供应链" in CONTENT_ANALYSIS_SYSTEM
    assert "relevance to software engineering" not in CONTENT_ANALYSIS_SYSTEM
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
uv run pytest tests/test_analyzer.py -v
```

预期：缺少 `{category}`、专业提示词和 `analysis_failed` 标记而失败。

- [ ] **Step 3: 替换评分提示词**

在 `src/ai/prompts.py` 中把 `CONTENT_ANALYSIS_SYSTEM` 和 `CONTENT_ANALYSIS_USER` 替换为：

```python
CONTENT_ANALYSIS_SYSTEM = """你是一名为中国篮球球衣套装定制创业者服务的设计与商业情报策展人。

客户覆盖校园球队与班级定制、业余篮球队/俱乐部/赛事、企业团建与员工比赛。
根据内容所属类别按 0-10 分评分：

1. design-inspiration（设计灵感）
- 高分：有辨识度的配色、版型、字体、号码、纹样、视觉层级或文化叙事；
  能抽象为原创方法；包含可信发布信息、设计师说明或有价值讨论。
- 低分：普通晒单、假货鉴定、纯商品广告、无设计分析的推广、只能照搬的品牌资产。

2. market-opportunity（市场商机）
- 高分：出现采购、招标、赛事周期、组织者、赞助、报名、校园/俱乐部/企业客户信号；
  能转化为客户触达、营销内容、产品组合或区域行动。
- 低分：只有比分、转会、球员八卦，或没有定制业务价值的普通篮球新闻。

3. supply-chain（工艺供应链）
- 高分：涉及面料性能、热升华、数码印花、刺绣、裁剪缝制、打样、小单快反，
  并说明成本、起订量、交期、质量或差异化影响。
- 低分：缺少技术细节的批发广告。

通用标准：
- 9-10：高度原创、及时且可立即形成产品或商业行动。
- 7-8：明显有价值，值得进入今日情报。
- 5-6：相关但常规、信息不完整或行动价值有限。
- 3-4：低价值、重复、泛化或过度推广。
- 0-2：无关、垃圾、抄袭导向或事实不可信。

不得鼓励复制球队标识、品牌图形或他人原创作品。社区讨论具体且有洞察时可以加分。
"""

CONTENT_ANALYSIS_USER = """分析以下内容并只返回有效 JSON：
- score: 0-10
- reason: 一句中文评分理由
- summary: 一句中文摘要
- tags: 3-5 个中文标签

Category: {category}
Title: {title}
Source: {source}
Author: {author}
URL: {url}
{content_section}
{discussion_section}

返回：
{{"score": 0, "reason": "", "summary": "", "tags": ["", "", ""]}}
"""
```

- [ ] **Step 4: 把类别传给提示词并记录健康状态**

在 `src/ai/analyzer.py` 的 `CONTENT_ANALYSIS_USER.format(...)` 中加入：

```python
category=item.metadata.get("category", "unclassified"),
```

解析失败分支加入：

```python
item.metadata["analysis_failed"] = True
```

成功写入结果之前加入：

```python
item.metadata["analysis_failed"] = False
```

`analyze_batch()` 捕获异常的分支同时加入：

```python
item.metadata["analysis_failed"] = True
```

- [ ] **Step 5: 运行评分相关测试**

```powershell
uv run pytest tests/test_analyzer.py tests/test_chained_client.py -v
```

预期：全部通过。

- [ ] **Step 6: 提交**

```powershell
git add src/ai/prompts.py src/ai/analyzer.py tests/test_analyzer.py
git commit -m "feat: score content for basketball jersey business"
```

---

### Task 4: 中文业务 enrichment 元数据

**Files:**
- Modify: `src/ai/prompts.py`
- Modify: `src/ai/enricher.py`
- Create: `tests/test_enricher.py`

**Interfaces:**
- Consumes: 评分后的 `ContentItem` 和 `metadata.category`。
- Produces: `title_zh`、`detailed_summary_zh`、`design_breakdown_zh`、`business_value_zh`、`recommended_action_zh`、`ip_risk_zh`。

- [ ] **Step 1: 写 enrichment 失败测试**

创建 `tests/test_enricher.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
uv run pytest tests/test_enricher.py -v
```

预期：enricher 尚未存储四个专业字段而失败。

- [ ] **Step 3: 写中文专业 enrichment 提示词**

在 `src/ai/prompts.py` 中保留去重提示词，替换 concept/enrichment 提示词为中文业务版本。`CONTENT_ENRICHMENT_USER` 必须包含类别：

```python
CONCEPT_EXTRACTION_SYSTEM = """识别篮球球衣设计、市场商机或运动服工艺中需要补充背景的专有概念。
只返回内容明确提到、且解释后能帮助中国篮球服定制创业者判断价值的 0-3 个检索词。"""

CONCEPT_EXTRACTION_USER = """标题：{title}
摘要：{summary}
标签：{tags}
内容：{content}
只返回有效 JSON：{{"queries": ["", ""]}}"""

CONTENT_ENRICHMENT_SYSTEM = """你是一名中国篮球球衣设计与定制业务分析师。
只使用内容本身和给定检索结果，不得编造。所有文本字段必须使用简体中文。
设计类要拆解配色、版型、字体、号码、纹样、视觉层级和文化叙事；
商机类要说明客户、时机、地点、需求信号和跟进行动；
供应链类要说明材料/工艺、质量、成本、起订量、交期和打样建议。
对球队标识、品牌图形和他人独特作品明确提示知识产权风险。
sources 只能使用检索结果中原样出现的 URL。"""

CONTENT_ENRICHMENT_USER = """类别：{category}
标题：{title}
链接：{url}
摘要：{summary}
评分：{score}/10
理由：{reason}
标签：{tags}

正文：
{content}
{comments_section}

检索结果：
{web_context}

只返回有效 JSON：
{{
  "title_zh": "",
  "whats_new_zh": "",
  "design_breakdown_zh": "",
  "business_value_zh": "",
  "recommended_action_zh": "",
  "ip_risk_zh": "",
  "background_zh": "",
  "community_discussion_zh": "",
  "sources": []
}}"""
```

- [ ] **Step 4: 传入类别并存储专业字段**

在 `src/ai/enricher.py` 调用 `CONTENT_ENRICHMENT_USER.format(...)` 时加入：

```python
category=item.metadata.get("category", "unclassified"),
```

用以下逻辑替换双语字段合并循环：

```python
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
```

保留现有 `sources` URL 白名单校验和 `_translate_item()` 降级逻辑。

- [ ] **Step 5: 运行 enrichment 测试**

```powershell
uv run pytest tests/test_enricher.py tests/test_analyzer.py -v
```

预期：全部通过。

- [ ] **Step 6: 提交**

```powershell
git add src/ai/prompts.py src/ai/enricher.py tests/test_enricher.py
git commit -m "feat: enrich jersey intelligence in Chinese"
```

---

### Task 5: 三段式中文日报、趋势和行动建议

**Files:**
- Modify: `src/ai/summarizer.py`
- Modify: `tests/test_summarizer.py`

**Interfaces:**
- Consumes: 分类后的 `ContentItem` 及 Task 4 专业元数据。
- Produces: `generate_summary(..., source_warnings: list[str] | None = None) -> str`。

- [ ] **Step 1: 写分组日报失败测试**

在 `tests/test_summarizer.py` 追加：

```python
def _business_item(idx, category, tag, action):
    item = _make_item(idx)
    item.metadata.update(
        {
            "category": category,
            "title_zh": f"中文标题 {idx}",
            "detailed_summary_zh": f"中文摘要 {idx}",
            "design_breakdown_zh": "配色与号码形成清楚层级。",
            "business_value_zh": "适合目标客户场景。",
            "recommended_action_zh": action,
            "ip_risk_zh": "不要复制注册标识。",
        }
    )
    item.ai_tags = [tag]
    return item


def test_generate_summary_zh_groups_business_sections_and_actions():
    summarizer = DailySummarizer()
    items = [
        _business_item(
            1, "design-inspiration", "城市文化", "制作本地文化纹样草案。"
        ),
        _business_item(
            2, "market-opportunity", "校园篮球", "建立校园赛事触达清单。"
        ),
        _business_item(
            3, "supply-chain", "热升华", "向供应商申请耐洗测试样。"
        ),
    ]

    result = _run_async(
        summarizer.generate_summary(
            items,
            date="2026-07-26",
            total_fetched=40,
            language="zh",
            source_warnings=["Twitter 本次抓取失败，其他来源正常。"],
        )
    )

    assert "## 今日趋势" in result
    assert "## 今日行动建议" in result
    assert "## 设计灵感（1）" in result
    assert "## 市场商机（1）" in result
    assert "## 工艺供应链（1）" in result
    assert "制作本地文化纹样草案" in result
    assert "**设计拆解**" in result
    assert "**原创/IP 提醒**" in result
    assert "Twitter 本次抓取失败" in result
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
uv run pytest tests/test_summarizer.py -v
```

预期：当前 summarizer 不分组且不接受 `source_warnings`，测试失败。

- [ ] **Step 3: 增加类别定义与趋势/行动 helper**

在 `src/ai/summarizer.py` 顶部增加：

```python
from collections import Counter
from typing import List, Dict, Optional

CATEGORY_SECTIONS = (
    ("design-inspiration", "设计灵感"),
    ("market-opportunity", "市场商机"),
    ("supply-chain", "工艺供应链"),
)
```

在 `DailySummarizer` 中增加：

```python
def _render_trends(self, items: List[ContentItem]) -> str:
    counter = Counter(tag for item in items for tag in item.ai_tags)
    lines = ["## 今日趋势", ""]
    for tag, count in counter.most_common(5):
        representative = next(item for item in items if tag in item.ai_tags)
        title = representative.metadata.get("title_zh") or representative.title
        lines.append(f"- **{tag}**（{count} 条）：[{title}]({representative.url})")
    if len(lines) == 2:
        lines.append("- 今日入选内容尚未形成重复趋势标签。")
    return "\n".join(lines) + "\n\n"

def _render_actions(self, items: List[ContentItem]) -> str:
    ranked = sorted(items, key=lambda item: item.ai_score or 0, reverse=True)
    actions = [
        item.metadata["recommended_action_zh"]
        for item in ranked
        if item.metadata.get("recommended_action_zh")
    ][:3]
    lines = ["## 今日行动建议", ""]
    lines.extend(f"{index}. {action}" for index, action in enumerate(actions, 1))
    if not actions:
        lines.append("1. 今日暂无足够明确的立即行动建议。")
    return "\n".join(lines) + "\n\n"
```

- [ ] **Step 4: 增加中文分组路径并原样保留现有英文路径**

在现有 `generate_summary()` 签名末尾增加：

```python
source_warnings: Optional[List[str]] = None,
```

在现有空列表返回语句之后、原有非空渲染逻辑之前插入：

```python
if language == "zh":
    return self._generate_business_summary(
        items,
        date,
        total_fetched,
        labels,
        source_warnings or [],
    )
```

现有英文非空渲染代码不移动、不改名。然后在 `DailySummarizer` 中新增以下方法：

```python
def _generate_business_summary(
    self,
    items: List[ContentItem],
    date: str,
    total_fetched: int,
    labels: Dict[str, str],
    source_warnings: List[str],
) -> str:
    counts = Counter(
        str(item.metadata.get("category", "unclassified")) for item in items
    )
    parts = [
        f"# 篮球球衣商业情报 - {date}\n\n",
        f"> 从 {total_fetched} 条内容中筛选出 {len(items)} 条高价值情报；"
        f"设计 {counts['design-inspiration']} 条、"
        f"商机 {counts['market-opportunity']} 条、"
        f"供应链 {counts['supply-chain']} 条。\n\n",
    ]
    if source_warnings:
        parts.append("### 来源提示\n\n")
        parts.extend(f"- {warning}\n" for warning in source_warnings)
        parts.append("\n")
    parts.append(self._render_trends(items))
    parts.append(self._render_actions(items))
    for category, label in CATEGORY_SECTIONS:
        section_items = [
            item for item in items if item.metadata.get("category") == category
        ]
        parts.append(f"## {label}（{len(section_items)}）\n\n")
        if not section_items:
            parts.append("今日暂无达到阈值的内容。\n\n")
            continue
        for index, item in enumerate(section_items, 1):
            parts.append(self._format_item(item, labels, "zh", index))
    return "".join(parts)
```

- [ ] **Step 5: 在条目中渲染业务字段**

在 `_format_item()` 的来源行后、背景前加入：

```python
business_fields = (
    ("design_breakdown_zh", "设计拆解"),
    ("business_value_zh", "业务价值"),
    ("recommended_action_zh", "建议行动"),
    ("ip_risk_zh", "原创/IP 提醒"),
)
if language == "zh":
    for key, label in business_fields:
        value = meta.get(key)
        if value:
            lines.extend(["", f"**{label}**：{_pangu(str(value))}"])
```

- [ ] **Step 6: 运行摘要回归测试**

```powershell
uv run pytest tests/test_summarizer.py -v
```

预期：新测试与原有中英文/Webhook 测试全部通过。

- [ ] **Step 7: 提交**

```powershell
git add src/ai/summarizer.py tests/test_summarizer.py
git commit -m "feat: render grouped jersey business briefings"
```

---

### Task 6: Twitter 72 小时独立回看

**Files:**
- Modify: `src/models.py`
- Modify: `src/scrapers/twitter.py`
- Modify: `tests/test_twitter.py`

**Interfaces:**
- Consumes: `TwitterConfig.lookback_hours`，默认 24。
- Produces: `TwitterScraper._effective_since(since, now=None) -> datetime`。

- [ ] **Step 1: 写回看窗口失败测试**

在 `tests/test_twitter.py` 追加：

```python
import pytest
from datetime import datetime, timedelta, timezone

from src.models import TwitterConfig
from src.scrapers.twitter import TwitterScraper


def test_twitter_effective_since_extends_only_twitter_window():
    config = TwitterConfig(
        enabled=True,
        mode="apify",
        users=["NBA"],
        fetch_limit=100,
        category="design-inspiration",
        lookback_hours=72,
    )
    scraper = TwitterScraper(config, None)
    now = datetime(2026, 7, 27, 0, 0, tzinfo=timezone.utc)
    pipeline_since = now - timedelta(hours=24)

    effective = scraper._effective_since(pipeline_since, now=now)

    assert effective == now - timedelta(hours=72)


def test_twitter_lookback_is_bounded():
    with pytest.raises(ValueError):
        TwitterConfig(
            enabled=True,
            users=["NBA"],
            lookback_hours=169,
        )
```

`_effective_since()` 是不访问网络的纯时间计算；该单元测试明确传入 `None`，不依赖文件中已有 HTTP 假对象。

- [ ] **Step 2: 运行测试确认失败**

```powershell
uv run pytest tests/test_twitter.py -k "lookback or effective_since" -v
```

预期：`lookback_hours` 和 `_effective_since` 尚不存在。

- [ ] **Step 3: 增加模型字段**

在 `src/models.py` 的 `TwitterConfig` 中加入：

```python
lookback_hours: int = Field(default=24, ge=1, le=168)
```

- [ ] **Step 4: 实现独立窗口**

在 `src/scrapers/twitter.py` 导入 `timedelta`，并增加：

```python
def _effective_since(
    self,
    since: datetime,
    *,
    now: Optional[datetime] = None,
) -> datetime:
    current = now or datetime.now(timezone.utc)
    lookback_since = current - timedelta(hours=self.config.lookback_hours)
    return min(since, lookback_since)
```

在 `fetch()` 开始处计算：

```python
effective_since = self._effective_since(since)
```

把 `_parse_item(raw, since)` 改为：

```python
parsed = self._parse_item(raw, effective_since)
```

- [ ] **Step 5: 运行 Twitter 与配置测试**

```powershell
uv run pytest tests/test_twitter.py tests/test_jersey_config.py -v
```

预期：全部通过。

- [ ] **Step 6: 提交**

```powershell
git add src/models.py src/scrapers/twitter.py tests/test_twitter.py
git commit -m "feat: add independent Twitter lookback window"
```

---

### Task 7: 发布前验证与秘密落盘扫描

**Files:**
- Create: `src/services/publication_validator.py`
- Create: `scripts/check_runtime_secrets.py`
- Modify: `src/orchestrator.py`
- Create: `tests/test_publication_validator.py`
- Create: `tests/test_secret_scan.py`
- Modify: `tests/test_fetch_reporting.py`

**Interfaces:**
- Produces: `PublicationValidationError`、`validate_analysis_health()`、`validate_selected_items()`、`validate_markdown()`、`scan_tree_for_values()`。
- Consumes: 已分析/已补充的 `ContentItem`、Markdown 和运行时 Secret 值。

- [ ] **Step 1: 写 validator 失败测试**

创建 `tests/test_publication_validator.py`：

```python
from datetime import datetime, timezone

import pytest

from src.models import ContentItem, SourceType
from src.services.publication_validator import (
    PublicationValidationError,
    validate_analysis_health,
    validate_markdown,
    validate_selected_items,
)


def _item(category="design-inspiration", index=1):
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


def test_rejects_all_failed_analysis():
    items = [_item()]
    items[0].metadata["analysis_failed"] = True
    with pytest.raises(PublicationValidationError, match="AI analysis failed"):
        validate_analysis_health(items)


def test_rejects_unclassified_selected_item():
    with pytest.raises(PublicationValidationError, match="unclassified"):
        validate_selected_items([_item("unclassified")])


def test_rejects_category_over_limit():
    items = [_item("supply-chain", index) for index in range(3)]
    with pytest.raises(PublicationValidationError, match="supply-chain"):
        validate_selected_items(items)


def test_rejects_secret_or_unresolved_env_in_markdown():
    with pytest.raises(PublicationValidationError, match="secret"):
        validate_markdown("report contains runtime-secret", ["runtime-secret"])
    with pytest.raises(PublicationValidationError, match="environment"):
        validate_markdown("report contains ${MISSING_VALUE}", [])


def test_rejects_markdown_without_grouped_sections_or_source_link():
    sections_only = (
        "## 设计灵感（1）\n"
        "## 市场商机（0）\n"
        "## 工艺供应链（0）\n"
    )
    with pytest.raises(PublicationValidationError, match="category section"):
        validate_markdown("# 篮球球衣商业情报", [])
    with pytest.raises(PublicationValidationError, match="source link"):
        validate_markdown(sections_only, [])
```

- [ ] **Step 2: 写秘密扫描失败测试**

创建 `tests/test_secret_scan.py`：

```python
from pathlib import Path

from scripts.check_runtime_secrets import scan_tree_for_values


def test_secret_scan_reports_path_without_echoing_value(tmp_path):
    secret = "runtime-secret-value"
    (tmp_path / "safe.txt").write_text("public", encoding="utf-8")
    leaked = tmp_path / "leaked.txt"
    leaked.write_text(secret, encoding="utf-8")

    findings = scan_tree_for_values(tmp_path, [secret])

    assert findings == [Path("leaked.txt")]
    assert secret not in repr(findings)
```

- [ ] **Step 3: 运行测试确认失败**

```powershell
uv run pytest tests/test_publication_validator.py tests/test_secret_scan.py -v
```

预期：两个新模块尚不存在。

- [ ] **Step 4: 实现发布验证器**

创建 `src/services/publication_validator.py`：

```python
import re
from collections import Counter
from typing import Iterable
from urllib.parse import urlparse

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


class PublicationValidationError(RuntimeError):
    pass


def validate_analysis_health(items: list[ContentItem]) -> None:
    if not items:
        raise PublicationValidationError("No content was available for AI analysis")
    if all(item.metadata.get("analysis_failed") is True for item in items):
        raise PublicationValidationError("AI analysis failed for every content item")


def validate_selected_items(items: list[ContentItem]) -> None:
    if not items:
        raise PublicationValidationError("No content passed the publication threshold")
    counts = Counter(str(item.metadata.get("category", "unclassified")) for item in items)
    for category, count in counts.items():
        if category not in LIMITS:
            raise PublicationValidationError(
                f"Selected item has unsupported category: {category}"
            )
        if count > LIMITS[category]:
            raise PublicationValidationError(
                f"Category {category} exceeds limit {LIMITS[category]}"
            )
    if len(items) > 20:
        raise PublicationValidationError("Selected item count exceeds limit 20")
    for item in items:
        parsed = urlparse(str(item.url))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise PublicationValidationError("Selected item has invalid URL")
        if not str(item.metadata.get("title_zh", "")).strip():
            raise PublicationValidationError("Selected item has no Chinese title")


def validate_markdown(markdown: str, secret_values: Iterable[str]) -> None:
    if not markdown.strip():
        raise PublicationValidationError("Generated Markdown is empty")
    if _UNRESOLVED_ENV.search(markdown):
        raise PublicationValidationError(
            "Generated Markdown contains unresolved environment reference"
        )
    for secret in secret_values:
        if secret and secret in markdown:
            raise PublicationValidationError(
                "Generated Markdown contains a runtime secret"
            )
    for pattern in _REQUIRED_SECTION_PATTERNS:
        if re.search(pattern, markdown, flags=re.MULTILINE) is None:
            raise PublicationValidationError(
                "Generated Markdown is missing a required category section"
            )
    if _SOURCE_LINK.search(markdown) is None:
        raise PublicationValidationError(
            "Generated Markdown contains no source link"
        )
```

- [ ] **Step 5: 实现工作树秘密扫描**

创建 `scripts/check_runtime_secrets.py`：

```python
import os
from pathlib import Path


EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache"}


def scan_tree_for_values(root: Path, values: list[str]) -> list[Path]:
    findings: list[Path] = []
    active_values = [value.encode() for value in values if value]
    if not active_values:
        return findings
    for path in root.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if any(value in data for value in active_values):
            findings.append(path.relative_to(root))
    return sorted(findings)


def main() -> int:
    values = [
        os.getenv("DEEPSEEK_API_KEY", ""),
        os.getenv("APIFY_TOKEN", ""),
    ]
    findings = scan_tree_for_values(Path.cwd(), values)
    if findings:
        print("Runtime secret value found in tracked workspace files:")
        for path in findings:
            print(f"- {path}")
        return 1
    print("Runtime secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: 接入 orchestrator**

在 `src/orchestrator.py` 导入 `os`、`ZoneInfo` 和验证函数：

```python
import os
from zoneinfo import ZoneInfo

from .services.publication_validator import (
    validate_analysis_health,
    validate_markdown,
    validate_selected_items,
)
```

AI 分析后立即加入：

```python
validate_analysis_health(analyzed_items)
```

enrichment 完成后加入：

```python
validate_selected_items(important_items)
```

用北京时间生成日期：

```python
today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
```

在 `src/orchestrator.py` 的数据类定义之后增加非敏感提示 helper：

```python
def build_source_warnings(report: Optional[FetchReport]) -> List[str]:
    if report is None:
        return []
    warnings = [
        f"{outcome.source_name} 本次抓取失败，其他来源继续运行。"
        for outcome in report.outcomes
        if outcome.status == "failure"
    ]
    if any(
        outcome.source_name == "Twitter" and outcome.status == "empty"
        for outcome in report.outcomes
    ):
        warnings.append("Twitter 本次未抓取到新内容，其他来源继续运行。")
    return warnings
```

在生成摘要之前调用：

```python
source_warnings = build_source_warnings(self.last_fetch_report)
```

调用 summarizer 时传入：

```python
summary = await summarizer.generate_summary(
    important_items,
    today,
    len(all_items),
    language=lang,
    source_warnings=source_warnings,
)
validate_markdown(
    summary,
    [
        os.getenv("DEEPSEEK_API_KEY", ""),
        os.getenv("APIFY_TOKEN", ""),
    ],
)
```

验证必须发生在 `save_daily_summary()` 和写入 `docs/_posts` 之前。

- [ ] **Step 7: 测试 Twitter 失败/空结果只形成公开安全提示**

在 `tests/test_fetch_reporting.py` 追加：

```python
from src.orchestrator import (
    FetchReport,
    SourceFetchOutcome,
    build_source_warnings,
)


def test_twitter_failure_and_empty_results_are_non_sensitive_warnings():
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
```

- [ ] **Step 8: 运行验证和回归测试**

```powershell
uv run pytest tests/test_publication_validator.py tests/test_secret_scan.py tests/test_fetch_reporting.py tests/test_summarizer.py -v
```

预期：全部通过。

- [ ] **Step 9: 提交**

```powershell
git add src/services/publication_validator.py scripts/check_runtime_secrets.py src/orchestrator.py tests/test_publication_validator.py tests/test_secret_scan.py tests/test_fetch_reporting.py
git commit -m "feat: validate reports before publication"
```

---

### Task 8: GitHub Actions、中文站点与部署测试

**Files:**
- Modify: `.github/workflows/daily-summary.yml`
- Modify: `docs/_config.yml`
- Modify: `docs/index.md`
- Create: `tests/test_deployment_files.py`

**Interfaces:**
- Consumes: `DEEPSEEK_API_KEY`、`APIFY_TOKEN`、`TWITTER_ENABLED`、Task 2 配置。
- Produces: 每日 08:00 工作流、手动 `force_twitter` 验收入口和中文 Pages。

- [ ] **Step 1: 写部署文件失败测试**

创建 `tests/test_deployment_files.py`：

```python
from pathlib import Path


def test_daily_workflow_has_beijing_schedule_and_secrets():
    workflow = Path(".github/workflows/daily-summary.yml").read_text(
        encoding="utf-8"
    )
    assert "cron: '0 0 * * *'" in workflow
    assert "force_twitter:" in workflow
    assert "TZ=Asia/Shanghai date +%u" in workflow
    assert '"$weekday" == "1"' in workflow
    assert '"$weekday" == "3"' in workflow
    assert '"$weekday" == "5"' in workflow
    assert "TWITTER_ENABLED=true" in workflow
    assert "TWITTER_ENABLED=false" in workflow
    assert "DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}" in workflow
    assert "APIFY_TOKEN: ${{ secrets.APIFY_TOKEN }}" in workflow
    assert "python scripts/check_runtime_secrets.py" in workflow


def test_pages_branding_is_chinese_jersey_intelligence():
    config = Path("docs/_config.yml").read_text(encoding="utf-8")
    index = Path("docs/index.md").read_text(encoding="utf-8")
    assert "title: Horizon 篮球球衣商业情报" in config
    assert 'baseurl: "/Horizon"' in config
    assert "# Horizon 篮球球衣商业情报" in index
    assert "设计灵感 60%" in index
    assert "市场商机 30%" in index
    assert "工艺供应链 10%" in index
    assert "Daily Digest" not in index
```

- [ ] **Step 2: 运行测试确认失败**

```powershell
uv run pytest tests/test_deployment_files.py -v
```

预期：旧 cron、旧站点标题和缺少 Twitter 星期逻辑导致失败。

- [ ] **Step 3: 修改 daily workflow**

保留上游 Actions 版本和 Pages deploy step，把触发器、星期判断及运行环境改为：

```yaml
name: Daily Horizon Jersey Intelligence

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

jobs:
  daily-summary:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          version: "0.11.26"

      - name: Install dependencies
        run: uv sync

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

      - name: Prepare production config
        run: cp data/config.github.json data/config.json

      - name: Run Horizon
        env:
          TZ: Asia/Shanghai
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          APIFY_TOKEN: ${{ secrets.APIFY_TOKEN }}
        run: uv run horizon --hours 24

      - name: Check that runtime secrets were not written
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          APIFY_TOKEN: ${{ secrets.APIFY_TOKEN }}
        run: uv run python scripts/check_runtime_secrets.py

      - name: Set current date
        run: echo "DATE=$(TZ=Asia/Shanghai date +'%Y-%m-%d')" >> "$GITHUB_ENV"

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs
          keep_files: true
          commit_message: "Daily jersey intelligence: ${{ env.DATE }}"
          publish_branch: gh-pages
          enable_jekyll: true
```

- [ ] **Step 4: 修改 Jekyll 配置**

将 `docs/_config.yml` 改为：

```yaml
theme: jekyll-theme-cayman
title: Horizon 篮球球衣商业情报
description: 每日篮球球衣设计、市场商机与工艺供应链情报
baseurl: "/Horizon"
url: ""
markdown: kramdown
future: true
plugins:
  - jekyll-feed
feed:
  path: feed.xml
exclude:
  - ".github"
  - "node_modules"
defaults:
  - scope:
      path: ""
      type: "posts"
    values:
      layout: "default"
```

- [ ] **Step 5: 修改中文首页**

将 `docs/index.md` 改为：

```markdown
---
layout: default
title: 首页
---

# Horizon 篮球球衣商业情报

面向篮球球衣套装定制创业者的每日中文信息雷达。

- 设计灵感 60%
- 市场商机 30%
- 工艺供应链 10%
- 每天北京时间 08:00 左右更新

## 每日情报

{% assign zh_posts = site.posts | where: "lang", "zh" %}
{% for post in zh_posts limit:30 %}
- [{{ post.date | date: "%Y-%m-%d" }}]({{ post.url | relative_url }})
{% else %}
- 首次日报生成后将在这里显示。
{% endfor %}
```

- [ ] **Step 6: 运行部署文件测试**

```powershell
uv run pytest tests/test_deployment_files.py -v
```

预期：全部通过。

- [ ] **Step 7: 提交**

```powershell
git add .github/workflows/daily-summary.yml docs/_config.yml docs/index.md tests/test_deployment_files.py
git commit -m "feat: schedule and publish Chinese jersey briefings"
```

---

### Task 9: 全量验证、凭证接入和首次上线

**Files:**
- Verify only: all changed files
- Generated at runtime: `data/config.json`
- Generated at runtime: `data/summaries/horizon-YYYY-MM-DD-zh.md`
- Generated at runtime: `docs/_posts/YYYY-MM-DD-summary-zh.md`

**Interfaces:**
- Consumes: 用户 GitHub 登录、DeepSeek API Key、Apify Token。
- Produces: 通过的功能分支、首次真实日报、公开 GitHub Pages URL。

- [ ] **Step 1: 运行聚焦测试**

```powershell
uv run pytest tests/test_jersey_config.py tests/test_analyzer.py tests/test_enricher.py tests/test_summarizer.py tests/test_twitter.py tests/test_publication_validator.py tests/test_secret_scan.py tests/test_deployment_files.py -v
```

预期：全部通过。

- [ ] **Step 2: 运行完整测试和配置解析**

```powershell
uv run pytest -q
$env:TWITTER_ENABLED='false'
Copy-Item -LiteralPath 'data\config.github.json' -Destination 'data\config.json' -Force
uv run python -c "from src.storage.manager import StorageManager; c=StorageManager('data').load_config(); print(c.ai.provider.value, c.ai.model, c.ai.languages, c.filtering.max_items)"
```

预期输出包含：

```text
deepseek deepseek-v4-flash ['zh'] 20
```

- [ ] **Step 3: 查看最终差异和提交状态**

```powershell
git diff --check
git status --short
git log --oneline --decorate -10
```

预期：`git diff --check` 无输出；只有预期文件发生变化；每个前置任务均有独立提交。

- [ ] **Step 4: 请求代码审查**

使用 `requesting-code-review` 检查设计覆盖、测试、Secret 安全、Actions 表达式、DeepSeek 模型与 Apify 成本保护。修复审查发现后重新运行完整测试。

- [ ] **Step 5: 推送功能分支**

```powershell
git push -u origin feat/basketball-jersey-intelligence
```

预期：远端出现同名分支。

- [ ] **Step 6: 引导用户创建 DeepSeek Key**

在用户已登录的浏览器中打开 DeepSeek API 控制台，由用户完成实名认证/充值要求并创建 API Key。用户复制 Key 后直接进入 GitHub，不在聊天中发送。

- [ ] **Step 7: 引导用户创建 Apify Token**

在 Apify 创建免费账号，进入 Integrations，复制 API Token。确认账户显示免费计划和每月可用额度；Token 不在聊天中发送。

- [ ] **Step 8: 在 GitHub 添加 Secrets**

打开用户 fork：

```text
Settings → Secrets and variables → Actions → New repository secret
```

依次添加：

```text
DEEPSEEK_API_KEY
APIFY_TOKEN
```

只确认名称存在，不读取或回显 Secret 值。

- [ ] **Step 9: 合并分支并手动验收**

合并到 `main` 后，在 Actions 中运行 `Daily Horizon Jersey Intelligence`，首次把 `force_twitter` 设为 `true`。使用 Actions 日志验证：

```text
- production config loaded
- DeepSeek model is deepseek-v4-flash
- Twitter source attempted once
- selected total <= 20
- design <= 12
- market <= 6
- supply <= 2
- runtime secret scan passed
- gh-pages deployment succeeded
```

- [ ] **Step 10: 检查真实日报质量**

打开生成的中文日报，逐项确认：

```text
- 三个分类标题存在
- 中文标题和来源链接可用
- 设计条目含设计拆解和原创/IP 提醒
- 商机条目含客户/时机/行动建议
- 供应链条目含材料或工艺价值
- 今日趋势含 3-5 个信号或明确的无趋势说明
- 今日行动建议不超过 3 条
- 页面不含任何 Secret 或未展开环境变量
```

- [ ] **Step 11: 启用 Pages 和定时运行**

在 GitHub 仓库 Settings → Pages 中选择：

```text
Deploy from a branch
Branch: gh-pages
Folder: / (root)
```

确认公开 Pages 可访问，并保留 cron `0 0 * * *`。记录首次成功的 Actions run URL、Pages URL 和当日三类实际数量。

- [ ] **Step 12: 完成交付验证**

再次运行：

```powershell
git status --short --branch
uv run pytest -q
```

预期：工作树干净、所有测试通过。随后使用 `verification-before-completion`，只有在测试、Actions 和 Pages 都有成功证据时才宣告完成。
