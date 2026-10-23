# agent-video-sum 开发接手指南

核查日期：2026-10-23（Asia/Shanghai）。源码基线：`master` / `fa606cf`。本次仅研究本仓库；这里的 onboarding 指开发接手，不是执行用户 ASR 安装向导。

更新（2026-10-24）：下方 issue 对照保留修复前基线快照。当前工作区已针对 #9 增加显式分 P 选择与缓存隔离，针对 #8 对齐 Windows 路径并兼容旧配置/模型目录，针对 #7 将新笔记首标题改为 `# 总结`。详细取舍见 [PRE_FIX_ANALYSIS.md](PRE_FIX_ANALYSIS.md)；这些改动尚未发布。

## 1. 项目定位与现状

项目把视频学习拆成确定性的 CLI 操作与宿主 AI 内容分析。CLI 负责媒体下载、ASR、候选帧、缓存、结构校验及笔记写入；内嵌 Skill 指导宿主完成纠错、视觉选择、总结、事实核验与学习页面。

- 本地只有 `origin`：https://github.com/l4place0/agent-video-sum；GitHub 标记 `isFork=false`，没有另一个 fork parent。本指南将该远程仓库视为上游。
- 核查时本地 HEAD 与远程 master 相同，初始工作区干净。
- 源码版本和 Skill 的 `runtime.lock.json` 都是 `0.4.0`；最新 Release 为 [v0.4.0](https://github.com/l4place0/agent-video-sum/releases/tag/v0.4.0)。仓库最近完成改名、Skill 内嵌和旧环境变量别名清理。
- 远程有 3 个开放 issue、0 个开放 PR；旧 issue 中的仓库名和版本反映历史状态。
- 当前 HEAD 的 [Test](https://github.com/l4place0/agent-video-sum/actions/runs/39970588421) 和 [Release](https://github.com/l4place0/agent-video-sum/actions/runs/39976656392) workflow 均成功。这里只核对发布记录，未下载并逐一验证发行包。

## 2. 核心数据流与代码地图

```text
URL / 分享文本
  → cli/commands.py: capture
  → core/ingestion.py: IngestionService
  → 平台下载 → 缓存 → ASR → 候选关键帧 → capture 资源
  → 宿主 AI：术语纠错、选帧、总结、事实核验、可选观众分析
  → cli/commands.py: resource compose
  → core/library.py: 校验、复制资产、原子替换
  → 单份 Markdown + 同级 assets/
```

| 入口 | 接手时重点关注 |
| --- | --- |
| `cli/__init__.py`、`cli/commands.py`、`cli/output.py` | Click 命令注册；参数覆盖；stdout 的版本化 NDJSON；stderr 人类日志 |
| `core/ingestion.py` | 下载、转写、帧提取的编排；缓存 key；依赖注入便于 mock |
| `core/platforms/bilibili.py`、`youtube.py`、`base.py` | B 站先走公开 API，失败回退 yt-dlp；YouTube 走 yt-dlp |
| `core/asr/` | whisper.cpp 本机进程、OpenAI API、兼容 HTTP 服务三种 provider |
| `core/vision/frames.py` | hybrid 场景/时间采样和指定时间补帧；语义筛选由宿主完成 |
| `core/cache.py` | 用户级缓存、SQLite 索引、lease、TTL/LRU |
| `core/library.py` | resource ID、manifest、最终笔记及资产；Windows 原子替换与权限继承 |
| `core/config.py` | Pydantic settings；项目/用户配置与环境变量 |
| `core/community.py`、`core/fact_check.py` | 评论/弹幕候选与核验结构；不把热度当事实 |
| `skills/agent-video-sum/` | 产品 Skill、bootstrap、install/update/onboard、脱敏 issue 草稿 |
| `scripts/build_standalone.py`、`.github/workflows/` | 独立包构建、测试和发布 |
| `docs/automation/loopctl.py` | 仓库工程流程状态/证据管理；不是产品采集流水线 |

推荐阅读顺序：README → ARCHITECTURE → CLI → ingestion → library/cache → 对应平台/ASR → 内嵌 Skill 和 bootstrap → 测试 → 工程流程文档。

## 3. 开发与运行

Python 要求 `>=3.10`，仓库约定使用 uv。新开发环境的标准命令为：

```powershell
uv sync --extra dev
uv run video-sum --help
uv run ruff check .
uv run pytest --tb=short -q
```

已有环境需要避免隐式同步时，使用 `uv run --no-sync ...`。本次使用已有 `.venv`，没有安装依赖。

真实采集还需要 FFmpeg 和可用 ASR。源码开发安装不等于已装好 whisper.cpp：模型和 `whisper-cli` 都不包含在 Release 内；Release 包含 Python、依赖和 FFmpeg。三档本机模型分别为 `ggml-base-q5_1.bin`、`ggml-small-q5_1.bin`、`ggml-medium-q5_0.bin`。

运行诊断的入口：

```powershell
uv run video-sum doctor
uv run video-sum asr profiles
uv run python skills/agent-video-sum/scripts/bootstrap.py onboard status
```

这些诊断与测试通过都不能替代真实视频端到端验收。用户安装场景使用 Skill 薄脚本与固定版本 Release；开发环境则使用源码和 uv。

配置优先级：CLI 参数 > 进程环境 > 项目 `.env` > 用户 `config.env` > 默认值。建议显式确定 library、cache、model 的绝对路径，尤其是 Windows，见下文 #8。

## 4. 必须守住的行为约定

- `capture` 提供原始材料，最终内容由宿主生成后交给 `resource compose`。
- 每条资源一份 Markdown；图片、manifest 和附加 HTML/观众数据统一进入同级 `assets/`。
- 当前工作区一级标题契约为 `# 总结`、`# 辅助理解`、`# Data`。保留原始转写与帧，区别视频证据、AI 推断和外部补充。
- `auto` 等模式可显式跳过外部核验；`required` 有严格闸门。结构化校验并不自动证明事实真实。
- Skill 还规定默认尝试交互 HTML；宿主有图像生成能力时可产生一图总结。这些是宿主侧行为，并非 CLI 内置 LLM。
- 评论默认热门一级评论；弹幕为当前可访问数据，降级样本需标明。候选排序与词典信号不能直接当作语义结论。
- GPU 硬件存在不代表 whisper GPU 后端有效；当前帧处理流水线按 CPU 路径工作。
- 修改写入逻辑时保留目标目录内创建临时文件再原子替换的策略，避免 Windows ACL 回归。

## 5. 上游 issue：状态与源码对照

以下优先级是本次接手建议，不是上游标签。

| 建议顺序 | Issue | 核查结论 | 建议验收范围 |
| --- | --- | --- | --- |
| 1 | [#9 B 站多 P 采集不完整](https://github.com/l4place0/agent-video-sum/issues/9)，OPEN | 当前公开 API 下载仍用 `view.cid`，metadata 用聚合 `view.duration`；URL 解析只返回 BV 号。与报告吻合，尚未重新下载原视频复现 | 明确分 P/全选语义；标题、时长、转写、帧一致；分 P 隔离缓存及 resource ID；覆盖默认 URL、`?p=N`、非法 P、回退路径及旧缓存 |
| 2 | [#8 Windows 模型目录错误](https://github.com/l4place0/agent-video-sum/issues/8)，OPEN | bootstrap 手工拼接目录，CLI 使用 platformdirs；本机直接比较默认值，model/config/cache 三项均不相等 | 统一路径契约；兼容已有目录与配置；不自动覆盖；跨层测试验证 onboard 写入后 CLI 能读取 |
| 3 | [#7 总结标题不符](https://github.com/l4place0/agent-video-sum/issues/7)，OPEN | issue 期待“总结”，当前 README、Skill、renderer 都明确使用“总结稿” | 先确定产品契约；如改名，文档、生成器、测试、历史兼容策略一起调整 |

#9 的修复不能只改 metadata duration：`core/ingestion.py` 的媒体 key 使用平台名与 BV，`core/library.py` 使用 `platform-video_id` 构造资源 ID。分 P 身份需要贯穿下载、缓存、资源与引用，否则会有内容复用或资源冲突风险。

#8 的扩大影响来自本机默认值比较，不等于已经复现所有用户配置失效情形。bootstrap 默认数据根为 `%LOCALAPPDATA%/video-sum`；CLI 的 platformdirs Windows 默认路径包含重复应用目录层级。项目 `.env` 和显式环境变量可能掩盖这种差异，用户级配置读写尤其值得覆盖。

已关闭的历史 issue 提供设计背景：

- [#1 首次安装 onboarding](https://github.com/l4place0/agent-video-sum/issues/1)：已有 plan/apply/status、配置优先级与预检；不代表 #8 不存在。
- [#3 可降级外部事实核验](https://github.com/l4place0/agent-video-sum/issues/3)：已引入结构化状态、原因码与严格模式。
- [#5 Windows compose ACL](https://github.com/l4place0/agent-video-sum/issues/5)：已有目标目录暂存修复与 Windows CI，修改 library 时需要保留回归覆盖。

## 6. 开发流程与本次验证

`CLAUDE.md` 要求使用 uv、改代码前 mock 外部依赖自测业务流程、提交前通过单元/集成测试。CI 包含 Linux Python 3.11/3.12、ruff、Windows compose 回归和 Skill 测试；项目声明支持 Python 3.10，但当前测试矩阵未覆盖它。

工程任务参考 `ISSUE_ENGINEERING_LOOP.md` 和 `automation/engineering-loop.md`：先记录问题、验收与证据，再实现、测试、审查；对外操作受当次授权范围约束。普通开发接手不需要启动 issue 修复状态机。

本次已验证：本地/远程 SHA 一致；CLI help 可运行；`uv run --no-sync ruff check .` 通过；`uv run --no-sync pytest -q` 为 **113 passed in 66.94s**（包含内嵌 Skill 测试）；Windows 三组默认路径对比均不一致。

本次没有下载真实视频、调用云端转写或执行运行时配置 apply。上述 issue 判断区分了源码证据、默认值实测和报告中的历史复现；完整采集能力需要后续真实媒体验收。
