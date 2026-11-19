# Additional experiments

The main study presents the active `2021–2023` global directed return network portfolio (`1,095` days, annualized arithmetic Sharpe **1.63 Gross / 1.38 Net 1 bp**). This archive preserves the legacy pre-extension baseline (`2019-08-23` to `2023-11-05`, `1,536` days, CAGR-based Sharpe convention) together with the exploratory spectral-clustering extension:

| Legacy pre-extension gross result (`2019-08-23` – `2023-11-05`) | Legacy Sharpe (zero cash rate) | Legacy Sharpe (2% cash-rate assumption) | Maximum drawdown |
|---|---:|---:|---:|
| Global portfolio (`upstream_gp` legacy convention) | 1.41 | 1.34 | -23.21% |
| Absolute-degree spectral variant | 0.22 | 0.15 | -40.95% |

On the recomputed pre-extension `upstream_gp` sample in [upstream_reproduction.csv](../artifacts/upstream_reproduction.csv), the CAGR-based Sharpe evaluates to `1.43` (`1.32` conventional arithmetic Sharpe) vs. `-23.22%` max drawdown, distinct from the active `2021–2023` global headline metrics in the root [README.md](../README.md). The spectral variant did not improve this sample; its normalization uses absolute degrees to preserve Hermitian symmetry, while the signed complex-degree normalization comparison and the changes made here are documented in the [experiment notebook](../notebooks/experiments.ipynb) and [audit](../artifacts/upstream_audit.json).

The [full scores](../artifacts/scores.csv), [daily returns](../artifacts/daily.csv) and target files preserve all variants and fee/delay scenarios. Gross returns exclude fees, funding and borrowing costs; zero-delay cases assume daily close-mark execution.

Implementation and data provenance remain recorded in the notebooks, `config.json` and `LICENSE`.
