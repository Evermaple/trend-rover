<p align="center">
  <h1 align="center">Trend Rover</h1>
  <p align="center">
    跨 YouTube 和 X (Twitter) 追踪品牌关键词热度趋势
    <br />
    <a href="./README.md">English</a> · <a href="#快速开始">快速开始</a> · <a href="#参与贡献">参与贡献</a>
  </p>
</p>

---

**Trend Rover** 实时爬取 YouTube 和 X 平台，采集互动指标（查看次数、点赞、评论、转发、收藏），检测视频封面中的品牌 Logo，并导出汇总报告 —— 一条命令搞定。

专为市场团队打造，回答一个核心问题：*"我们的品牌本周在社交媒体上表现如何？"*

## 功能亮点

- **多平台搜索** — YouTube 和 X，统一关键词 + 日期范围搜索
- **互动追踪** — 查看次数、点赞、评论、转发、收藏，逐条统计
- **Logo 识别** — 通过 OpenCV 或 LLM（Claude / OpenAI）检测 YouTube 封面中的品牌 Logo
- **YouTube 筛选** — 按视频类型（视频 / 短视频 / 直播）、时长、排序方式过滤
- **Gradio 仪表盘** — 4 页签 Web UI：搜索、统计、详情、导出
- **CSV 导出** — 一键生成汇总报告，直接导入 Excel
- **Claude Code 技能** — 在 Claude Code 中使用 `/trend-rover` 进行自然语言查询
- **SQLite 存储** — 本地数据库，自动去重

## 快速开始

### 安装

```bash
# 需要 Python 3.11+
pip install trend-rover
playwright install chromium
```

### 搜索

```bash
# 在 YouTube 和 X 上搜索 "Pokekara"（2026 年 4 月）
trend-rover search "Pokekara" \
  --platform youtube x \
  --since 2026-04-01 \
  --until 2026-04-30

# 仅 YouTube，短视频，按播放量排序
trend-rover search "Pokekara" \
  --platform youtube \
  --since 2026-04-01 \
  --until 2026-04-30 \
  --type shorts \
  --sort-by views
```

### Logo 检测

```bash
# 检测封面中包含品牌 Logo 的视频
trend-rover search "Pokekara" \
  --platform youtube \
  --since 2026-04-01 \
  --until 2026-04-30 \
  --logo ./brand-logo.png \
  --vision-engine opencv
```

### 统计与导出

```bash
# 查看汇总统计
trend-rover stats "Pokekara" \
  --platform youtube x \
  --since 2026-04-01 \
  --until 2026-04-30

# 导出 CSV 报告
trend-rover export "Pokekara" \
  --platform youtube x \
  --date 20260426 \
  --output ./report.csv
```

### 仪表盘

```bash
trend-rover dashboard --port 7860
```

在 `http://localhost:7860` 打开 Gradio Web UI，包含四个页签：

| 页签 | 功能 |
|------|------|
| **搜索** | 按关键词、平台、日期范围、筛选条件和 Logo 搜索 |
| **统计** | 查看汇总互动数据 |
| **详情** | 浏览单条帖子及元数据 |
| **导出** | 下载 CSV 汇总报告 |

### Claude Code

如果你安装了 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)：

```
/trend-rover
> 搜索上个月 YouTube 上的 Pokekara 视频
```

## 项目架构

```
trend_rover/
├── cli.py              # argparse 命令行入口
├── orchestrator.py     # 搜索流水线：爬取 → 检测 → 存储
├── models.py           # Feed 数据模型
├── config.py           # TOML 配置加载
├── scrapers/
│   ├── youtube.py      # Playwright + XHR 拦截
│   ├── x.py            # Playwright + 滚动加载 + Cookie 认证
│   └── _utils.py       # UA 轮换、重试、延迟
├── vision/
│   ├── opencv.py       # 多尺度模板匹配
│   └── llm.py          # Claude / OpenAI 视觉 API
├── storage/
│   ├── db.py           # SQLite（含 upsert）
│   └── export.py       # 转置 CSV 导出
├── dashboard/
│   └── app.py          # Gradio 四页签 UI
└── skill/
    └── trend-rover.md  # Claude Code 技能定义
```

## 配置

在项目根目录创建 `trend_rover.toml`：

```toml
[scraper]
min_delay = 2.0
max_delay = 5.0
max_retries = 3

[vision]
engine = "opencv"        # "opencv" 或 "llm"
threshold = 0.8

[llm]
provider = "claude"      # "claude" 或 "openai"
api_key = "sk-..."
model = "claude-sonnet-4-6"

[x]
cookies_file = "./x_cookies.json"
```

## 开发

```bash
git clone https://github.com/user/trend-rover.git
cd trend-rover
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium

# 运行测试（62 个测试用例）
pytest tests/ -v
```

## 参与贡献

欢迎贡献！以下是一些可以参与的方向：

- **新增平台** — Instagram、TikTok、Reddit、LinkedIn
- **优化爬虫** — 反检测策略、代理支持、频率控制
- **增强 Logo 检测** — YOLO / CLIP 模型、批量处理
- **仪表盘功能** — 图表、趋势可视化、对比视图
- **国际化** — 更多语言支持
- **文档完善** — 教程、示例、部署指南

### 如何贡献

1. Fork 本仓库
2. 创建功能分支（`git checkout -b feat/add-instagram`）
3. 先写测试（我们使用 TDD）
4. 实现功能
5. 运行 `pytest tests/ -v` 确保所有测试通过
6. 提交 PR

## 许可证

MIT

## Star History

如果这个工具对你的市场团队有帮助，请给个 Star！这有助于更多人发现这个项目。
