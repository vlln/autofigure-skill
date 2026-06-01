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

*Paper: Exploratory characterization of gut microbiota and cognitive profiles in adolescents with subthreshold depression: a shotgun metagenomics sequencing study*

*DOI: [10.1038/s44184-026-00202-9](https://doi.org/10.1038/s44184-026-00202-9)*

![Generated Chinese scientific schematic](https://github.com/vlln/autofigure-skill/blob/main/example_output/figure_final.png)

> **图 1 | 阈下抑郁青少年肠道微生物组—认知功能关联模型。**
>
>本图呈现了青少年阈下抑郁(SD)中肠道菌群失调、微生物-肠-脑轴功能通路及认知/临床表型三者共现的整体框架。左侧展示研究队列(SD组 n=38, CW组 n=139)及宏基因组测序揭示的显著差异菌群——螺旋体门/纲/目在门、纲、目三级均显著升高，互养菌门和根瘤菌目亦显著升高，伴随β-多样性显著差异。中央的微生物-肠-脑轴通过EggNOG功能分析（胞内运输与囊泡转运负相关于空间广度）和KEGG通路分析（神经退行性疾病与翻译通路在SD组富集）解释菌群如何经代谢中介(GABA、5-HT、多巴胺)影响大脑功能。右侧展示认知与临床表型——空间工作记忆(SD组WMS-III评分高于CW组，可能与青少年期补偿性上调有关)以及C-PHQ-9抑郁评分升高，其余MCCB六维度无显著差异。随机森林分类器以螺旋体门/纲/目为最佳预测因子(AUC=0.76)，根瘤菌目次之(AUC=0.74)，分类准确率74.39%。底部总结线概括三者协同共现关系。图中省略了具体p值、其他无显著差异的菌群类群以及样本量等细节，这些信息详见正文表1和图2-5。关联性不等于因果性——本图呈现的是观察性关联，实验验证仍有待进一步研究。
>
> CW = 临床健康; SD = 阈下抑郁; MCCB = MATRICS认知成套测验; WMS-III = 韦氏记忆量表第3版; C-PHQ-9 = 中文版患者健康问卷-9; RF = 随机森林; EggNOG = 直系同源基因簇数据库; KEGG = 京都基因与基因组百科全书。

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
