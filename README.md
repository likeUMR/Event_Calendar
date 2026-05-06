# Event Calendar Collector

这个项目用于采集竞品活动日历。每个竞品使用独立模块实现采集逻辑，最终输出统一结构的 JSON，便于后续合并、入库或展示。

## 文件结构

```text
Event_Calendar/
├── 数据/
│   ├── monopolygo/       # Monopoly GO 按游戏归档的数据
│   │   ├── monopolygo_wiki_raw.json    # 原始抓取缓存，包含列表页和文章 HTML
│   │   └── monopolygo_wiki_events.json # 处理后的统一 JSON 数据
├── 获取数据/             # 采集入口和各竞品采集规则
│   ├── collect.py        # 命令行采集入口
│   └── monopolygo_wiki/  # monopolygo.wiki 的独立采集模块
│       ├── raw.py        # 只负责下载和缓存原始页面
│       ├── processor.py  # 只负责把 raw 转为活动、文章和轨道
│       └── collector.py  # 解析与轨道规则
└── 可视化数据/           # 前端日历看板
    ├── index.html
    ├── styles.css
    └── app.js
```

新增竞品时，在 `获取数据/` 下新建一个竞品目录，并在其中实现自己的采集规则；入口脚本负责把不同竞品模块的输出写成统一 JSON。

## 当前支持

- `monopolygo-wiki`：从 <https://monopolygo.wiki/page/2/> 发现站点文章，解析每日活动、专题活动说明和 Album 贴纸信息。

## 安装依赖

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 运行采集

```powershell
python 获取数据\collect.py monopolygo-wiki --pages 1
```

默认流程会先检查 `数据/monopolygo/monopolygo_wiki_raw.json`。如果文件存在，会复用这份 raw 缓存并直接重新生成处理后数据；只有 raw 不存在或传入 `--refresh-raw` 时才会重新下载网页。

常用参数：

- `--pages`：扫描列表页数量，默认 `1`。
- `--source-url`：起始列表页，默认 `https://monopolygo.wiki/page/2/`。
- `--max-posts`：最多解析多少篇详情文章，默认不限制。
- `--raw-output`：原始数据缓存路径，默认 `数据/monopolygo/monopolygo_wiki_raw.json`。
- `--processed-output`：处理后数据输出路径，默认 `数据/monopolygo/monopolygo_wiki_events.json`。
- `--delay`：详情页请求间隔秒数，默认 `0.5`。
- `--refresh-raw`：强制重新下载 raw，再生成 processed。
- `--process-only`：只使用已有 raw 重新生成 processed；raw 不存在时会报错。

只重建处理后数据：

```powershell
python 获取数据\collect.py monopolygo-wiki --process-only
```

## 查看前端看板

看板参考 AppMagic 的 Live Ops Calendar 思路，以横向日期时间轴展示活动开放区间，并提供搜索、分类筛选、日期范围筛选、统计卡片和活动详情弹窗。

时间轴只读取处理后 JSON 中的 `lifecycles`、`tracks` 和活动轨道字段，不在前端重新做分类推断。

线上版本通过 GitHub Pages 发布；仓库只提交 `数据/monopolygo/monopolygo_wiki_events.json` 这类处理后 JSON，不提交 `*_raw.json` 原始抓取缓存。

从项目根目录启动本地静态服务：

```powershell
python -m http.server 8000
```

然后在浏览器打开：

```text
http://localhost:8000/可视化数据/
```

不要直接双击打开 `index.html`，浏览器可能会因为本地文件安全限制阻止读取 `数据/monopolygo/monopolygo_wiki_events.json`。

## JSON 格式

输出文件包含顶层元信息和统一事件数组：

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-05-06T08:00:00+00:00",
  "competitor": "monopoly_go",
  "source": "monopolygo.wiki",
  "listing_source_url": "https://monopolygo.wiki/page/2/",
  "supplemental_source_urls": ["https://monopolygo.wiki/tag/albums/"],
  "lifecycles": [
    { "id": "one_time", "label": "一次性", "sort": 10 },
    { "id": "recurring", "label": "周期性", "sort": 20 },
    { "id": "irregular", "label": "不定期", "sort": 30 },
    { "id": "seasonal", "label": "赛季性", "sort": 40 }
  ],
  "tracks": [
    {
      "id": "buff",
      "label": "buff",
      "group": "buff",
      "group_label": "buff",
      "lifecycle": "recurring",
      "lifecycle_label": "周期性",
      "lifecycle_sort": 20,
      "index": 1,
      "sort": 2001,
      "event_count": 657
    }
  ],
  "articles": [
    {
      "id": "monopoly_go:article:star-wars-go-album",
      "type": "album",
      "url": "https://monopolygo.wiki/star-wars-go-album/",
      "title": "Star Wars GO! Album",
      "published_date": "2025-06-01",
      "summary": "Want to view the stickers up close...",
      "sections": [],
      "album": {
        "name": "Star Wars GO! Album",
        "set_count": 26,
        "sticker_count": 234,
        "gold_sticker_count": 34,
        "sets": []
      }
    }
  ],
  "events": [
    {
      "id": "monopoly_go:cash-boost:1778050800:1778072340",
      "competitor": "monopoly_go",
      "source": "monopolygo.wiki",
      "source_url": "https://monopolygo.wiki/todays-events-may-06-2026/",
      "category": "Special Events",
      "name": "Cash Boost",
      "start_time": "2026-05-06T03:00:00+00:00",
      "end_time": "2026-05-06T08:59:00+00:00",
      "timezone": "UTC",
      "start_timestamp": 1778050800,
      "end_timestamp": 1778072340,
      "duration_seconds": 21540,
      "duration_text": "00:10:00",
      "track_group": "buff",
      "track_group_label": "buff",
      "track": "buff",
      "track_label": "buff",
      "track_index": 1,
      "track_sort": 2001,
      "lifecycle": "recurring",
      "lifecycle_label": "周期性",
      "lifecycle_sort": 20,
      "description": "Tournaments are limited-time competitive events...",
      "article_summary": "Tournaments are limited-time competitive events...",
      "related_article": {
        "type": "daily_events",
        "title": "Today's Events (May 06, 2026)",
        "url": "https://monopolygo.wiki/todays-events-may-06-2026/",
        "published_date": "2026-05-06"
      },
      "detail_url": "https://monopolygo.wiki/wiki/event/05062026-2-se-cashboost",
      "image_url": "https://cdn.monopolygo.wiki/commodities/CashBoost.png",
      "raw": {
        "display_start": "03:00 AM",
        "display_end": "08:59AM",
        "classes": ["event-block", "event-container"]
      }
    }
  ]
}
```

站点页面里的时间以 `data-date` Unix 时间戳为准，程序统一输出 UTC ISO 时间，同时保留页面原始展示文本。

轨道规则：

- `一次性活动`：Trade Fest、Lucky Coin 等一次性/阶段性特殊活动。
- `buff`：短时增益活动，例如 Rent Frenzy、Cash Boost、High Roller、Lucky Chance、Golden Blitz；只要某个名称曾以短于 12 小时的 buff 出现，同名活动后续即使时长超过 12 小时也归入 buff。
- `album`：Album 周期，例如 Monopoly Ever After。
- `Tycoon-class`：单独拆出的 Tycoon Class 锦标赛轨道。
- `其它 tournaments`：除 Tycoon Class 外的锦标赛。
- `minigames`：长时 special event、Partner Events、Dig Minigame 等非 buff 玩法。

归并规则：

- 如果 daily events 里出现泛称 `Partner Event`，且同一开始/结束时间存在具体 `Partner Events` 专题活动，则删除泛称事件，保留专题来源，并重命名为 `Partner Event（具体活动名）`，例如 `Partner Event（Pet Show Partners）`。
- 如果 daily events 里出现泛称 `Dig Minigame`，且同一开始/结束时间存在具体 `Dig Minigame` 专题活动，则删除泛称事件，保留专题来源，并重命名为 `Dig Minigame（具体活动名）`。

同一轨道内按时间排序且不允许重叠；如果发生重叠，会自动拆出 `buff2`、`minigames2`、`其它 tournaments2` 等后续轨道。

生命周期规则：

- `一次性`：一次性活动轨道。
- `周期性`：buff、Tycoon-class、其它 tournaments。
- `不定期`：minigames。
- `赛季性`：album。

前端只读取 JSON 中已处理好的 `lifecycles`、`tracks` 和事件轨道字段，展示时按生命周期分区、按轨道逐行显示。
