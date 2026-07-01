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

Generate publication-ready scientific SVG figures for non-data content through
iterative refinement (Generate → Evaluate → Improve). Evaluation prompts live
in `references/prompts/`.

## Trigger Keywords

figure, diagram, illustration, schematic, flowchart, architecture diagram,
methodology overview, conceptual diagram, paper figure, publication figure,
journal figure, scientific figure, SVG figure, workflow diagram

## Scope

This skill draws relationship diagrams — information structured as nodes,
connections, flows, and hierarchies.

| Yes (non-data figure) | No (data figure — use dedicated tools) |
|---|---|
| CONSORT participant flow | Bar chart, histogram, box plot |
| Experimental design overview | Scatter plot, PCoA, PCA projection |
| Methodology workflow | Heatmap, correlation matrix |
| System architecture diagram | ROC curve, precision-recall curve |
| Conceptual mechanism / pathway | Line chart, time series |
| Hierarchical taxonomy / ontology | Volcano plot, Manhattan plot |

If a figure's value depends on numerical accuracy of rendered data points, this
skill cannot produce it.

## Publication-Figure Standard

The target is a paper-ready figure, not an explainer slide or dashboard. A
successful figure resembles a concise journal schematic: one strong visual
metaphor, sparse labels, clear flow, and just enough text to make the scientific
claim interpretable with the caption.

Hard design rules:
- **One visual thesis**: encode the paper's central claim as spatial structure
  (e.g., funnel, landscape, circuit, split cohort, gated pipeline, feedback loop).
  Do not merely place study facts in adjacent cards.
- **Low text density**: short labels (1-5 words), at most 8-12 primary text
  blocks on the canvas. No paragraph-like sentences inside boxes. Put nuance in
  the caption.
- **No dashboard layout by default**: avoid equal panels, title bars, stacked
  cards, and long explanatory footers unless the user explicitly asks for a
  slide-style overview.
- **Visual encoding before wording**: show relationships through position,
  arrows, grouping, color, scale, icons, and simple symbolic shapes. Text names
  elements, not explains them.
- **Caption-ready, title-light**: paper figures rarely need a large headline
  inside the artwork. Prefer a compact label or no title.
- **Information triage**: include only the core mechanism/pipeline/claim.
  Secondary methods, caveats, sample sizes, abbreviations, and exact metrics
  should be reduced to tiny annotations or omitted.

## Configuration

All via environment variables. See `.env.example` for the full list.

Minimal setup:
```sh
export AUTOFIGURE_EVAL_API_KEY="sk-or-v1-..."
```

Defaults (override via env):
- `AUTOFIGURE_MAX_ITERATIONS` → 5
- `AUTOFIGURE_QUALITY_THRESHOLD` → 8.0
- `AUTOFIGURE_OUTPUT_DIR` → `./autofigure_output`
- `AUTOFIGURE_RENDER_WIDTH/HEIGHT` → 1333×750

If the output directory already contains files, create a suffixed directory
(e.g., `autofigure_output_1`) unless the user explicitly wants overwrite.

## Pipeline

### Stage 1: Prepare

1. If the user provided a paper (PDF/Markdown), read it and extract the core
   methodology, key findings, and concepts.
2. **Reject data figures before planning.** If the user asks for a bar chart,
   scatter plot, ROC curve, heatmap, line chart, or any figure that depends on
   rendering numerical data, explain the scope limitation and suggest
   alternatives (Python matplotlib/seaborn, R ggplot2, BioRender).
3. For `paper` topic, inspect reference figures from `references/paper/` only
   as style/density examples unless the user asks to reuse them.
4. Produce a **figure brief** before drawing:
   - `claim`: one sentence stating the scientific argument the figure should make.
   - `visual_metaphor`: the spatial metaphor that will carry the claim
     (e.g., gated pipeline, basin/landscape, layered axis, loop, fork-and-merge).
   - `must_show`: 3-5 indispensable elements.
   - `can_omit`: details that belong in the caption or text.
   - `text_budget`: maximum primary labels and maximum words per label.
5. Check configuration. Infer the drawing target from the user's request.
   Ask only if ambiguous:
   - **Drawing target** — what specifically should the figure visualize?
     (e.g., "the proposed MoE routing mechanism in Section 3.2").
   - **Topic** — default `paper` if ambiguous.
   - `AUTOFIGURE_EVAL_API_KEY` — note if missing; VLM evaluation is disabled
     when unset.

**Checkpoint:** Figure brief written and drawing target confirmed. Do not
proceed to generation without a clear claim and visual metaphor.

### Stage 2: Generate

1. **Choose the design strategy** — compare 2-3 candidate visual metaphors in
   one or two sentences each. Select the one that best compresses the central
   claim with the least text. If the best candidate is still a grid of equal
   cards, redesign the concept.
2. **Generate SVG** — produce an SVG figure. Design constraints:
   - Canvas: 1333×750. Clear visual hierarchy, consistent palette, no overlapping
     components.
   - Topic roles: paper=figure designer, survey=visualization expert,
     blog/textbook=educational illustrator.
   - For paper topic, use reference figures as style and density guides.
   - Make the figure look like a manuscript schematic: integrated composition,
     light labels, deliberate whitespace, clear visual path.
   - Prefer symbolic visual elements over text-heavy cards: icons, small
     document glyphs, cohorts, gates, modules, arrows, layered bands, gradients,
     or contours when they carry meaning.
   - Avoid large in-figure titles, paragraph labels, legends that restate the
     whole diagram, and repeated cards with similar text.
3. **Structural check** — run the structural validity check on the SVG.
   If errors, fix the SVG (max 3 attempts) before proceeding.
4. **Render** — `cairosvg {svg} -o {png} -W 1333 -H 750`.
   If rendering fails, treat it as a structural error and go back to step 2.

**Checkpoint:** SVG passes structural check and renders to PNG without errors.

### Stage 3: Evaluate

Evaluation runs in an isolated context so the critique is independent. Use
a 5-layer quality framework (`references/prompts/evaluate.md`):

| Layer | Severity | What it checks |
|---|---|---|
| 0: Macro Critique | **block** | Central thesis, spatial allocation, layout metaphor |
| 1: Structural Correctness | **block** | Overlaps, connectors, grouping, rendering |
| 2: Logical Flow | major | Entry point, flow direction, hierarchy |
| 3: Visual Clarity | major | Legibility, contrast, consistency, color, text density |
| 4: Information Completeness | minor | Labels, abbreviations, caption-readiness |

**Layer 0 is critical.** Before checking any detail, ask: *"What argument does
this figure make? Does the spatial allocation serve it? Is this the right layout
metaphor?"* If any fail, the figure needs redesign — not patching.

**Evaluation procedure** — use the first available method:
1. Launch a subAgent with the rendered PNG and `references/prompts/evaluate.md`.
   The subAgent sees the figure fresh and returns JSON.
2. If subAgents unavailable: run VLM visual evaluation on the rendered PNG
   (requires `AUTOFIGURE_EVAL_API_KEY`), providing the SVG and paper references
   for context.
3. If neither available: evaluate the rendered PNG manually against
   `references/prompts/evaluate.md` and write the same JSON fields.

Parse the JSON output. Key fields:
- `readability_pass` — if false, one or more Layer 0 or Layer 1 issues exist.
  Fix these BEFORE addressing any other issues.
- `central_thesis` — what argument the evaluator extracted. If "No clear thesis,"
  the figure has a fundamental design problem. This is the most important
  feedback signal in the entire iteration loop.
- `overall_quality` — drives the loop stop conditions.
- `publication_readiness` — whether the figure looks like it could appear in a
  paper rather than a slide deck or dashboard.
- `issues[]` — each has `layer` (0-4), `severity` (block/major/minor), `where`,
  and `problem`.

**Checkpoint:** Evaluation JSON produced with all required fields. Do not
proceed to improvement until evaluation is complete.

### Stage 4: Improve

Feed the evaluation `issues[]` back for refinement. Fix in strict priority:
Layer 0 → Layer 1 → major → minor.

**Critical distinction — rebuild vs. patch:**

| Signal | Action |
|---|---|
| Any Layer 0 issue exists | **Rebuild.** Generate a new SVG from a revised design. |
| `central_thesis: "No clear thesis"` | **Rebuild.** The figure has no conceptual foundation. |
| `publication_readiness: "no"` or dashboard/slide composition | **Rebuild.** Reduce text and choose a stronger metaphor. |
| Only Layer 1-4 issues | Patch the existing SVG. |
| Same Layer 0 issue persists after rebuild | The design strategy is wrong — try a fundamentally different approach (e.g., if horizontal flow failed, try vertical; if split-panel failed, try integrated). |

**Layer 0 block issues require structural redesign:**
- Thesis unclear → rethink what this figure should argue, then rebuild.
- Spatial allocation wrong → reallocate canvas space, then rebuild.
- Layout metaphor wrong → choose a different layout, then rebuild.
- Text-summary/dashboard composition → compress into a stronger visual metaphor,
  then rebuild.
- Do NOT patch Layer 0 issues. Regenerate the SVG from the new design.
- Do NOT address Layer 1-4 issues until all Layer 0 issues are resolved.

**Layer 1 block issues**: SVG-level errors (overlaps, misrouted connectors,
truncated text). Fix directly in the SVG. Max 3 attempts per iteration.

**Major issues**: Logical flow, hierarchy, text density, visual inconsistency.
Fix in the SVG after all block issues are clear.

**Minor issues**: Visual polish — abbreviations, legends, spacing tweaks.
Fix last, and only if they don't conflict with higher-priority changes.

**Iteration numbering**: Each rebuild counts as an iteration (e.g.,
`iteration_2.svg` from scratch is iteration 2). Patching within the same design
counts toward the same iteration.

Track the best version across iterations.

**Stop conditions:**
- `readability_pass: true` AND `overall_quality >= AUTOFIGURE_QUALITY_THRESHOLD`
  (default 8.0). A passing score with Layer 0 issues still present is NOT
  acceptable.
- For paper-topic figures, `publication_readiness` must not be `no`, and no
  major text-density issue may remain.
- Improvement < 0.2 from previous best.
- `AUTOFIGURE_MAX_ITERATIONS` reached (default 5).
- No VLM and no subAgent: clean structural check plus manual evaluation meeting
  the same readability, publication-readiness, and text-density criteria.

**Checkpoint:** Stop conditions met or max iterations reached. If stopping due
to max iterations, note the best version and remaining issues.

### Stage 5: Finalize

Write these final artifacts to the output directory:

| File | Purpose |
|---|---|
| `figure_final.svg` | Editable final vector figure |
| `figure_final.png` | Rendered preview at target size |
| `figure_caption.md` | Manuscript-style caption |
| `evaluation_report.json` | Iteration history and stop condition |

Caption rules:
- Start with a bold figure title sentence.
- One concise paragraph after the title, usually 90-160 words.
- Include what the figure deliberately omits from the artwork: sample sizes,
  assay/method context, the key claim, and the interpretation boundary.
- For paper figures, distinguish association from causation unless the paper
  directly supports a causal claim.
- Do not repeat every visible label. The caption should explain the figure's
  scientific meaning, not narrate its layout.
- Mention important abbreviations that appear in the figure.

Add `final_caption` to `evaluation_report.json`.

**Checkpoint:** All four artifacts written to the output directory. Keep
intermediate files (`iteration_*.svg`, `iteration_*.png`). Primary editable
output is SVG. Do not offer mxGraph XML unless requested.

## Gotchas

- **AI enhancement destroys text**: Image generation models degrade text
  legibility and connector accuracy on flowcharts. Never use AI enhancement
  on relationship diagrams. Skip enhancement entirely.
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
- **Text density is the #1 paper-figure rejection reason**: If the evaluator
  flags text density, reduce labels aggressively. Most paper figures need
  far less text than the agent initially assumes.

## Checklist

- [ ] Reject data-figure requests before planning
- [ ] Figure brief written with claim, visual metaphor, must_show, can_omit, text_budget
- [ ] SVG passes structural check and renders to PNG
- [ ] Evaluation JSON produced with all required fields (readability_pass, central_thesis, overall_quality, publication_readiness, issues[])
- [ ] Layer 0 issues resolved by redesign (not patches) before addressing lower layers
- [ ] Stop conditions met (readability_pass + quality threshold, or max iterations)
- [ ] All four final artifacts written (figure_final.svg, figure_final.png, figure_caption.md, evaluation_report.json)
- [ ] Caption written per manuscript-style rules