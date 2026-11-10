# Additional experiments

The main study presents the global lead-lag portfolio. The spectral-clustering comparison remains here as an exploratory extension, rather than a second headline strategy.

| Historical gross result | Sharpe (zero cash rate) | Sharpe (2% cash-rate assumption) | Maximum drawdown |
|---|---:|---:|---:|
| Global portfolio | 1.41 | 1.34 | -23.21% |
| Absolute-degree spectral variant | 0.22 | 0.15 | -40.95% |

The spectral variant did not improve this sample. Its normalization uses absolute degrees to preserve Hermitian symmetry. The original signed complex-degree normalization and the change made here are documented in the [experiment notebook](../notebooks/experiments.ipynb) and [audit](../artifacts/upstream_audit.json).

The [full scores](../artifacts/scores.csv), [daily returns](../artifacts/daily.csv) and target files preserve all variants and fee/delay scenarios. No performance values were changed when the presentation was reorganized. Gross returns exclude fees, funding and borrowing costs; zero-delay cases assume idealized same-close execution.

The original convention comparison is preserved in [upstream_reproduction.csv](../artifacts/upstream_reproduction.csv). Implementation and data provenance remain recorded in the notebook, `config.json` and `LICENSE`.
