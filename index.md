---
layout: default
title: Horizon 篮球球衣商业情报
---

# Horizon 篮球球衣商业情报

聚焦篮球球衣的设计趋势、市场机会与工艺供应信息，为品牌、设计师与供应链团队提供每日决策参考。

> 每天北京时间 08:00 左右更新

## 情报配比

- **设计灵感 60%**：追踪配色、图案、版型与文化叙事趋势
- **市场商机 30%**：发现联名、赛事、收藏与消费需求机会
- **工艺供应链 10%**：关注面料、印绣、生产技术与供应动态

## 每日简报

<ul>
  {% assign zh_posts = site.posts | where: "lang", "zh" %}
  {% for post in zh_posts limit:20 %}
    <li>
      <a href="{{ post.url | relative_url }}">{{ post.date | date: "%Y-%m-%d" }}</a>
    </li>
  {% else %}
    <li><em>首份每日简报正在生成中，请稍后再来查看。</em></li>
  {% endfor %}
</ul>
