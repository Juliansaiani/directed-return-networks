# Directed Return Networks

Daily cryptocurrency lead-lag research using level-two path signatures and directed networks. The global portfolio follows recent leaders through a basket of followers, offset by a hedge across the observable universe.

The recorded sample has 57 assets and runs from 21 August 2019 to 5 November 2023. These are historical research results on a retrospectively selected universe, not an independent holdout or live track record.

| Portfolio | Gross Sharpe | Gross Sharpe, 2% cash-rate assumption | Maximum drawdown |
|---|---:|---:|---:|
| Global lead-lag | 1.41 | 1.34 | -23.21% |

Sharpe uses arithmetic daily mean divided by sample standard deviation, annualized by sqrt(365.25). Gross means no transaction, funding or borrowing costs. The zero-delay convention assumes execution at the same close used to form the signal. Dollar-neutral weights do not establish market-beta neutrality.

![Gross research portfolio values and drawdowns](artifacts/overview.png)

## Execution sensitivity

At 5 bps per traded dollar, the global portfolio's Sharpe falls to 0.14. With one additional day of execution delay, its gross Sharpe is -0.10. Average one-way turnover is about 190% of NAV per day. The historical signal is therefore not evidence of a profitable executable strategy under those assumptions.

All combinations of zero/one additional day and 0/5/10/20 bps costs are in [scores.csv](artifacts/scores.csv). Costs use post-fee target notionals and include initial entry and final liquidation. Funding and borrow availability remain unmodeled, including in the fee scenarios. Missing marks are carried forward for valuation; this does not establish executable prices.

## Method

Each decision uses the latest 30 daily returns, standardized within that window. A level-two signature gives an antisymmetric Lévy-area matrix. Its row means rank assets; the top and bottom 20% are leaders and followers. The sign of the leaders' latest average return determines the direction of the follower-minus-universe portfolio. Eligibility and hedge membership use information observed by the decision date.

## Implementation

The signature calculation is vectorized in NumPy and checked against an independent segment-by-segment recursion. The portfolio ledger tracks drifted holdings, post-fee target notionals and final liquidation. Tests also check signal causality, dollar neutrality and execution timing.

## Run

```bash
git clone https://github.com/julian5422/directed-return-networks.git
cd directed-return-networks
python -m venv .venv
# Activate the environment, then:
python -m pip install -r requirements.txt
python -m pip install -e '.[dev]'
python -m pytest -q
python -m leadlag.research
```

The runner downloads the pinned price CSV and checks its SHA-256. Raw prices remain in an ignored cache. The [executed notebook](notebooks/research.ipynb) presents the global portfolio, subperiods and block-bootstrap intervals. Target weights, daily returns and the run manifest are in `artifacts/`.

Additional comparisons are kept in [experiments/](experiments/README.md). The full runner also rebuilds those comparisons, which takes several minutes.

Implementation/data reference: [ARahimiQuant/lead-lag-portfolios](https://github.com/ARahimiQuant/lead-lag-portfolios), pinned in `config.json`; its MIT notice is retained in [LICENSE](LICENSE). Method references: [Bennett, Cucuringu and Reinert](https://arxiv.org/abs/2201.08283) and [Chevyrev and Kormilitzin](https://arxiv.org/abs/1603.03788). Market-data terms are separate.
