---
name: autofigure
description: Use this skill when creating publication-ready scientific SVG figures for flowcharts, architecture diagrams, conceptual schematics, and methodology overviews. This skill is for non-data figures only — no bar/line/scatter charts, no heatmaps, no ROC curves, no plots derived from numerical data. Use when the user asks to create a figure, diagram, or illustration for a paper, survey, blog post, or textbook.
license: MIT
requires:
  bins:
    - cairosvg
  platforms:
    os:
      - linux
      - darwin
metadata:
  author: vlln
  version: "0.1.0"
---

# AutoFigure

Generate publication-ready scientific SVG figures for **non-data** content
(flowcharts, architecture diagrams, conceptual schematics, methodology overviews)
through iterative refinement (Generate → Evaluate → Improve). Agent drives the loop;
evaluation prompts live in `references/prompts/`.

## Trigger Keywords

figure, diagram, illustration, schematic, flowchart, architecture diagram,
methodology overview, conceptual diagram, paper figure, publication figure,
journal figure, scientific figure, SVG figure, workflow diagram

## Publication-Figure Standard

The target is a **paper-ready figure**, not an explainer slide, dashboard, or
text summary. A successful figure should resemble a concise journal schematic:
one strong visual metaphor, sparse labels, clear flow, and just enough text to
make the scientific claim interpretable with the caption.

Hard design rules:
- **One visual thesis**: encode the paper's central claim as spatial structure
  (e.g., funnel, landscape, circuit, split cohort, gated pipeline, feedback loop).
  Do not merely place study facts in adjacent cards.
- **Low text density**: default to short labels (1-5 words). Use at most
  8-12 primary text blocks on the canvas. Avoid paragraph-like sentences inside
  boxes. Put nuance in the caption, not in the figure body.
- **No dashboard layout by default**: avoid four equal panels, title bars,
  stacked cards, and long explanatory footers unless the user explicitly asks
  for a slide-style overview.
- **Visual encoding before wording**: show relationships through position,
  arrows, grouping, color, scale, icons, and simple symbolic shapes; text should
  name the elements, not explain every element.
- **Caption-ready, title-light**: paper figures usually do not need a large
  headline inside the artwork. Prefer a compact label or no title; assume the
  manuscript caption carries the full explanation.
- **Information triage**: include only the core mechanism/pipeline/claim.
  Secondary methods, caveats, sample sizes, abbreviations, and exact metrics
  should be reduced to tiny annotations or omitted if they dilute the figure.

## Scope

This skill draws **relationship diagrams** — information structured as nodes,
connections, flows, and hierarchies. Correct use cases:

| Yes (non-data figure) | No (data figure — use dedicated tools) |
|---|---|
| CONSORT participant flow | Bar chart, histogram, box plot |
| Experimental design overview | Scatter plot, PCoA, PCA projection |
| Methodology workflow | Heatmap, correlation matrix |
| System architecture diagram | ROC curve, precision-recall curve |
| Conceptual mechanism / pathway | Line chart, time series |
| Hierarchical taxonomy / ontology | Volcano plot, Manhattan plot |

Rule of thumb: if a figure's value depends on the **numerical accuracy** of rendered
data points, this skill cannot produce it — a generative model cannot guarantee
faithful data rendering.

## Configuration

All via environment variables. See `.env.example` for the full list.

Minimal setup:
```sh
export AUTOFIGURE_EVAL_API_KEY="sk-or-v1-..."
```

> `AUTOFIGURE_ENHANCE_API_KEY` and `AUTOFIGURE_ART_STYLE` are no longer
> required — enhancement is deprecated (see P6).

## Workflow

### P1. Prepare

1. If the user provided a paper (PDF/Markdown), read it and extract the core
   methodology, key findings, and concepts.
2. **Reject data figures before planning.** If the user asks for a bar chart,
   scatter plot, ROC curve, heatmap, line chart, or any figure that depends on
   rendering numerical data, explain the scope limitation and suggest
   alternatives (e.g., Python matplotlib/seaborn, R ggplot2, BioRender).

3. For `paper` topic, inspect reference figures from `references/paper/` only
   as style/density examples unless the user asks to reuse them.

4. Produce a **figure brief** before drawing:
   - `claim`: one sentence stating the scientific argument the figure should
     make.
   - `visual_metaphor`: the spatial metaphor that will carry the claim
     (e.g., gated pipeline, basin/landscape, layered axis, loop, fork-and-merge).
   - `must_show`: 3-5 indispensable elements.
   - `can_omit`: details that belong in the caption or text.
   - `text_budget`: maximum primary labels and maximum words per label.

5. **Check configuration and ask only for missing values:**

   Infer without asking when the user's request or paper makes the target clear.
   Ask only if ambiguous:
   - **Drawing target** — what specifically should the figure visualize?
     (e.g., "the proposed MoE routing mechanism in Section 3.2",
     "the overall training pipeline", "the benchmark results in Table 2")

   Check and note if missing, but do not block:
   - `AUTOFIGURE_EVAL_API_KEY` — VLM evaluation is disabled when unset; use
     subAgent evaluation if available, otherwise manual evaluation with the
     same JSON schema.
   - Topic — if ambiguous from the user's request, ask. Default: `paper`.

   Use defaults without asking:
   - `AUTOFIGURE_MAX_ITERATIONS` → 5
   - `AUTOFIGURE_QUALITY_THRESHOLD` → 8.0
   - `AUTOFIGURE_OUTPUT_DIR` → `./autofigure_output`
   - `AUTOFIGURE_RENDER_WIDTH/HEIGHT` → 1333×750

   If the output directory already contains files, create a suffixed directory
   (e.g., `autofigure_output_1`) unless the user explicitly wants overwrite.

### P2. Generate

Generate SVG, then automatically validate and render:

1. **Choose the design strategy** — Before writing SVG, compare 2-3 candidate
   visual metaphors in one or two sentences each. Select the one that best
   compresses the central claim with the least text. If the best candidate is
   still a grid of equal cards, redesign the concept.

2. **Generate SVG** — Agent produces an SVG figure visualizing the content.
   Design constraints:
   - Canvas: 1333×750. Use clear visual hierarchy, consistent palette,
     no overlapping components.
   - Topic roles: paper=figure designer, survey=visualization expert,
     blog/textbook=educational illustrator.
   - For paper topic, use reference figures as style and density guides. Include
     them inline only if the user asks or the figure specifically requires it.
   - Make the figure look like a manuscript schematic: integrated composition,
     light labels, deliberate whitespace, and a clear visual path.
   - Prefer symbolic visual elements over text-heavy cards: icons, small
     document glyphs, cohorts, microbial shapes, gates, modules, arrows,
     layered bands, gradients, or contours when they carry meaning.
   - Avoid large in-figure titles, paragraph labels, legends that restate the
     whole diagram, and repeated cards with similar text.

   SVG code standards:
   - **Group logically** — wrap related elements in `<g>` with an `id`
     (e.g., `<g id="background">`, `<g id="data-flow">`, `<g id="labels">`).
   - **Define reusable symbols in `<defs>`** — arrow markers (`<marker>`),
     gradients (`<linearGradient>`), and drop shadows (`<filter>`) go in a
     single `<defs>` block at the top.
   - **Prefer simple shapes over `<path>`** — use `<rect>`, `<circle>`,
     `<line>`, `<polygon>` when they fit. Reserve `<path>` only for curves.
   - **Comment each section** — add a brief `<!-- purpose -->` comment above
     each `<g>` group.

3. **Structural check** — Run the structural validity check on the SVG.
   If errors, fix the SVG (max 3 attempts) before proceeding.

4. **Render** — `cairosvg {svg} -o {png} -W 1333 -H 750`.
   If rendering fails, treat it as a structural error and go back to step 2.

### P3. Evaluate

Evaluation runs in an isolated context so the critique is independent.
The evaluator uses a **5-layer** quality framework for non-data figures
(`references/prompts/evaluate.md`):

| Layer | Severity | What it checks |
|---|---|---|
| 0: Macro Critique | **block** | Central thesis, spatial allocation, layout metaphor |
| 1: Structural Correctness | **block** | Overlaps, connectors, grouping, rendering |
| 2: Logical Flow | major | Entry point, flow direction, hierarchy |
| 3: Visual Clarity | major | Legibility, contrast, consistency, color, text density |
| 4: Information Completeness | minor | Labels, abbreviations, caption-readiness |

**Layer 0 is the critical addition.** Before checking any detail, the evaluator
asks: *"What argument does this figure make? Does the spatial allocation serve
it? Is this the right layout metaphor?"* If any of these fail, the figure needs
redesign — not patching.

**Preferred when the environment permits:** Launch a subAgent with the rendered
PNG and `references/prompts/evaluate.md`. The subAgent sees the figure fresh
and returns JSON.

**Fallback (requires `AUTOFIGURE_EVAL_API_KEY`):**
Run the VLM visual evaluation on the rendered PNG, providing the SVG and paper
references for context.

Parse the JSON output. Key fields:
- `readability_pass` — if false, one or more Layer 0 or Layer 1 issues exist.
  Fix these BEFORE addressing any other issues.
- `central_thesis` — what argument the evaluator extracted. If this is
  "No clear thesis," the figure has a fundamental design problem. This is
  the most important feedback signal in the entire iteration loop.
- `overall_quality` — drives the loop stop conditions.
- `publication_readiness` — whether the figure looks like it could appear in
  a paper rather than in a slide deck or dashboard.
- `issues[]` — each has `layer` (0-4), `severity` (block/major/minor),
  `where`, and `problem`.

If no subAgent and no VLM: Agent evaluates the rendered PNG manually against
`references/prompts/evaluate.md` and writes the same JSON fields. Do not use a
passing score unless the figure satisfies the publication standard.

### P4. Improve

Feed the evaluation `issues[]` back for refinement. **Critical distinction**:

- **Layer 0 `block` issues**: Require structural redesign.
  - Thesis unclear → rethink what this figure should argue, then rebuild.
  - Spatial allocation wrong → reallocate canvas space, then rebuild.
  - Layout metaphor wrong → choose a different layout, then rebuild.
  - Text-summary/dashboard composition → compress into a stronger visual
    metaphor, then rebuild.
  - **Do NOT patch. Regenerate the SVG from the new design.**
  - Do NOT address Layer 1-4 issues until all Layer 0 issues are resolved.

- **Layer 1 `block` issues**: SVG-level errors (overlaps, misrouted connectors,
  truncated text). Fix directly in the SVG. Max 3 attempts per iteration.

- **`major` issues**: Logical flow problems, poor hierarchy, text density,
  visual inconsistency. Fix in the SVG after all block issues are clear.

- **`minor` issues**: Visual polish — abbreviations, legends, spacing tweaks.
  Fix last, and only if they don't conflict with higher-priority changes.

**When to rebuild vs. patch:**

| Signal | Action |
|---|---|
| Any Layer 0 issue exists | **Rebuild.** Generate a new SVG from a revised design. |
| `central_thesis: "No clear thesis"` | **Rebuild.** The figure has no conceptual foundation. |
| `publication_readiness: "no"` or dashboard/slide composition | **Rebuild.** Reduce text and choose a stronger metaphor. |
| Only Layer 1-4 issues | Patch the existing SVG. |
| Same Layer 0 issue persists after rebuild | The design strategy is wrong — try a fundamentally different approach (e.g., if horizontal flow failed, try vertical; if split-panel failed, try integrated). |

Fix in strict priority: Layer 0 → Layer 1 → major → minor. Track the best
version across iterations.

**Iteration numbering**: Each rebuild counts as an iteration (e.g.,
`iteration_2.svg` from scratch is iteration 2, not iteration 1.1).
Patching within the same design counts toward the same iteration.

**Stop conditions:**
- `readability_pass: true` AND `overall_quality >= 8.0` (configurable via
  `AUTOFIGURE_QUALITY_THRESHOLD`). A passing score with Layer 0 issues
  still present is NOT acceptable — `readability_pass` must be true first.
- For paper-topic figures, `publication_readiness` must not be `no`, and no
  major text-density issue may remain.
- Improvement < 0.2 from previous best
- 5 iterations reached (configurable via `AUTOFIGURE_MAX_ITERATIONS`)
- No VLM and no subAgent: clean structural check plus manual evaluation meeting
  the same readability, publication-readiness, and text-density criteria.

### P5. Caption and Finalize

When the best iteration is selected, always write these final artifacts to the
output directory:

| File | Purpose |
|---|---|
| `figure_final.svg` | Editable final vector figure |
| `figure_final.png` | Rendered preview at target size |
| `figure_caption.md` | Manuscript-style caption |
| `evaluation_report.json` | Iteration history and stop condition |

Caption rules:
- Start with a bold figure title sentence.
- Use one concise paragraph after the title, usually 90-160 words.
- Include what the figure deliberately omits from the artwork: sample sizes,
  assay/method context, the key claim, and the interpretation boundary.
- For paper figures, distinguish association from causation unless the paper
  directly supports a causal claim.
- Do not repeat every visible label. The caption should explain the figure's
  scientific meaning, not narrate its layout.
- Mention important abbreviations that appear in the figure.

Add `final_caption` to `evaluation_report.json` using the same path style as
the other final artifacts.

### P6. Enhance (deprecated)

AI image enhancement of flowcharts and relationship diagrams typically
degrades text legibility and connector accuracy. Image generation models
are optimized for photographic/illustrative output, not for preserving
fine-text and precise line work. **Skip this step.**

## Gotchas

- **AI enhancement destroys text**: Image generation models degrade text
  legibility and connector accuracy on flowcharts. Never use AI enhancement
  on relationship diagrams.
- **Generative models cannot render data**: This skill cannot produce bar
  charts, scatter plots, heatmaps, or any figure whose value depends on
  numerical accuracy of rendered data points. Reject data-figure requests.
- **Dashboard layouts are not paper figures**: The default output must look
  like a journal schematic, not a slide deck. Avoid equal-panel grids, title
  bars, stacked cards, and long explanatory footers.
- **Same-agent evaluation is biased**: An isolated subAgent produces more
  honest critiques than the same agent instance that generated the figure.
  Always prefer subAgent evaluation when available.
- **Layer 0 issues require redesign, not patching**: If the central thesis is
  unclear or the spatial metaphor is wrong, regenerate from scratch. Patching
  a fundamentally broken design wastes iterations.
- **Parse markdown code fences from JSON**: When parsing evaluation JSON
  output, strip markdown code fences before decoding.
- **Text density is the #1 paper-figure rejection reason**: If the evaluator
  flags text density, reduce labels aggressively. Most paper figures need
  far less text than the agent initially assumes.

## Rules

- **Scope**: Reject data figures (charts, plots, heatmaps). This skill only
  draws relationship diagrams: flowcharts, architecture diagrams, conceptual
  schematics, methodology overviews.
- **P2 always includes structural check + render.** Never skip either.
- **P3 uses a subAgent when the environment permits.** An isolated context
  produces more honest critiques than the same Agent instance that generated
  the figure. If subAgents are unavailable, manual evaluation is acceptable but
  must be explicit in `evaluation_report.json`.
- **P3 prompts live in `references/prompts/evaluate.md`.** Edit there, not here.
- **P5 always writes a caption.** Final output is incomplete without
  `figure_caption.md`.
- Handle markdown code fences when parsing JSON from evaluation.
- Keep intermediate files (`iteration_*.svg`, `iteration_*.png`).
- Primary editable output is SVG. Final output also includes PNG, caption, and
  evaluation report. Do not offer mxGraph XML unless requested.