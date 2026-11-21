# Figure Quality Audit

Audit performed on the final 48-page compiled PDF at 160% equivalent raster scale. Preview images are stored under `figure_previews/`.

| File | Label / page | Icons | Routed arrows | Arrow/text overlap | Text overlap | Labels | Color grammar | Grayscale | Caption | PNG inspected | Fixes applied | Final |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `figures/tikz_architecture.tex` | `fig:architecture`, p. 5 | yes | yes | none | none | readable; legend present | consistent | shapes/patterns + line styles | informative | `page_05_fig_01.png` | removed congested edge labels and rerouted recovery control | Pass |
| `figures/tikz_threat_privacy_robustness.tex` | `fig:threat`, p. 13 | yes | yes | none | none | induced-action label has white background | consistent | honest/attack shapes and pattern | informative | `page_13_fig_02.png` | curved adaptive path; changed memory/LoRA control to vertical anchors | Pass |
| `figures/tikz_method_pipeline.tex` | `fig:pipeline`, p. 16 | stage icons | yes | none | none | numbered stages readable | consistent | shapes and dashed attack flow | informative | `page_16_fig_03.png` | removed labels that collided with feedback routes | Pass |
| `figures/tikz_theory_diagram.tex` | `fig:theory`, p. 22 | semantic node shapes | yes | none | none | n/a | purple theory / green consequence | double borders and grouping | informative | `page_22_fig_04.png` | no final correction required | Pass |
| `figures/tikz_experimental_setup.tex` | `fig:experimental-setup`, p. 29 | semantic node shapes | yes | none | none | concise | consistent | attack pattern and shapes | informative | `page_29_fig_05.png` | scaled to text width; result table also constrained | Pass |
| `figures/pgfplots_placeholder_results.tex` | `fig:placeholder-trends`, p. 30 | n/a | n/a | none | none | legends readable | consistent | markers and line styles | explicitly conceptual | `page_30_fig_06.png` | verified placeholder warning in caption and plot context | Pass |

No figure is cropped. No arrow crosses text, equations, or icons. Nodes do not overlap. All multi-flow figures use color plus dash/pattern/shape cues. The conceptual plots remain intentionally non-empirical and must be replaced after real experiments.
