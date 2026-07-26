# Horizon 篮球球衣商业情报系统设计

日期：2026-07-26  
状态：已由用户确认

## 1. 目标

基于开源项目 [Thysrael/Horizon](https://github.com/Thysrael/Horizon) 建立一个面向中国篮球球衣套装定制创业者的公开信息雷达。系统每天自动收集、筛选和整理原创篮球球衣设计、市场商机及工艺供应链信息，在北京时间 08:00 左右发布一份中文 GitHub Pages 日报。

系统服务以下三类客户场景：

1. 校园球队与班级定制。
2. 业余篮球队、俱乐部与赛事。
3. 企业团建与员工比赛。

中国市场经营信息优先，同时保留 NBA、WNBA、品牌、海外制服媒体及社区中的设计趋势。

## 2. 成功标准

- GitHub Actions 无需本地电脑开机即可每日运行。
- 每天最多精选 20 条高价值信息，以 12 条设计灵感、6 条市场商机、2 条工艺供应链为目标上限。
- 只发布简体中文日报，并按日期长期归档。
- 普通来源每天采集；X/Twitter 在每周一、三、五采集，并回看最近 72 小时。
- 报告从篮球球衣创业者视角解释每条信息的设计价值、商业价值或工艺价值。
- 系统明确区分“借鉴设计方法”和“复制他人作品”，对球队标识、品牌图形和原创作品给出知识产权风险提示。
- DeepSeek、Apify 或信息源发生异常时按本设计降级，不发布明显无效或泄露秘密的内容。
- `DEEPSEEK_API_KEY` 与 `APIFY_TOKEN` 只保存在 GitHub Secrets 中，不进入仓库、日志或网页。

## 3. 部署架构

### 3.1 仓库与运行环境

- 在用户 GitHub 账号下建立一个公开的 Horizon 专业版仓库。
- 保留原仓库为 `upstream`，使后续可以拉取 Horizon 更新。
- 使用仓库自带的 Python 3.12、`uv` 和 GitHub Actions 工作流，不在当前 Windows 电脑安装运行环境。
- 使用 GitHub Pages 的 `gh-pages` 分支公开发布日报。
- 电子邮件、Webhook、飞书、本地运行和 MCP 第一版均不启用。

### 3.2 定时

- 工作流使用 `0 0 * * *`，即北京时间 08:00；接受 GitHub Actions 调度可能出现的少量延迟。
- 工作流显式使用 `Asia/Shanghai` 判断星期，避免按 UTC 错判。
- 周一、三、五设置 `TWITTER_ENABLED=true`，其余日期设置为 `false`。
- `data/config.github.json` 通过 `${TWITTER_ENABLED}` 环境变量控制 Twitter 来源。

### 3.3 凭证

| GitHub Secret | 用途 | 必需性 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek V4 Flash 评分、去重、补充分析和中文摘要 | 必需 |
| `APIFY_TOKEN` | 周一、三、五通过 Apify 抓取 X/Twitter | 必需 |
| `GITHUB_TOKEN` | Actions 自动提供，用于发布 GitHub Pages | 自动提供 |

用户不在聊天、配置文件或提交中发送完整密钥。密钥由用户直接粘贴到 GitHub 仓库的 Actions Secrets 页面。

## 4. AI 配置与专业评分

### 4.1 模型

Horizon AI 配置使用：

```json
{
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "api_key_env": "DEEPSEEK_API_KEY",
  "temperature": 0.2,
  "max_tokens": 4096,
  "throttle_sec": 0,
  "analysis_concurrency": 3,
  "enrichment_concurrency": 2,
  "languages": ["zh"]
}
```

不得使用 Horizon 当前默认的 `deepseek-chat`；该旧名称已于 2026-07-24 停止使用。基础地址沿用 Horizon 内置的 `https://api.deepseek.com`。

### 4.2 评分角色

原版 Horizon 的评分角色偏向软件工程、AI 和学术资讯，不适合篮球球衣。本专业版把角色替换为：

> 为中国篮球球衣套装定制创业者服务的设计与商业情报策展人。

分析提示词必须把 `item.metadata.category` 传给模型，并按类别使用不同判断标准。

### 4.3 设计灵感评分

高分内容应至少满足一项：

- 展示有辨识度的配色系统、版型、字体、号码、纹样或视觉层级。
- 把城市、学校、社区、历史或球队文化转化为清楚的视觉叙事。
- 体现值得学习的新趋势、复古回潮、联名方法或跨品类灵感。
- 含有可验证的发布信息、设计师说明或高质量社区讨论。
- 能抽象成原创设计方法，而不是只能照搬现成图形。

降低以下内容的分数：

- 单纯商品广告、假货鉴定、晒单或无设计分析的推广。
- 只涉及比赛比分、球员转会或普通篮球新闻。
- 缺乏来源、明显抄袭或只能通过复制球队/品牌知识产权使用的设计。

### 4.4 市场商机评分

重点判断：

- 是否出现校园、业余俱乐部、赛事或企业团建场景。
- 是否包含采购、招标、赛事周期、合作单位、赞助、报名或组织者信号。
- 是否能转化为内容营销、客户触达、产品组合或区域市场行动。
- 商机的时效性、规模、客户匹配度和可执行性。

### 4.5 工艺供应链评分

重点判断：

- 是否改进吸湿速干、透气、耐磨、轻量、舒适度或环保表现。
- 是否涉及热升华、数码印花、刺绣、裁剪、缝制、打样和小单快反。
- 是否对成本、起订量、交期、质量稳定性或差异化有实际影响。
- 是否提供技术细节，而非普通批发广告。

### 4.6 阈值与去重

- `ai_score_threshold` 固定为 `6.5`。
- 在评分后执行 URL 去重和 AI 主题去重。
- 不使用低质量内容填满日报；当天不足 20 条时允许发布更短的报告。

## 5. 信息源

所有启用来源必须明确设置为以下三个类别之一：

- `design-inspiration`
- `market-opportunity`
- `supply-chain`

### 5.1 设计灵感

#### 专业媒体与搜索 RSS

通过 Google News RSS 查询专业站点和主题，避免依赖站点是否提供稳定的原生 Feed：

- Basketball Jersey Archive
- Uni Watch
- SportsLogos.Net
- UNISWAG
- 中文：篮球球衣设计、篮球队服配色、球衣字体、号码设计、城市版球衣、复古球衣。
- 英文：`basketball jersey design`、`basketball uniform unveil`、`City Edition`、`throwback jersey`。

#### Reddit

- `r/UniWatch`
- `r/basketballjerseys`

每个社区每次最多读取 15 条，优先 `hot`，读取最多 5 条高价值评论。第一版不启用泛化且高噪声的 `r/nba`。

#### X/Twitter

- `NBA`
- `nikebasketball`
- `Jumpman23`
- `adidasHoops`
- `UniWatch`
- `sportslogosnet`
- `SLAMonline`

通过 Apify `altimis/scweet` 的 profile 模式统一抓取，`fetch_limit` 为 100，`fetch_reply_text=false`，避免为回复额外启动 Actor。

Twitter 配置增加 `lookback_hours: 72`。Twitter 抓取器使用该字段计算独立回看窗口，不改变 RSS、Reddit 和其他来源的每日 24 小时窗口。

### 5.2 市场商机

Google News RSS 使用多条中文查询，分别覆盖：

- 篮球服定制、篮球队服采购、比赛服招标。
- 校园篮球赛、班级篮球赛、大学生篮球赛事。
- 企业篮球赛、员工运动会、企业团建篮球。
- 业余篮球联赛、篮球俱乐部、训练营、赛事承办。

同义词采用 `OR` 组合，并保留原始来源链接。纯比赛结果、球员新闻和没有定制价值的内容在 AI 评分阶段被过滤。

### 5.3 工艺供应链

Google News RSS 查询：

- 篮球服面料、运动服装面料、吸湿速干、透气网眼。
- 热升华、数码印花、刺绣、环保纤维。
- 运动服装供应链、打样、交期、小单快反。

第一版不启用 OpenBB、Hacker News、GitHub、OSS Insight、Telegram 和内置泛科技预设。

### 5.4 全球补充

启用一个 GDELT 全球查询，围绕 `basketball jersey`、`basketball uniform`、`design`、`unveil` 和 `branding` 组合，最多取 25 条并归类为 `design-inspiration`。

## 6. 分类配额

```json
{
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
```

发布验证不允许出现 `unclassified` 入选项，因此正常日报仍严格受 12/6/2 三组上限控制。配额是上限和目标，不是低质量内容填充要求。

## 7. 数据流

1. GitHub Actions 设置北京时间、Twitter 星期开关和两个 Secret 环境变量。
2. Horizon 并行抓取每日 RSS、Reddit、GDELT，以及周一、三、五的 X/Twitter。
3. 统一转换为 `ContentItem`，保留来源类别。
4. 按规范化 URL 合并重复来源。
5. DeepSeek 使用篮球球衣专业提示词评分并生成原因、中文摘要和标签。
6. 只保留分数不低于 6.5 的内容。
7. AI 合并报道同一事件的重复条目。
8. 按 12/6/2 类别上限筛选，最多 20 条。
9. 对入选条目进行补充检索和中文业务分析。
10. 生成分组 Markdown，执行发布前验证。
11. 验证通过后写入 `docs/_posts` 并发布至 `gh-pages`。

## 8. 日报结构

### 8.1 首页与概览

- 标题、日期、抓取总数和入选总数。
- 设计灵感、市场商机和工艺供应链的实际数量。
- 从入选内容归纳 3–5 个趋势信号。
- 从最高价值条目提炼 1–3 个“今日行动建议”。

### 8.2 设计灵感条目

每条展示：

- 中文标题、原始链接、来源、时间和评分。
- 设计拆解：配色、版型、字体、号码、图案、视觉层级或文化叙事。
- 可借鉴方法：可以转化为自有原创方案的抽象方法。
- 原创/IP 提醒：不得直接复制的球队标识、品牌资产或独特作品元素。
- 相关背景和社区观点。

### 8.3 市场商机条目

每条展示：

- 客户类型、地点、时间窗口和需求信号。
- 为什么与篮球服套装定制相关。
- 建议的跟进、内容营销、产品组合或合作动作。
- 来源与事实依据。

### 8.4 工艺供应链条目

每条展示：

- 材料或工艺说明。
- 质量、成本、交期、起订量和适用场景影响。
- 是否值得询价或打样的建议。
- 风险、限制和来源。

### 8.5 实现方式

扩充 AI enrichment 的 JSON 结果，保存以下中文元数据：

- `design_breakdown_zh`
- `business_value_zh`
- `recommended_action_zh`
- `ip_risk_zh`

专业版 enrichment 提示词只请求中文业务字段，不再为第一版生成未使用的英文分析，以减少 Token 消耗。`DailySummarizer` 按类别分组渲染，并从分数最高且包含 `recommended_action_zh` 的条目中选择最多三条作为“今日行动建议”。“趋势信号”由入选条目的标签频次、类别和高分代表标题确定，展示 3–5 个带代表链接的趋势，不增加第三次 AI 调用。

## 9. 异常处理

### 9.1 DeepSeek

- SDK 请求沿用最多三次指数退避重试。
- API Key 无效、余额不足、模型不可用或所有评分均失败时，工作流失败。
- 工作流失败时不发布新的 Pages 内容，保留上一份有效日报。
- 单条 enrichment 失败时允许退化为中文标题与简短摘要，但必须保留原始链接。

### 9.2 Apify 与 X/Twitter

- 缺少 `APIFY_TOKEN`、Actor 超时、额度耗尽或 X 返回空结果时，记录清晰警告并跳过 Twitter。
- Twitter 失败不阻止 RSS、Reddit、GDELT 和日报发布。
- 日报概览标注 X 来源本次未成功，避免用户误以为已经覆盖。

### 9.3 信息源

- 单个 RSS、Reddit 或 GDELT 来源失败时继续运行。
- 所有来源均失败时工作流失败，不发布空白日报。
- 来源无新内容不视为失败。

### 9.4 发布前验证

发布前必须满足：

- 至少有一条入选内容。
- 所有入选内容具有允许的类别、有效 HTTP(S) 链接和非空中文标题。
- 三个类别均不超过 12/6/2 上限，总数不超过 20。
- 输出文件不含 Secret 值、典型密钥前缀或 `${UNRESOLVED_VAR}`。
- Markdown 和 Jekyll front matter 能正常解析。

任何发布验证失败都会使工作流失败，并阻止部署不完整日报。

## 10. 测试与验证

### 10.1 自动测试

- 配置解析：DeepSeek V4 Flash、中文单语言、类别、环境变量和配额。
- 专业评分提示词：高质量球衣设计、三类客户商机和工艺内容得到合理高分；泛科技新闻、比分、转会、垃圾广告和复制内容得到低分。
- 类别传递：RSS、Reddit、GDELT 和 Twitter 均保留正确类别。
- 平衡筛选：严格执行 12/6/2 和总数 20。
- Twitter 调度：按北京时间仅在周一、三、五启用，独立使用 72 小时回看。
- Twitter 成本保护：不抓回复，单次 `max_items` 保持 100。
- 摘要渲染：三段分组、趋势概览、行动建议和原创/IP 提醒正常显示。
- 异常降级：Twitter 失败继续发布；DeepSeek 全面失败或空日报不发布。
- Secret 扫描：测试夹具和生成文件均不含真实密钥。

### 10.2 首次真实验收

1. 用户在 DeepSeek 与 Apify 创建凭证。
2. 用户在 GitHub Secrets 中录入两个值。
3. 手动触发 Actions。
4. 检查抓取、AI 评分、分类数量、中文日报和 Pages 部署。
5. 在周一、三或五验证 X 来源；若首次验收不在这些日期，可通过手动测试参数临时启用一次，测试后恢复自动星期逻辑。
6. 查看 Actions 日志确认没有密钥或 Token。
7. 启用定时工作流与 GitHub Pages。

## 11. 成本控制

- DeepSeek 使用价格较低的 `deepseek-v4-flash`，只对入选内容执行较昂贵的 enrichment。
- X/Twitter 每周运行三次，每次只启动一次 profile Actor，不抓回复。
- Apify 免费套餐目前含每月 5 美元额度；若 Actor 定价变化或额度不足，系统允许跳过 X 而不中断日报。
- 每次运行在 Actions 日志中输出 Token 数量，但不输出密钥。

## 12. 第一版范围外

- 飞书、邮件、Slack、Discord 和自定义 Webhook。
- Instagram、小红书、Pinterest、Behance 的直接抓取。
- X/Twitter Cookie 抓取。
- 本地 Windows、Docker 或服务器部署。
- 自动联系潜在客户、自动发送营销信息或自动下单。
- 图片下载、图片相似度分析和生成新球衣图片。
- 面向多个行业的通用 `business_profile` 配置系统。

## 13. 用户需要完成的动作

实施阶段只需要用户参与以下账号步骤：

1. 确认用于公开仓库的 GitHub 账号并完成必要登录。
2. 创建 DeepSeek API Key，确保账户有可用余额。
3. 创建 Apify 免费账号并复制 API Token。
4. 在 GitHub Secrets 页面直接录入两个 Secret。
5. 在 GitHub 设置中启用 Actions 和 Pages。

其余代码、配置、工作流、测试和首次运行检查由 Codex 完成或逐步引导。
