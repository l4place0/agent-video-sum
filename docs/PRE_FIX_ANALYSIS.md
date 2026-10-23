# 修复前分析：#9、#8、#7

日期：2026-10-23。基线：`fa606cf`。仅分析，没有实现补丁、修改配置、迁移数据或向 GitHub 写入。本报告的建议尚未成为产品契约。

## 结论与顺序

| 顺序 | 问题 | 证据强度 | 改动规模判断 |
| --- | --- | --- | --- |
| 1 | #9 分 P 身份在采集链路丢失 | 源码 + 无网络 mock 复现 | 中等偏大：平台、编排、缓存、资源、弹幕一致性、CLI/Skill |
| 2 | #8 bootstrap 与 CLI 路径契约分叉 | Windows 本机默认路径实测 + 源码 | 中等：跨层配置读取、兼容旧布局、计划和预检 |
| 3 | #7 标题契约冲突 | renderer、README、Skill、测试一致；与 issue 期望不一致 | 产品决定先行；若改名，代码量小但需兼容既有笔记 |

建议分别处理、独立验收。上一轮基线测试为 113 passed、ruff 通过；现有测试没有覆盖这里的关键跨层关系，测试绿不能排除这些问题。本轮未重复全量测试，也未下载视频或调用真实 ASR。

## #9：多 P 内容与元数据、缓存、资源身份不一致

上游：[Issue #9](https://github.com/l4place0/agent-video-sum/issues/9)。

### 根因链

1. `core/platforms/bilibili.py:28` 的 `parse_url()` 仅返回 BV，丢弃 `p`。
2. `:73` 的公开 API 路径固定取 `view.cid`，没有从 `pages` 选择目标分 P；`:144` 保存 `view.duration`，没有取分 P 时长。
3. `core/ingestion.py:70` 在下载之前用平台和 BV 构造 media key，后续音频、视频、转写、帧和 metadata 都由它派生。
4. `:124` 开始读取缓存；缓存齐全时 `:152` 可以完全绕过下载。只修下载函数无法纠正已经缓存的错误结果。
5. `core/library.py:318` 的 resource ID 为 `platform-video_id`，`:320` 笔记文件名仅由标题产生。仅隔离缓存仍不足以让多个分 P 共存。

### 无网络复现

使用两个分 P 的合成 view：P1=`cid=111, duration=100`，P2=`cid=222, duration=200`，顶层 `cid=111, duration=300`。mock HTTP、媒体下载和音频转换，直接调用当前公开 API 下载路径：

| 输入 p | 实际请求 cid | 保存 duration | parse_url 返回 |
| --- | --- | --- | --- |
| 1 | 111 | 300 | 同一 BV |
| 2 | 111 | 300 | 同一 BV |
| 999 | 111 | 300 | 同一 BV |
| abc | 111 | 300 | 同一 BV |

另行调用 `media_key()`，P1/P2 的 key 相等。这个实验确认当前代码的选择与身份问题；没有声称重新复现了 issue 中那条真实视频。

### 额外影响与陷阱

- `core/community.py:262` 的弹幕解析已根据 `p` 选择 cid，采集模块却忽略它。同一个 P2 链接存在“P1 转写/画面 + P2 弹幕”的混合风险。评论接口用 aid，属于整条投稿，不能假装是某一 P 的独立评论。
- `BilibiliPlatform.download()` 捕获所有异常后回退 yt-dlp。新增非法 P/未选择 P 错误若仍落入这个 catch，会绕过新的业务限制。
- 回退下载也必须选择同一分 P；`YtdlpPlatform` 目前假定单个 info 对象，没有明确 playlist 结果处理。视频单独下载的 options 只从主 options 复制 cookie；仅在音频 options 设置选 P 不够。
- 公开 API 路径可能先生成 WAV 再在取视频时失败；回退函数看见已有 WAV 会复用它。验收应覆盖部分失败，防止回退把不同范围的音频/视频拼在一起。这里是源码推导的风险，未做真实网络故障复现。
- 转写最后一个时间戳不等于媒体时长：片尾静音是正常情况。不能以二者严格相等作为完整性的唯一标准。

### 推荐行为与实现边界

建议第一阶段支持“显式单 P”，不在同一修复中引入自动整课聚合：

- 单 P 投稿继续直接采集，尽量保持现有资源 ID。
- 多 P URL 没有明确选择时，返回结构化的选择提示和分 P 列表，停止下载/转写；不再返回含糊的成功结果。
- `?p=N` 明确采集对应分 P。可增加 `--part N`，若同时存在 URL 参数，冲突应明确报错，不能静默选其中之一。
- 将 BV、cid、part index、part count、part title、part duration、canonical URL 和范围类型作为结构化来源信息。保留 BV 原义，不建议只把 `BV-p2` 塞进所有 `video_id` 字段。
- 在缓存查找前完成范围解析。建议缓存身份使用 BV+cid+范围版本；资源 ID 对多 P 使用可稳定识别的分 P 身份，标题/文件名包含 P 编号以避免同标题冲突。
- 下载与弹幕复用同一套选择规则；评论仍标注投稿范围。避免直接复用带 HTTP/评论职责的大对象，应提取小的选择/规范化逻辑。
- 在本次 B 站缓存命名空间或派生参数中增加范围版本，使旧的“仅 BV”缓存不自动命中；不必让 YouTube 缓存一起失效。
- 保留旧笔记和旧 manifest 的读取能力，不自动覆盖或迁移旧资源。旧记录缺少 cid/范围信息时不能凭 BV 认定为完整课程。

替代方案“默认 P1 并显式标注”改变较小，但仍可能违背用户传入整课链接的意图；“自动所有 P”还需要聚合时间轴、失败恢复、逐 P 预算和资源组织设计，范围明显更大。

### 必须覆盖的验收

1. 单 P 回归；多 P 无选择；P1/P2；非整数、零、负数、越界与重复冲突参数。
2. 所选 cid、标题、时长、canonical URL、音视频、弹幕完全一致；投稿评论明确标注范围。
3. P1/P2 不共享媒体、metadata、ASR、帧或资源 ID；两份笔记可共存，同名分 P 不互相覆盖。
4. 缓存命中与非命中产生相同范围；旧缓存不能绕过新的选择规则。
5. API 失败回退、已有部分 WAV、音视频分开下载和 playlist 返回均不改变目标分 P。
6. 非法选择是稳定的结构化错误，不会进入兜底下载；正常单 P/YouTube 工作流保持通过。

## #8：默认路径和有效配置由两个实现分别定义

上游：[Issue #8](https://github.com/l4place0/agent-video-sum/issues/8)。

### 已确认的路径分叉

`core/config.py` 使用 platformdirs，bootstrap 的 `default_user_*()` 用标准库手工拼接。Windows 本机输出如下，根目录用 `%LOCALAPPDATA%` 表示：

| 对象 | CLI 默认值 | bootstrap 默认值 |
| --- | --- | --- |
| user config | `video-sum/video-sum/config.env` | `video-sum/config.env` |
| models | `video-sum/video-sum/models` | `video-sum/models` |
| cache | `video-sum/video-sum/Cache` | `video-sum/Cache` |

cookies 的默认值也来自各自数据根，源码上受相同分叉影响。安装可执行文件的 bin 路径属于另一项契约，不应顺手移动。

### 为什么不能只修 model_dir

- `effective_onboard_config()` 从 bootstrap 自己的 user config 读取，而 CLI 的 Settings 从另一处读取。用户级 apply 可以写成功，却没有改变 CLI 的有效配置。
- 项目 `.env` 或环境变量能覆盖默认值，掩盖这个问题，因此现有项目配置测试通过并不奇怪。
- `onboard_values()` 不发现已有模型，仅选显式值、已有配置或内置目录；plan 没有把缺少目标模型作为独立预检结果展示。
- `doctor_onboard_check()` 启动真实 CLI，只传 provider/profile，以项目目录为 cwd；它没有证明 CLI 的路径值与 bootstrap 一致。返回码健康也可能只是 CLI 在另一套已有配置下可用。
- 测试通常显式注入临时 model/cache 路径，mock doctor/ASR；`tests/test_config.py` 又显式传入 dotenv 文件，绕过了两套默认 user config 定位。缺少 bootstrap 写入与 CLI 读取的集成契约测试。

### 推荐策略

优先保留 CLI 已发布的 platformdirs 默认布局作为新版本的 canonical 布局，使 bootstrap 与其对齐；同时兼容 bootstrap 曾写出的较浅路径。这样可减少对已有 CLI 缓存/模型的干扰。若希望改成更简洁的新目录，也可以，但应作为显式迁移设计，不能只改一个函数。

路径策略需覆盖以下行为：

1. 显式 CLI/环境/项目配置继续具有最高优先级，保留已有有效选择；不要为了“标准化”改写用户路径。
2. 用户配置发现兼容两种旧位置；若只有一份，读取它；两份内容冲突时在 plan/status 明确报告来源与冲突，不静默合并秘密或覆盖文件。确定迁移后只保留一个明确写入目标。
3. 模型发现只探测已知旧/新目录，并按选定 profile 检查准确文件名；多个有效候选报告选中原因；都没有时 plan 明确 `model_missing`。不递归扫描整个用户目录。
4. 对 cache 不自动搬移/删除；保留配置中选定的位置。无配置但存在多份缓存时要采用稳定规则并披露结果。
5. 安装前 bootstrap 只依赖标准库，不能简单 `import core.config` 或新增未安装的 platformdirs 依赖。可维护一个很小的路径协议实现，并用跨层契约测试约束；若提取公共模块，必须同时验证独立 Skill 分发与 CLI 打包能携带它。
6. apply 后让实际 CLI 返回脱敏的有效配置与来源，再与计划逐项比较；不能仅靠 bootstrap 自身重读文件和 doctor 返回码判断配置生效。

邻近兼容点：CLI 在未选 profile 时保留 `WHISPER_CPP_MODEL` 路径行为，而 bootstrap 默认 profile 为 balanced；旧别名读取也不完全相同。路径修复需验证不会破坏这些已有行为，不必在这次扩大为全面重写配置系统。

### 必须覆盖的验收

- Windows project/user 两个 scope；无配置、新目录、仅旧目录、两份配置冲突、已有显式路径、环境覆盖。
- 空模型目录、已有 balanced 模型、缺少所选 profile、两个目录都有模型；plan 无写入、apply 幂等、不覆盖冲突。
- 临时隔离用户目录中运行 bootstrap 与真实 CLI 子进程，验证实际 library/cache/model/config 来源相同；外部 ASR 可 mock，但配置读取不能 mock 掉。
- CLI 健康但读到另一套配置时，不能报 onboarding 完全就绪。
- Linux/macOS 路径契约回归，包括 XDG 自定义值和独立 Skill 运行；保护已有秘密脱敏与 UTF-8 行为。

## #7：属于产品契约决策，不是已定位的单点回归

上游：[Issue #7](https://github.com/l4place0/agent-video-sum/issues/7)。

`core/library.py:442`、中英文 README、内嵌 Skill 和 `tests/test_ingestion.py:84` 都明确采用“总结稿”。issue 要求“总结”，两者冲突。现有证据无法认定当前代码违背仓库当前约定，也不能仅因文档一致就自动关闭用户诉求。

推荐在前两项修复期间保持当前标题，单独确定以下选择：

- 保留“总结稿”：不需要代码补丁，后续在上游解释契约并按用户授权处理 issue。
- 统一改为“总结”：同时改 renderer、文档、Skill、测试；新 capture 和新 compose 输出新标题；已有文件不批量改写。

兼容性判断：compose 从 `## 原始转写稿` 提取原文，而非依赖 `# 总结稿`，因此旧标题笔记原则上仍可 compose；需要回归验证。外部校验器或知识库标题锚点可能受影响，应在发布说明中记录变化。没有必要为两个同义标题引入长期可配置选项。

若改名，验收包括：capture/compose 的 H1 顺序、旧标题笔记再次 compose、原始转写与资产完整保留，以及文档/Skill 一致。

## 实施前需要固定的决策与当前建议

| 决策 | 当前建议 | 原因 |
| --- | --- | --- |
| 多 P URL 未明确选 P | 提示选择并停止采集 | 避免静默生成不完整课程笔记 |
| 首轮是否支持整课聚合 | 暂不纳入 | 单 P 完整性已能满足 issue 的一种明确预期；聚合需单独设计 |
| Windows canonical 目录 | 对齐现有 CLI 布局，并兼容浅目录 | 减少已安装模型/缓存迁移风险 |
| 标题 | 暂保持“总结稿”，单独定产品要求 | 当前实现和公开契约一致 |

以上为推荐方案，尚未应用。下一步进入实现前应确定这些行为，先补能复现缺陷的测试，再实施最小兼容补丁；不能用仅修改 duration、model_dir 或一个标题字符串代替完整验收。
