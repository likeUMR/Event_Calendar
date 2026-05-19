# Event Calendar Collector

这个项目用于整理竞品活动相关信息，目前包含两条能力线：

1. 活动日历采集：抓取结构化活动时间、轨道和文章信息，输出统一 JSON，并在时间轴看板中展示。
2. 活动信息看板：面向市场调研和策划分析，整理不同游戏的活动类型、研究备注、来源页和图片参考，形成横向可比的活动机制看板。

## 当前内容

- `monopolygo-wiki` 活动日历采集链路
- 多游戏活动信息研究数据
- 活动信息人工整理数据
- 两套前端页面：
  - `可视化数据/index.html`：活动日历看板
  - `可视化数据/manual.html`：活动信息看板

## 目录结构

```text
Event_Calendar/
├─ 数据/
│  ├─ monopolygo/
│  │  ├─ monopolygo_wiki_raw.json
│  │  └─ monopolygo_wiki_events.json
│  ├─ 活动信息/                 # 自动采集产物
│  ├─ 活动信息_人工/            # 人工整理产物
│  ├─ 活动信息_index.json
│  ├─ game_event_info_sources.json
│  ├─ image_clean_log.jsonl
│  └─ image_supplement_debug.jsonl
├─ 获取数据/
│  ├─ collect.py
│  ├─ collect_event_info.js
│  ├─ clean_activity_images.py
│  ├─ filter_manual_activity_images.py
│  ├─ supplement_manual_images.py
│  ├─ repair_manual_texts.py
│  └─ monopolygo_wiki/
│     ├─ raw.py
│     ├─ processor.py
│     └─ collector.py
├─ 可视化数据/
│  ├─ index.html
│  ├─ app.js
│  ├─ manual.html
│  ├─ manual-app.js
│  └─ styles.css
├─ index.html
├─ requirements.txt
└─ README.md
```

## 活动信息看板思路

### 1. 前期调研结论

前期调研发现，活动有关信息主要出现在以下渠道：

- Reddit
- Facebook
- Discord
- 各游戏专属 wiki / forum

进一步调研后有几个比较稳定的结论：

- Facebook 反爬很强，账号还触发过重新认证。并且一个游戏通常会分散在多个 group 中，活跃度一般，少数活跃内容也大多偏向换卡、社交，不一定是活动信息。
- Discord 里很多游戏根本没有公开可用群组；即便有群组，活动相关信息密度通常也比较低。
- Reddit 往往有更集中的单游戏社区，例如 `r/游戏名`。虽然大部分帖子依旧和活动无关，但某些 subreddit 会有特殊 tag，可以明显提升信息密度。例如 `Royal Aid (Q&A)` 这种 tag 可以作为筛选入口。不过这并不稳定，不是每个游戏都有高相关 tag，也有些游戏的 Reddit 社区缺失或已经不活跃。
- 专有 wiki / forum 的建设程度差异极大，很多游戏根本没有稳定维护的资料站。

### 2. 核心问题

- Problem A：每个游戏的有效信息渠道参差不齐。
- Problem B：即使进入了有效渠道，渠道内部的信息含量通常也很低。

### 3. 解决 Problem A：先找信源，再整理活动类型

第一阶段先解决“去哪里看”的问题，做法是：

- 使用 AI 配合搜索引擎搜索每个游戏的活动相关公开信息源
- 再由 AI 对这些信息源进行整理和归纳

这样做的原因：

- 比逐个游戏人工找来源快很多
- 能快速形成每个游戏的信源列表和初步活动类型概览

但也有明确限制：

- AI 搜索基于非登录态，拿不到必须登录后才能查看的内容，例如 Discord、Facebook
- AI 总结不一定完全精准，可能会把某些玩法大类误当成活动
- 对于活动定义本来就不清晰、或公开信源极度缺失的游戏，AI 也可能会“强行总结”

这一阶段的主要产出是：每个游戏的各种活动类型和对应公开信息源。

### 4. 解决 Problem B：用 Google Image 提升信息密度

第二阶段继续用搜索引擎，但重点转向 Google Image 搜索活动类型相关结果。

这样做有几个优势：

- 图片结果天然是高信息密度结果，至少会带有关键词
- 会同时覆盖多种信源，相当于复用 Google 已有的索引数据库和排序能力
- 带图内容通常比纯文字更高质量，对策划也更直观

这一步也不是完全无噪声：

- 仍然会混入少量无关图片
- 因此需要后续结合 AI 做图片筛选和清洗

这一阶段的主要产出是：活动类型对应的高信息密度图片参考。

### 5. 可视化展示

最终将整理后的活动机制、研究备注、来源页和图片参考可视化到活动信息看板中，便于：

- 横向比较不同游戏的活动设计
- 快速浏览某类活动在多个游戏中的实现方式
- 给策划提供更直观的视觉参考

## 活动信息数据流

活动信息看板目前大致分为 4 步：

1. 在 `数据/game_event_info_sources.json` 中维护每个游戏的候选公开来源。
2. 使用 `获取数据/collect_event_info.js` 拉取公开页面，抽取活动相关文本、候选详情页和图片。
3. 结合人工整理结果沉淀到 `数据/活动信息_人工/`，并通过图片清洗脚本过滤无关图、重复图和难加载图片。
4. 前端 `可视化数据/manual.html` 读取 `活动信息_index.json`、`活动信息/` 与 `活动信息_人工/` 数据进行展示。

## 安装依赖

Python 依赖：

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

活动信息自动采集脚本 `获取数据/collect_event_info.js` 使用 Node.js 运行，仅依赖 Node 内置模块。

## 活动日历采集

运行 `monopolygo-wiki` 采集：

```powershell
python 获取数据\collect.py monopolygo-wiki --pages 1
```

默认流程会先检查 `数据/monopolygo/monopolygo_wiki_raw.json`。

- 如果 raw 已存在，会优先复用 raw，再重新生成 processed
- 只有 raw 不存在，或传入 `--refresh-raw` 时才会重新下载网页

常用参数：

- `--pages`：扫描列表页数量，默认 `1`
- `--source-url`：起始列表页，默认 `https://monopolygo.wiki/page/2/`
- `--max-posts`：最多解析多少篇详情文章
- `--raw-output`：原始数据缓存路径
- `--processed-output`：处理后数据输出路径
- `--delay`：详情页请求间隔秒数，默认 `0.5`
- `--refresh-raw`：强制重抓 raw
- `--process-only`：只使用已有 raw 重新生成 processed

仅重建处理后数据：

```powershell
python 获取数据\collect.py monopolygo-wiki --process-only
```

## 活动信息采集与整理

按 rank 范围运行活动信息自动采集：

```powershell
node 获取数据\collect_event_info.js 1 10
```

脚本会：

- 读取 `数据/game_event_info_sources.json`
- 抓取公开来源页
- 抽取活动相关文本块、候选详情页和图片
- 生成 `数据/活动信息/*.json`

图片清洗脚本示例：

```powershell
python 获取数据\clean_activity_images.py --write
```

如果需要检查远端图片是否可加载：

```powershell
python 获取数据\clean_activity_images.py --write --check-remote
```

如果需要按前端真实 `<img>` 嵌入方式校验：

```powershell
python 获取数据\clean_activity_images.py --write --check-embed
```

## 查看前端看板

从项目根目录启动本地静态服务：

```powershell
python -m http.server 8000
```

然后打开：

```text
http://localhost:8000/可视化数据/index.html
http://localhost:8000/可视化数据/manual.html
```

说明：

- `index.html` 是活动日历看板
- `manual.html` 是活动信息看板
- 不要直接双击本地 HTML 文件打开，否则浏览器可能因为本地文件安全限制无法读取 JSON

## 活动日历 JSON 说明

活动日历输出 JSON 包含顶层元信息和统一事件数组，核心字段包括：

- `lifecycles`：生命周期分组
- `tracks`：活动轨道定义
- `articles`：来源文章与专题内容
- `events`：标准化活动事件

时间统一输出为 UTC ISO 格式，同时保留原始展示文本，前端只读取已经整理好的 `lifecycles`、`tracks` 和事件轨道字段进行展示，不在前端重新推断分类。

## 备注

- 仓库中既有自动采集结果，也有人工整理结果；活动信息看板默认优先读取人工整理数据。
- 活动信息研究是开放网页视角下的近似整理，不等价于游戏内完整活动配置。
- 对于必须登录、强反爬、社区沉寂或公开资料极少的游戏，数据覆盖度会明显受限。
