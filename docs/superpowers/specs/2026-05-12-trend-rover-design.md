# Trend Rover - Design Spec

## Overview

GitHub 开源项目，帮助公司市场部门对品牌进行热度趋势监测。通过爬虫方式在 YouTube、X 等社交媒体进行实时搜索，统计指定时间段内包含关键词的 feed 数量、查看次数和互动数据。

**目标：** 1000+ GitHub Stars

## Tech Stack

- **语言：** Python
- **爬虫：** Playwright（主）+ httpx（降级）
- **CLI：** argparse
- **Dashboard：** Gradio
- **存储：** SQLite
- **图像识别：** OpenCV（默认）/ 多模态 LLM（可选）
- **分发：** pip install + Claude Code Skill

## 项目结构

```
trend-rover/
├── trend_rover/
│   ├── __init__.py
│   ├── cli.py              # argparse 入口
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py         # BaseScraper 抽象基类
│   │   ├── youtube.py
│   │   └── x.py
│   ├── vision/
│   │   ├── __init__.py
│   │   ├── base.py         # BaseDetector 抽象基类
│   │   ├── opencv.py       # 默认 OpenCV 模板匹配
│   │   └── llm.py          # 多模态 LLM 方案
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py           # SQLite 操作
│   │   └── export.py       # CSV 导出
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── app.py          # Gradio UI
│   └── skill/
│       └── trend-rover.md  # Claude Code Skill 定义
├── pyproject.toml
├── README.md
└── tests/
```

## 数据模型

```python
@dataclass
class Feed:
    platform: str          # "youtube" | "x"
    feed_id: str           # 平台原始 ID
    keyword: str           # 搜索关键词
    title: str
    url: str
    author: str
    published_at: datetime
    views: int
    likes: int
    comments: int
    shares: int            # 转发/repost
    bookmarks: int         # 收藏
    thumbnail_url: str     # 封面图 URL（YouTube）
    logo_matched: bool     # 封面是否匹配 logo
    scraped_at: datetime   # 抓取时间
```

## 抽象基类

```python
class BaseScraper(ABC):
    @abstractmethod
    def search(self, keyword: str, start_date: date, end_date: date, **filters) -> list[Feed]:
        """按关键词和时间范围搜索"""

    @abstractmethod
    def get_stats(self, feed_id: str) -> Feed:
        """获取单条 feed 的最新互动数据"""

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, thumbnail_path: str, logo_path: str) -> tuple[bool, float]:
        """返回 (是否匹配, 置信度分数)"""
```

## 爬虫策略

### YouTube

- **搜索：** Playwright 加载搜索页面（`youtube.com/results?search_query=xxx`），解析视频列表
- **内部 API 降级：** 直接调用 `youtubei/v1/search` 端点获取 JSON 数据
- **封面获取：** 从结果中提取缩略图 URL，httpx 下载
- **搜索过滤：**
  - 类型：视频（Video）、短视频（Shorts）、直播（Live）
  - 时长：短于 4 分钟（Short）、4-20 分钟（Medium）、长于 20 分钟（Long）
  - 时间范围：一小时内、今天、本周、本月、今年、自定义 start/end date
  - 排序方式：相关性（默认）、上传日期、观看次数、评分
- **实现：** 通过 YouTube 搜索 URL 的 `sp=` 参数编码

### X (Twitter)

- **搜索：** Playwright 加载搜索页面，模拟滚动加载
- **数据提取：** 解析推文的点赞、转发、回复、书签、浏览量
- **登录处理：** 支持用户配置 cookies（从浏览器导出）
- **时间过滤：** 使用搜索的 `since:` 和 `until:` 操作符

### 通用策略

- 请求间隔：随机延迟 2-5 秒
- 重试机制：失败自动重试 3 次，指数退避
- User-Agent 轮换：维护一组常见浏览器 UA
- 结果去重：按 `platform + feed_id` 去重

## 搜索入库判定规则

一个 feed 满足以下流程判定后入库：

```
搜索关键词 → 获取结果列表 → 逐条判断：
  ├── 文本匹配关键词？ → 是 → 入库（logo_matched=false）
  └── 文本不匹配 → 提供了 logo？
       ├── 是 → 下载封面 → 检测 logo → 命中 → 入库（logo_matched=true）
       └── 否 → 跳过
```

文本匹配优先，命中直接入库不做 logo 检测。只有文本未命中且用户提供了 logo 时才降级到封面检测。

**文本匹配规则：** 对搜索结果做二次精确匹配——标题或描述中严格包含关键词字符串（不区分大小写）。搜索引擎可能返回语义相关但不含关键词的结果，这些不入库（除非封面 logo 命中）。

## Vision（Logo 检测）

### OpenCV 方案（默认）

- 方法：模板匹配（`cv2.matchTemplate`）
- 多尺度匹配：对模板进行 0.5x ~ 2.0x 缩放逐一匹配
- 匹配度超过阈值（默认 0.8）则判定为包含 logo
- 局限：对旋转、透视变形、半遮挡效果差

### 多模态 LLM 方案（可选）

- 将封面图 + logo 图一起发送给多模态模型
- Prompt：「请判断第一张图片中是否包含第二张图片中的 logo/标志，只回答 yes 或 no」
- 支持 provider：Claude（claude-sonnet-4-6）、OpenAI（gpt-4o）
- 优点：精度高，能处理变形、遮挡、风格化 logo
- 缺点：需要 API Key，有调用成本

## CLI 设计

### 命令

```bash
# 搜索并入库
trend-rover search "keyword" \
  --platform youtube,x \
  --since 2026-04-01 \
  --until 2026-05-12 \
  --type video \
  --duration medium \
  --sort-by views \
  --limit 100 \
  --logo ./brand-logo.png \
  --vision-engine opencv \
  --vision-threshold 0.8

# 统计报告
trend-rover stats "keyword" \
  --platform youtube,x \
  --since 2026-04-01 \
  --until 2026-05-12 \
  --group-by day

# 导出
trend-rover export "keyword" \
  --platform youtube,x \
  --date 20260426 \
  --output ./report.csv

# 启动 Dashboard
trend-rover dashboard --port 7860
```

### 输出格式

- 默认终端表格输出（Rich 库美化）
- `--json` 标志输出 JSON 格式
- `--quiet` 标志仅输出数据

### 配置文件

`~/.trend-rover/config.toml`：

```toml
[scraper]
delay_min = 2
delay_max = 5
max_retries = 3

[scraper.x]
cookies_file = "~/.trend-rover/x_cookies.json"

[vision]
engine = "opencv"
threshold = 0.8

[vision.llm]
provider = "claude"
api_key = "sk-xxx"
model = "claude-sonnet-4-6"
```

## CSV 导出格式

汇总报告式，行列转置格式：

```csv
媒体平台,YouTube,X
日期,20260426,20260426
关键词,IPokekara,IPokekara
视频/帖子数量,20,11
查看次数,10000,2000
互动次数（转发，评论，点赞）,300,100
```

- 每行是一个指标，每列是一个平台
- 单次导出支持一个关键词
- 如果只搜了一个平台则只有一列数据

## Dashboard（Gradio）

### 页面

1. **搜索页** — 关键词输入、平台选择、时间范围、YouTube 过滤条件、Logo 上传、执行搜索
2. **数据统计页** — 趋势折线图、互动柱状图、平台对比、时间粒度切换（日/周/月）
3. **结果明细页** — Feed 列表表格，支持排序筛选，点击跳转原始链接
4. **导出页** — 选择参数、预览汇总、一键导出 CSV

### 启动

```bash
trend-rover dashboard --port 7860
```

## Claude Code Skill

### 封装方式

单一 `/trend-rover` Skill，通过自然语言交互：

- "搜索 YouTube 上过去一周关于 Pokekara 的视频"
- "统计 X 上 5 月份 Pokekara 的互动数据"
- "导出 YouTube 和 X 的汇总报告"

### 执行方式

Skill 内部调用 `trend-rover` CLI 命令。

### 增强能力

- 自然语言解析 → CLI 参数
- 结果解读：趋势分析和洞察
- 交互式追问：参数不完整时主动询问
- 输出格式化：可读的表格/摘要

### 安装

`pip install trend-rover` 后 Skill 文件随包安装，Claude Code 自动发现。

## 插件化扩展

虽然采用单体模块化架构，但通过抽象基类（BaseScraper、BaseDetector）预留扩展点：

- 新增平台：继承 BaseScraper，实现 search/get_stats 方法
- 新增识别引擎：继承 BaseDetector，实现 detect 方法
- 社区贡献者可以通过 PR 添加新平台支持
