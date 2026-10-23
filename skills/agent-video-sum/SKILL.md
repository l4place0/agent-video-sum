---
name: agent-video-sum
description: >-
  Ingest Bilibili or YouTube videos into a local resource library through the
  video-sum CLI. Use when the user shares a video URL or share text, asks for a
  video summary/transcript/key frames, wants Bilibili comments, danmaku,
  audience sentiment or hotspot analysis, asks to save video learning material
  into a local folder, needs to install, update, or configure the CLI runtime,
  or wants to diagnose and report a problem encountered in that workflow. The
  Skill interprets intent, composes deterministic CLI primitives, creates an
  interactive single-page HTML learning experience, and can add a one-image
  visual summary when the host exposes image generation.
---

# Agent Video Sum

Use `video-sum` as the only business-operation interface. Interpret the user's
intent, choose explicit arguments, execute the CLI, and report its structured
result.

## Lifecycle entry points

Use the bundled thin scripts for lifecycle operations. On macOS/Linux invoke
the `.sh` files through `sh`; on Windows invoke the matching `.ps1` files.
They delegate to the pinned bootstrap and never clone source repositories.

- Install: run `sh scripts/install.sh` or `scripts/install.ps1` to produce a
  download plan. Show the plan, obtain approval, then rerun with `--apply`.
- Update: run `sh scripts/update.sh` or `scripts/update.ps1`. It atomically
  installs the CLI version pinned by the current Skill; use the same plan and
  approval flow.
- Onboard: run `sh scripts/onboard.sh status` to inspect effective settings.
  Run it without `status` to produce a configuration plan, then use `--apply`
  only after approval.
- Issue report: run `sh scripts/issue.sh` or `scripts/issue.ps1` after the user
  accepts diagnostic collection. It writes a permission-restricted,
  sanitized local Markdown report and never uploads it.

Use `--component cli|skill` with the issue script to label the failing layer
when routing is already known. Otherwise pass `--stage`; every stage routes to
the single `l4place0/agent-video-sum` repository, which now hosts both the
Skill and the CLI. Read [issue-reporting.md](references/issue-reporting.md)
before searching for duplicates or submitting the reviewed report.

Before the first operation, run `python3 scripts/bootstrap.py status` on
macOS/Linux (`py -3 scripts/bootstrap.py status` on Windows). Use the exact
absolute executable returned in `command` for every CLI invocation. If
the runtime is missing or broken, read
[environment-recovery.md](references/environment-recovery.md), show the
pinned GitHub Release download plan, and obtain explicit approval before using
`--apply`. Never clone the repository or install Python packages during normal
recovery.

Before the first capture or compose operation, run
`python3 scripts/bootstrap.py onboard status` on macOS/Linux
(`py -3 scripts/bootstrap.py onboard status` on Windows). Consume the
secret-safe effective values and their sources. Configuration precedence is:
explicit CLI argument, process environment, project `.env`, user
`config.env`, then built-in default.

If library, cache, or ASR configuration has not been confirmed, compose an
onboarding plan with absolute paths and explicit options:

```bash
python3 scripts/bootstrap.py onboard \
  --scope project \
  --library-dir "<absolute-library-path>" \
  --cache-dir "<absolute-cache-path>" \
  --asr-provider whisper-cpp \
  --asr-profile balanced
```

Show the returned `onboard_plan` and obtain explicit approval before rerunning
with `--apply`. Applying may create directories and write project or user
configuration. Existing differing values are preserved unless the user
approves `--update`. Treat `onboard_done.ready=false` as a blocked setup and
report the failed checks; do not start a capture.

The project does not publish a GPU-specific whisper.cpp runtime. Never invent
a CUDA download URL or imply that hardware detection proves backend support.
Configure only an existing absolute `whisper-cli` path or a separately
verified runtime whose installation the user approved.

Consume `acceleration` and `ai_guidance` from bootstrap status before choosing
an ASR path:

- Treat `acceleration.hardware` only as a dependency-free hardware candidate
  probe. It does not prove that a compatible runtime is installed.
- If `acceleration.whisper_cpp.recommendation` is
  `prefer_whisper_cpp_gpu`, the user did not select another provider, and
  `doctor --asr-profile balanced` is healthy, prefer
  `--asr-profile balanced`. The detected whisper.cpp GPU backend is enabled by
  default; do not invent additional GPU flags.
- If the recommendation is `offer_gpu_whisper_setup` or
  `offer_gpu_whisper_runtime`, tell the user which hardware backend was
  detected and offer a matching GPU-enabled whisper.cpp runtime and model.
  Obtain approval before installing dependencies, then rerun bootstrap status
  and doctor. Keep the configured ASR provider until the backend is verified.
- If the probe is `unverified` or `unavailable`, keep the configured provider.
  Do not infer GPU support merely from installed GPU hardware or a
  `--no-gpu` help option.
- Always obey `frame_extraction.recommendation`. The current CLI frame pipeline
  is CPU-only even when bundled FFmpeg reports hardware acceleration methods;
  never add unsupported FFmpeg flags.

Run `<command> doctor --asr-profile <profile>` when capability state is
unknown or after a missing-tool or missing-provider failure. Consume its
structured checks; do not ask for credentials that are already configured.

In the examples below, replace `video-sum` with the exact `command` returned by
bootstrap status. Do not rely on shell PATH changes.

## Delegate analysis

Prefer subagents whenever the host supports them and the request contains two
or more independent content-analysis stages. Keep CLI mutations and final
resource assembly in the main agent.

After raw artifacts are available:

1. Run a transcript agent, visual agent, and—when Bilibili audience artifacts
   were collected—an audience agent in parallel.
   - The transcript agent determines the domain, builds a glossary, corrects
     likely ASR terminology errors, and returns the corrected transcript plus a
     correction map. It must preserve timestamps and meaning.
   - The visual agent inspects the key frames, identifies which frames add
     explanatory value, and returns frame indices with concise reasons. It must
     inspect actual image contents rather than infer them from filenames.
     When a local source video is available and a UI transition, command, or
     prompt is only partly visible, request targeted follow-up frames with:

     ```bash
     video-sum frames extract "<video-file>" \
       --at "<MM:SS>" \
       --around 2 \
       --output-dir "<temporary-frame-dir>"
     ```

     Repeat `--at` for multiple regions. Treat scene/hybrid sampling as
     candidate generation and the host AI as the semantic selector.
   - Give the audience agent the comment-candidate JSON and danmaku-analysis
     JSON, not the full raw datasets by default. Ask it to name semantic
     clusters, interpret sentiment in context, explain hotspot timestamps, and
     select only comments that add useful qualifications, questions, or
     corrections. Require it to distinguish audience opinion from video
     evidence and return structured provenance for every selected comment.
2. Extract externally verifiable claims from the corrected transcript before
   synthesis. Preserve timestamps and include only `objective_fact` and
   `time_sensitive_fact`; do not fact-check opinions or personal experience.
   Follow the configured fact-check mode:
   - `off`: record `skipped` with `user_disabled`.
   - `auto`: verify important claims when search, page reading, source
     evaluation, and budget are available; otherwise record an explicit skip.
   - `important`: verify only decision-relevant or time-sensitive claims.
   - `all`: attempt every extracted factual claim.
   - `required`: stop before compose if verification cannot be completed.

   Prefer official material, primary papers, datasets, benchmarks, and source
   repositories. Use reliable secondary sources only when primary evidence is
   unavailable. Never treat a search-result snippet as verified evidence.
   Supported skip reason codes are `user_disabled`, `no_web_access`,
   `no_search_tool`, `no_page_reader`, `insufficient_source_evaluation`,
   `time_or_budget_limit`, and `source_unavailable`.
3. Give the corrected transcript, visual findings, audience findings when
   available, and fact-check result to a synthesis agent. Ask it for the
   summary and `# 辅助理解` Markdown, including Mermaid diagrams and
   `{{frame:N}}` placeholders. Put useful audience findings under a subordinate
   `## 观众讨论与补充` section; never present popularity as factual proof.
4. Use a verification agent to check factual faithfulness, source quality,
   claim timestamps, fact-check status, Mermaid syntax, frame references,
   heading order, and preservation of raw data.
5. Reconcile the results in the main agent. Generate and verify the interactive
   single-page HTML learning experience and, when eligible, the optional
   one-image summary described below.
6. Invoke the CLI once to save the resource.

Give each subagent only the artifacts needed for its role and require
structured output. Do not let multiple agents write the same note or run
overwriting CLI operations. Skip delegation for trivial read-only lookups,
very short material, or hosts without subagent support.

## Capture and compose a video

Run:

```bash
video-sum capture "<URL or complete share text>" \
  --output-dir "<destination>" \
  --lang zh \
  --frame-mode hybrid \
  --cache reuse \
  --fact-check auto \
  --frames 10
```

If the user has configured `VIDEO_SUM_LIBRARY_DIR`, omit `--output-dir` unless
they explicitly request a different destination. An explicit CLI destination
overrides the configured library only for that operation.

Pass complete Bilibili share text unchanged; the CLI extracts and HTML-decodes
the URL.

Ask for a destination only when it cannot be inferred from the request or
configured default. Preserve an explicitly supplied destination exactly.

Use:

- `--lang zh|en|ja` for the video's spoken/output language.
- `--asr-provider whisper-cpp|local|openai` only when the user selects or
  configuration recovery requires a specific transcription provider.
- `--asr-profile fast|balanced|accurate` selects a local `whisper.cpp` model
  from `ASR_MODEL_DIR` and implies `--asr-provider whisper-cpp`. When local
  model state is unknown, run `video-sum asr profiles` first. For local
  transcription, use `balanced` unless the user prioritizes speed or accuracy;
  do not select a profile for a configured remote provider.
- `--frames N` for key-frame count. Keep frames enabled unless the user
  explicitly requests audio-only output.
- `--frame-mode hybrid` combines uniform coverage with scene-change candidates
  and is the default for host-AI visual selection. Use `timestamp` for the
  fastest uniform sampling, or `scene` when transitions matter more than
  timeline coverage.
- `--cache reuse|refresh|off` defaults to `reuse`. Keep it for repeat work;
  use `refresh` only when the user asks to disregard cached artifacts, and
  `off` for cache-isolation diagnostics.
- `--fact-check off|auto|important|all|required` selects external verification
  strictness. Keep `auto` unless the user requests another mode.
- `--force` only after the user explicitly asks to replace an existing resource.

## Collect audience material

For a Bilibili learning-note request, collect hot comments and current danmaku
by default unless the user asks for a minimal or fastest run. Skip this section
for YouTube. Write artifacts to a temporary working directory until compose:

```bash
video-sum comments fetch "<URL>" \
  --mode hot \
  --limit 50 \
  --output "<temp>/comments.jsonl"

video-sum comments select "<temp>/comments.jsonl" \
  --limit 20 \
  --output "<temp>/comment-candidates.json"

video-sum danmaku fetch "<URL>" \
  --output "<temp>/danmaku.jsonl"

video-sum danmaku analyze "<temp>/danmaku.jsonl" \
  --bucket-seconds 30 \
  --output "<temp>/danmaku-analysis.json"
```

Use `comments fetch --mode all --limit 0` only when the user explicitly asks
for every accessible top-level comment. Warn that it may be slow or trigger
platform rate limits. The CLI intentionally excludes nested replies.

Treat `danmaku fetch` as current-accessible collection, never historical
collection. It normally uses anonymous `seg.so` requests. If metadata reports
`scope=sampled_degraded`, disclose that the CLI fell back to the XML sample and
avoid strong population-level claims. A configured Cookie may improve access,
but never require login merely to try current comments or danmaku.

Treat `comments select` and `danmaku analyze` as candidate generators:

- Let the host AI perform semantic clustering and contextual sentiment
  interpretation; do not rename lexicon signals as model conclusions.
- Use hotspot timestamps to inspect the matching transcript, frames, and—when
  a local source video is available—request targeted follow-up frames.
- Use selected comments only as attributed audience supplementation. Verify
  externally checkable corrections before relying on them.
- Do not pass full raw JSONL to a subagent when the bounded candidate and
  analysis JSON files are sufficient.

## Generate an optional one-image summary

Inspect the host's available tools after the textual synthesis is verified. If
the host exposes a callable image-generation tool or API, generate one visual
summary by default unless the user opted out. Follow any host-specific image
generation instructions before calling it. Do not infer capability from an
environment variable, install an image provider, request credentials, or use
image search as a substitute. A host without image generation follows the
normal workflow without warning or failure.

Build a compact visual brief from all collected material: corrected transcript
and timestamps, verified summary, selected key-frame findings, fact-check
results, and audience findings when collected. Include only audience insights
that survived synthesis, label them as audience opinion, and remove usernames
or other unnecessary personal data. Give the image generator the selected key
frames as visual references when its interface supports reference images;
otherwise describe their relevant visual evidence in the brief. Do not send
private or access-restricted source material to an external image provider
without the user's explicit approval.

Request a single portrait infographic that is readable as a standalone
overview. Prefer a strong title, one central thesis, three to six concise
points, a simple flow/timeline when useful, and a small caveat or verification
area. Keep text sparse, use the note's output language, and require exact
spelling for titles and key terms. Treat the verified Markdown note and linked
sources as authoritative; the image must not introduce new facts, quotes,
numbers, people, logos, or source claims. Do not present audience popularity as
proof.

Inspect the generated image itself when the host supports image inspection.
Check legibility, factual alignment, visible text, and accidental fabrication.
Retry once with a corrected prompt if there is a material defect. If the retry
is still misleading or unreadable, omit the image from the saved resource and
finish the textual note; report the omission without blocking compose.

When the image-generation result can be materialized as a local PNG or JPEG,
save it in the temporary working directory with a short source basename such
as `visual-summary.png`. Prefer lowercase ASCII letters, digits, and hyphens so
the CLI's filename sanitization is predictable. The CLI archives every data
asset as `assets/<resource_id>-<sanitized-source-basename>`; do not put the
resource ID in the source basename, or it will be prefixed twice. Add the final
archived path near the start of the summary file:

```markdown
![一图流总结](assets/<resource_id>-visual-summary.png)
```

Pass that source file to `resource compose` as an additional `--data-asset` and
make the Markdown link match the CLI-computed archived basename. Never write
directly into the library's final `assets/` directory or modify the note after
compose. If the host can only return a conversation image and cannot provide a
local file through its supported interface, show the image in chat, do not add
the Markdown embed or `--data-asset`, and disclose that it was not persisted.

## Generate an interactive single-page HTML summary

Generate one offline, responsive, purposefully interactive HTML learning page
from the verified synthesis by default unless the user opts out. It must use
interaction, animation, or dynamic diagrams to explain relationships that the
Markdown note cannot express as effectively; a static restyling of the note is
not sufficient. Read
[single-page-html.md](references/single-page-html.md) before authoring or
validating it. Save it in the temporary working directory with a
short source basename such as `summary.html`, add
`[打开单页 HTML 总结](assets/<resource_id>-summary.html)` near the start of the
summary file, and pass the source file to compose as a data asset. Use the same
CLI-prefixed naming rule for local assets referenced inside the HTML. Omit both
the link and asset when HTML validation fails; keep the Markdown note workflow
non-blocking.

After delegation and verification, save the host-authored result exactly once:

```bash
video-sum resource compose "<resource_id>" \
  --summary-file "<summary.md>" \
  --understanding-file "<understanding.md>" \
  --corrected-transcript-file "<corrected-transcript.md>" \
  --corrections-file "<corrections.json>" \
  --fact-check-file "<fact-check.json>" \
  --data-asset "<temp>/comments.jsonl" \
  --data-asset "<temp>/comment-candidates.json" \
  --data-asset "<temp>/danmaku.jsonl" \
  --data-asset "<temp>/danmaku-analysis.json" \
  --data-asset "<temp>/visual-summary.png" \
  --data-asset "<temp>/summary.html" \
  --fact-check auto \
  --output-dir "<destination>"
```

Omit audience asset flags for material that was not collected. Omit the
generated-image asset flag when image generation was unavailable, declined,
unsafe for the material, unsuccessful, or not materializable as a local file.
Omit the HTML asset flag when the user declined it or validation failed.

The summary and understanding files must not contain level-one headings.
The understanding file must contain at least one Mermaid diagram. The corrected
transcript is optional only when the user explicitly declines enhancement.

The fact-check file must use one of these distinct outcomes:

```json
{"schema_version":1,"status":"completed","mode":"important","checked_at":"2026-07-27","claims":[]}
```

```json
{"schema_version":1,"status":"skipped","mode":"auto","reason":"no_web_access","message":"Host has no web search or page-reading capability.","claims":[]}
```

A completed claim must include its timestamp, classification, video statement,
verification result, status, and linked sources. Supported claim statuses are
`confirmed`, `partially_confirmed`, `contradicted`, `outdated`, `disputed`,
and `unverified`. A non-`unverified` claim requires at least one linked source.
`completed` with no claims is not the same as `skipped`.

Distinguish video evidence, host inference, and external supplementation. Any
claim introduced from outside the captured video must include a clickable
source link next to the claim, preferring the author's own material and then a
reputable secondary source. If a source cannot be linked, omit the unsupported
detail or label it explicitly as unverified. Never present external
supplementation as content demonstrated by the video.

## Consume output

Treat stdout as versioned NDJSON. Ignore human logs on stderr.

Expected events:

```json
{"schema_version":1,"event":"started","source":"...","output_dir":"..."}
{"schema_version":1,"event":"stage","stage":"download","progress":10,"message":"..."}
{"schema_version":1,"event":"done","resource_id":"...","note_path":"...","manifest_path":"...","frame_paths":[]}
{"schema_version":1,"event":"composed","resource_id":"...","note_path":"...","manifest_path":"...","frame_paths":[]}
{"schema_version":1,"event":"comments_fetched","output":"...","count":20,"mode":"hot"}
{"schema_version":1,"event":"danmaku_fetched","output":"...","count":1404,"scope":"current_accessible"}
{"schema_version":1,"event":"danmaku_analyzed","output":"...","host_ai_review_required":true}
```

On success, verify the returned paths exist. Inspect the note and confirm it
contains these level-one headings in order:

```markdown
# 总结稿
# 辅助理解
# Data
```

Keep each resource as one Markdown note. Store every image in the single
`assets/` directory beside the note; never create a per-note directory.
The CLI also copies each `--data-asset` into that same `assets/` directory,
records it in the manifest, and inserts links under `# Data`. Do not copy raw
audience data manually into the Markdown body.

The host AI authors `# 辅助理解` as Markdown containing one or more Mermaid
diagrams. Insert only frames that materially clarify the adjacent explanation,
using `{{frame:N}}` placeholders for the CLI to resolve. Put the complete raw
transcript and all extracted key frames under `# Data`; do not create separate
transcript files. Keep raw audience datasets only as CLI-managed `assets/`
files linked automatically under `# Data`.

Report the saved note path, resource ID, number of key frames, HTML summary
status (`saved`, `skipped`, or `failed_validation`), and one-image summary
status (`saved`, `shown_in_chat`, `skipped`, or `failed_quality_check`). Do not
paste the full transcript back into chat unless requested.

## Inspect the resource library

Use read-only primitives:

```bash
video-sum library list --output-dir "<destination>"
video-sum library search "<query>" --output-dir "<destination>"
video-sum library show "<resource_id>" --output-dir "<destination>"
```

Use the `resource_id` returned by `capture` for an exact lookup. Prefer
`library search` over scanning Markdown files manually.

## Handle failures

Use the structured `code` field from the final `error` event:

- `invalid_input`: explain that the URL/platform or argument is unsupported.
- `resource_exists`: show the existing target and ask whether to rerun with
  `--force`; do not overwrite automatically.
- `ingestion_failed`: inspect stderr for the concrete provider/tool failure,
  then offer the narrow recovery action.
- `comments_fetch_failed`: report API access or rate-limit failure and continue
  the core note without comments unless the user required them.
- `danmaku_fetch_failed`: continue without danmaku unless explicitly required;
  do not substitute historical endpoints or demand login.

If `ffmpeg` or `yt-dlp` is missing, report the missing dependency. If ASR
credentials or local model capability are missing, ask the user which
configured transcription provider to use; do not silently switch providers.

If the problem remains unresolved, appears to be a product defect, or required
an undocumented workaround, offer to report it:

> 这个问题可能值得反馈给维护者。要我替你收集脱敏诊断、检查重复项、起草并创建 GitHub Issue 吗？提交前我会先把完整草稿给你确认，你不需要手动填写表单。

When the user accepts, read
[issue-reporting.md](references/issue-reporting.md) and complete the workflow
through the AI. Do not merely send the user to an empty form. Creating an Issue
is an external write: show the sanitized title and body and obtain explicit
confirmation immediately before submission. If no authenticated GitHub tool is
available, return the complete ready-to-submit draft and the repository Issue
URL instead of requesting credentials or claiming success.

## Safety

- Never delete or overwrite resources without explicit user authorization.
- Never echo API keys, cookies, or authorization headers.
- Never attach private video content, full transcripts, cookies, API keys,
  authorization headers, or local usernames to an Issue.
- Do not reimplement downloading, transcription, frame extraction, summary
  generation, or note rendering in shell/Python snippets; invoke the CLI
  primitive.
