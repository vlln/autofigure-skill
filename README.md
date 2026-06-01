# autofigure-skill

`autofigure-skill` provides an Agent Skill for generating publication-ready
scientific SVG schematics from papers, markdown, or short figure briefs.

The skill focuses on non-data figures: methodology diagrams, conceptual
schematics, architecture diagrams, flowcharts, CONSORT-like flows, and manuscript
overview figures. It is not intended for numerical charts such as bar plots,
scatter plots, ROC curves, heatmaps, PCA/PCoA plots, volcano plots, or any figure
whose value depends on faithfully rendering data points.

## Skill

| Skill | Description |
|---|---|
| [`autofigure`](https://github.com/vlln/autofigure-skill/tree/main/skills/autofigure) | Generates publication-style SVG figures through an iterative Generate -> Check -> Render -> Evaluate -> Improve workflow. |

## Output

A completed run produces an editable figure bundle:

| Artifact | Purpose |
|---|---|
| `figure_final.svg` | Final editable vector figure |
| `figure_final.png` | Rendered preview |
| `figure_caption.md` | Manuscript-style caption |
| `evaluation_report.json` | Figure brief, design rationale, checks, and evaluation summary |
| `iteration_*.svg` / `iteration_*.png` | Intermediate versions for review |

## Example

The example below was generated from a biomedical paper about gut microbiota,
cognition, and subthreshold depression in adolescents. The figure and caption
language is Simplified Chinese.

![Generated Chinese scientific schematic](https://github.com/vlln/autofigure-skill/blob/main/example_output/figure_final.png)

## Design Principles

- One visual thesis per figure.
- Sparse labels, with scientific nuance moved into the caption.
- Visual structure first: position, arrows, grouping, scale, and color should
  carry the main argument.
- Manuscript schematic style rather than dashboard, slide, or infographic style.
- Clear distinction between association and causation when the source evidence
  is observational.
- No fabricated numerical charts.

## License

MIT
