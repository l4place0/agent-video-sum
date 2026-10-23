# Interactive single-page HTML summary

Author one standalone interactive learning experience from the corrected transcript,
verified summary, selected frame findings, fact-check results, and synthesized
audience findings when available. Keep the Markdown note and its linked sources
authoritative. Do not introduce unsupported facts or dump the full transcript,
comment dataset, or danmaku dataset into the page. Bounded, selected original
comments or danmaku phrases may be shown when they materially support an
audience-data interaction and are safely escaped.

The page must add explanatory value beyond typesetting the Markdown note. Use
interaction to let the learner explore comparisons, sequences, evidence, or
cause-and-effect relationships. Do not create decorative controls that reveal
the same paragraph without improving understanding.

## Content

- Use the note's output language and a descriptive document title.
- Present the central thesis, three to six key points, and a compact
  flow/timeline or comparison when it materially aids understanding.
- Add key terms, practical takeaways, and caveats or verification status.
- Put audience material in a visibly subordinate section labeled as audience
  opinion. Never use popularity as factual proof.
- When comment or danmaku artifacts were collected, do not reduce them to
  decorative totals. Add at least one interactive audience-data view that is
  justified by the available fields—for example a selectable danmaku timeline,
  engagement plot, or semantic-cluster explorer. Always display collection
  scope, sample size, platform-reported totals when available, completeness,
  and whether categories overlap. Do not convert hot-comment samples into
  population percentages or public-opinion claims. Anonymize authors unless
  identity is necessary to understand the material.
- When the available danmaku analysis contains time buckets, lexical sentiment
  signals, or repeated-text clusters, combine the applicable views instead of
  showing density alone. Label lexicon categories as overlapping signals, not
  mutually exclusive sentiment shares, and expose the method or limitation.
- Co-locate controls and readouts that explain the same data view. For example,
  place danmaku signal selectors, the timeline, and both selected-state details
  inside one timeline analysis surface instead of stacking them as unrelated
  modules.
- When timestamped danmaku and per-bucket signal data are available, link them
  directly: selecting a time bucket should update that bucket's signal counts,
  leading-signal marker, and a bounded set of representative original danmaku.
  Keep overlapping-signal and lexicon false-positive caveats visible; describe
  the marker as a leading lexical signal, not the objective emotion of a period.
- Stack dense audience-analysis surfaces vertically when both contain charts,
  long labels, or original comments. Give each surface the full content width
  instead of forcing a desktop-only side-by-side composition.
- A word cloud is appropriate for repeated-text clusters when it preserves
  exact collected counts. Scale font size by count, expose the numeric value in
  accessible text and selection details, keep words keyboard operable, and do
  not use color or placement to imply an unsupported topic or sentiment.
- For classified comment views, prefer showing the selected original comment
  text beside its category, engagement counts, and verification status when it
  is safe and useful. Keep the selection bounded, remove unnecessary identity,
  and distinguish verbatim audience text from host interpretation.
- Include concise source links for externally supplemented claims. Preserve
  video timestamps for claims derived from the video.
- Include the generated one-image summary with
  `<img src="./<resource_id>-visual-summary.png">` only when the source image
  is passed to compose as `visual-summary.png` and will be archived beside the
  HTML. The CLI prefixes the resource ID; do not pre-prefix the source file.
  Provide meaningful alt text.

## Interaction contract

- Include at least two meaningful learning interactions. Choose only patterns
  supported by the material, such as a step-through process, mode/comparison
  explorer, filterable evidence view, annotated timeline, clickable system
  map, scenario switcher, or short self-check.
- Make at least one interaction a controllable animated explanation or dynamic
  chart/diagram. Give the learner play/pause, restart, step, filter, or select
  controls rather than running an endless decorative animation.
- Make every control keyboard operable with visible focus, semantic buttons or
  inputs, accessible names, and current state exposed through `aria-pressed`,
  `aria-selected`, `aria-expanded`, or a polite live region as appropriate.
- Respect `prefers-reduced-motion`. Disable nonessential motion and keep state
  changes immediate when reduced motion is requested.
- Keep the core thesis, conclusions, caveats, and source links readable when
  JavaScript is unavailable. Use JavaScript as progressive enhancement, not as
  the only place where learning content exists.
- Do not invent quantitative charts. A dynamic chart must visualize collected
  values with their scope and caveats, or express a qualitative structure
  without implying measured magnitude.

## File contract

- Produce one UTF-8 HTML5 file with `<!doctype html>`, a correct `lang`,
  `<meta charset="utf-8">`, and a viewport meta tag.
- Inline all CSS. Use semantic landmarks, a responsive layout, accessible
  contrast, visible keyboard focus, and print-friendly styles.
- Inline all JavaScript and keep it dependency-free. Do not use remote scripts,
  remote stylesheets, remote fonts, trackers, iframes, autoplay media, or assets
  that will not be archived beside the HTML. Do not make automatic network
  requests; validated source links may navigate only after user activation.
- Keep scripts small and auditable. Bind behavior to fixed authored elements;
  use `textContent`, DOM attributes, and explicit allowlisted values instead of
  injecting captured material with `innerHTML`.
- Escape all transcript, title, comment, danmaku, and source text before placing
  it in markup or attributes. Never inject captured text as raw HTML.
- Allow only validated `http` or `https` source links. HTML-escape URLs and use
  `rel="noopener noreferrer"` for links that open a new tab.
- Keep the page useful without the generated image or any selected key frame.

## Validation

Open or render the local page when the host provides a browser or HTML preview
capability. Check desktop and narrow layouts, print output, text overflow,
navigation, local image resolution, source links, and factual alignment. Use
every interactive control with pointer and keyboard paths; verify state and
live-region changes, animation pause/restart or step behavior, reduced-motion
fallback, and an empty error console. When no renderer is available, inspect
the file statically and confirm required metadata, heading order, escaped
content, local asset references, inline script boundaries, control/state
pairing, progressive-enhancement content, and absence of automatic network
requests. Fix validation failures before compose; if they cannot be fixed,
omit the HTML asset and its Markdown link.
