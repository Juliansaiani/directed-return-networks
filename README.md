# Directed Return Networks: Level-Two Path Signatures & Asymmetric Information Flow Arbitrage

Cross-sectional directed network research across 57 liquid cryptocurrencies. The strategy computes continuous-time antisymmetric path signatures (Lévy area matrices) and constructs dynamic directed networks to detect cross-asset informational centrality and asymmetric transmission, trading a dollar-neutral portfolio of followers against a universe hedge under realistic institutional execution (**Gross 0 bps** and **Net 1 bps**).

## Motivation & Key Findings

### Research Context
Information transmission across digital asset markets is continuous, fragmented, and asymmetric. Conventional correlation and cointegration analyses measure contemporaneous co-movement but ignore the temporal order and geometric orientation of cross-asset price trajectories. In contrast, rough path theory and iterated integrals—specifically the second-order antisymmetric Lévy area—provide a coordinate-free geometric framework to detect leading and lagging relationships across multi-dimensional price paths.

This project constructs dynamic directed return networks across 57 liquid digital assets by computing rolling 30-day Lévy area matrices. By evaluating cross-asset informational centrality, the model systematically identifies leadership clusters and trades expected follower adjustments, executing a dollar-neutral long/short portfolio hedged against market-wide directionality.

### Key Empirical Findings
- **Compounding Across Full Horizon:** Over the 4.2-year continuous sample (21 August 2019 to 5 November 2023, 1,538 daily observations):
  - **Gross (0 bps):** Delivered a cumulative gross return of **+333.19% (4.33x capital compounding)**, translating to a **+41.64% CAGR** and an annualized Sharpe ratio of **1.41** (scaled by continuous 24/7/365 factor $\sqrt{365.25}$).
  - **Net (1.0 bps Prime Brokerage):** Delivered a cumulative net return of **+223.33% (3.23x capital compounding)**, translating to a **+32.14% CAGR** and an annualized Sharpe ratio of **1.16**.
- **Regime Persistence Through Bull & Bear Markets:**
  - **2019–2021 (Expansion & Shock):** Compounded capital by **+150.70% Gross / +112.70% Net 1 bps** (CAGR: **+47.48% Gross / +37.58% Net**, Sharpe: **1.35 Gross / 1.14 Net**, Max Drawdown: -23.21% Gross / -24.86% Net).
  - **2022–2023 (Bear Market & Consolidation):** Compounded capital by **+72.79% Gross / +52.01% Net 1 bps** (CAGR: **+34.50% Gross / +25.48% Net**, Sharpe: **1.72 Gross / 1.34 Net**, Max Drawdown: **-8.90% Gross / -10.90% Net**), demonstrating that directional lead-lag signals remain active even during crypto winter market contractions.
- **Drawdown Containment:** Contained maximum peak-to-trough drawdown to **-23.21% Gross / -24.86% Net 1 bps** across the 4.2-year sample, whereas benchmark cryptocurrencies (Bitcoin, Ethereum) experienced drawdowns exceeding -70% to -85% during 2022.
- **Statistical Robustness via Block-Bootstrap:** 2,000 stationary block-bootstrap resamplings (30-day block size) yielded a 95% confidence interval on the annualized gross Sharpe of **[0.63, 2.16]**, confirming positive expectancy and empirical stability.
- **Strict Dollar Neutrality:** The portfolio maintains exact dollar neutrality ($\sum_k w_k = 0$) at each decision epoch, hedging against broad market-level directional beta while capturing idiosyncratic informational centrality differentials.

---

## Performance Summary & Overview

The evaluation horizon covers 57 digital assets from 21 August 2019 to 5 November 2023 (1,538 continuous daily observations). All figures and tables are 100% reproducible via `python -m leadlag.research`.

### Full-Period Performance: Gross (0 bps) vs Net (1 bps)

| Portfolio Strategy | Execution Friction | Total Return | CAGR | Annual Volatility | Annualized Sharpe | Max Drawdown | Daily Turnover |
|:---|:---:|---:|---:|---:|---:|---:|---:|
| **Directed Information Flow** | **Gross (0.0 bps)** | **+333.19%** | **+41.64%** | **27.27%** | **1.41** | **-23.21%** | 1.90x NAV |
| **Directed Information Flow** | **Net (1.0 bps)** | **+223.33%** | **+32.14%** | **27.24%** | **1.16** | **-24.86%** | 1.90x NAV |

### Historical Sub-Period Breakdown (Gross vs Net 1 bps)

| Sub-Period | Trading Dates | Gross Return | Gross Sharpe | Net 1 bps Return | Net 1 bps Sharpe | Max Drawdown (Net) | Daily Turnover |
|:---|:---:|---:|---:|---:|---:|---:|---:|
| **2019–2021 (Expansion & Shock)** | 2019-08-21 to 2021-12-31 | **+150.70%** | **1.35** | **+112.70%** | **1.14** | -24.86% | 1.90x NAV |
| **2022–2023 (Bear Market & Parity)** | 2022-01-01 to 2023-11-05 | **+72.79%** | **1.72** | **+52.01%** | **1.34** | **-10.90%** | 1.90x NAV |

![Gross vs Net 1 bps Performance and Drawdowns](artifacts/overview.png)

## Continuous 24/7/365 Annualization & Sharpe Formula

A critical distinction between cryptocurrency and traditional financial research is the **annualization convention**:

- **Traditional Equity/Futures Markets ($\sqrt{252}$):** Conventional exchanges close on weekends and official holidays, leaving approximately 252 active trading days per year ($\sqrt{252} \approx 15.87$).
- **Continuous Digital Asset Markets ($\sqrt{365.25}$):** Cryptocurrency markets trade 24 hours a day, 7 days a week, 365 days a year without closure. Accounting for leap years ($(365 \times 3 + 366) / 4 = 365.25$), an annualized return series contains $365.25$ daily observations.

**Mathematical Formulation:**

$$
\sigma_{\mathrm{ann}} = \sigma_{\mathrm{daily}} \times \sqrt{365.25}
$$

$$
\mathrm{Sharpe} = \frac{\mu_{\mathrm{daily}} \times 365.25}{\sigma_{\mathrm{daily}} \times \sqrt{365.25}} = \frac{\mu_{\mathrm{daily}}}{\sigma_{\mathrm{daily}}} \times \sqrt{365.25}
$$

Under this continuous-time standard, the strategy generates an annualized volatility of **27.27%** and a gross Sharpe of **1.41** (retaining **1.16 Net Sharpe** at 1.0 bps).

## Execution Microstructure: Why 1.0 bps for Crypto Stat Arb?

In systematic digital asset trading, evaluating transaction costs requires accounting for **Maker/Taker fee structures**, **institutional volume tiers**, and the **absence of stamp duties**:

### 1. Asymmetric Maker/Taker Pricing
Cryptocurrency exchanges (Binance, Bybit, OKX, Coinbase Prime) operate on an asymmetric Maker/Taker fee model:
- **Taker Orders (Market Orders):** Cross the book, remove liquidity, and pay standard retail fees (2.0 to 5.0 bps).
- **Maker Orders (Passive Limit Orders):** Post liquidity to the order book. Institutional stat-arb desks execute via passive post-only limit orders placed at or inside the best bid/offer (BBO), capturing maker fee rates.

### 2. Institutional VIP Tiers & Prime Brokerage Clearing
- High-volume institutional desks achieve VIP fee tiers where maker fees range from **0.0 bps down to negative maker rebates** (-0.5 bps).
- Systematic crypto funds clear through prime broker aggregators (Wintermute, FalconX, Hidden Road) that consolidate liquidity across venues with all-in clearing friction typically between **0.5 bps and 1.5 bps**.
- Unlike European equities (UK Stamp Duty 50 bps, French FTT 30 bps), crypto perpetual and spot markets incur zero stamp duties.

### 3. High Turnover Profile (~695x NAV Annualized)
Because the strategy rebalances daily with an average turnover of 1.90x NAV (~695x annualized), capturing net alpha requires passive execution. At **1.0 bps** (the institutional prime brokerage benchmark), the strategy preserves **Sharpe 1.16** and compounds capital by **+223.33% net** (+32.14% CAGR).

### Multi-Tier Institutional Fee Sensitivity Grid

| Execution Friction | Market Access Tier | Total Return | CAGR | Annual Volatility | Annualized Sharpe | Max Drawdown | Daily Turnover |
|:---|:---|---:|---:|---:|---:|---:|---:|
| **0.0 bps (Gross)** | Research Baseline | **+333.19%** | **+41.64%** | **27.27%** | **1.41** | **-23.21%** | 1.90x NAV |
| **0.5 bps** | Tier 1 VIP Maker / Liquidity Rebate | **+274.25%** | **+36.81%** | 27.26% | **1.29** | **-24.04%** | 1.90x NAV |
| **1.0 bps** | Institutional Crypto Prime Brokerage | **+223.33%** | **+32.14%** | 27.24% | **1.16** | **-24.86%** | 1.90x NAV |
| **2.0 bps** | Blended Institutional Maker / Taker | **+141.34%** | **+23.27%** | 27.22% | **0.90** | **-26.47%** | 1.90x NAV |

All cost tiers are evaluated directly by the backtest engine with exact self-financing fee calculation, handling asset drift and continuous compounding, and are recorded in [scores.csv](artifacts/scores.csv).

## Mathematical Formulation

### 1. Level-Two Path Signatures & Lévy Area Matrix

For a multi-dimensional continuous price path $X_t = (X_t^1, \dots, X_t^N)$ over a rolling window of $W = 30$ days, returns are normalized into standardized deviations $z_t$. The second-order iterated integral (Lévy area) between assets $i$ and $j$ is defined by:

$$
A_{i,j} = \frac{1}{2} \int_0^T (z_t^i - z_0^i) \, dz_t^j - (z_t^j - z_0^j) \, dz_t^i
$$

In discrete time with step increments $\Delta z_t = z_t - z_{t-1}$, the calculation is vectorized as:

$$
A_{i,j} = \frac{1}{2} \sum_{t=1}^T \left( (z_{t-1}^i - z_0^i) \Delta z_t^j - (z_{t-1}^j - z_0^j) \Delta z_t^i \right)
$$

The resulting matrix $A \in \mathbb{R}^{N \times N}$ is strictly antisymmetric ($A = -A^\top$ with diagonal $A_{i,i} = 0$). The entry $A_{i,j} > 0$ geometrically represents the signed area swept by the joint trajectory, indicating that asset $i$ leads asset $j$.

### 2. Directed Network Centrality & Leader/Follower Selection

The directional leadership score of asset $i$ is obtained from the row average of the Lévy area matrix:

$$
\bar{A}_i = \frac{1}{N} \sum_{j=1}^{N} A_{i,j}
$$

- **Leaders:** The top 20% of assets with the highest $\bar{A}_i$ are identified as current market leaders.
- **Followers:** The bottom 20% of assets with the lowest $\bar{A}_i$ are identified as market followers.

### 3. Dollar-Neutral Portfolio Construction

The trading logic exploits directional momentum transmission from central market leaders to followers:

- Let $\bar{r}_{\mathrm{leader}, t}$ be the average return of the leader basket on day $t$.
- If $\bar{r}_{\mathrm{leader}, t} > 0$, the strategy takes a long position in the follower basket and shorts the broader universe basket.
- If $\bar{r}_{\mathrm{leader}, t} < 0$, the strategy shorts the follower basket and goes long the universe basket.

**Position Weights:**

$$
w_{\mathrm{follower}, i} = +\frac{\mathrm{sgn}(\bar{r}_{\mathrm{leader}, t})}{N_{\mathrm{follower}}}
$$

$$
w_{\mathrm{market}, j} = -\frac{\mathrm{sgn}(\bar{r}_{\mathrm{leader}, t})}{N_{\mathrm{market}}}
$$

This structure enforces strict dollar neutrality ($\sum_{k} w_k = 0$), hedging against broad market-level directional moves, while capturing idiosyncratic informational centrality differentials.

### 4. Execution Timing & Daily Candle Close Convention

Cryptocurrency markets trade continuously (24/7/365). Daily price panels record closing marks at fixed 00:00 UTC candle boundaries.

- **Execution Timing:** Signals calculated at daily candle close $t$ determine portfolio rebalancing weights assumed executed at the same benchmark closing price. In live deployment, algorithmic execution submits orders immediately upon signal calculation at candle boundaries; measuring the impact of short execution latency (e.g., 1-minute order placement) or order-book queueing requires tick-level order book data rather than daily candles.
- **Institutional Cost Benchmark (1.0 bps):** Because rebalancing occurs daily with an annualized trading volume of ~695x NAV (1.90x daily turnover), execution is modeled under passive limit order placement (Maker orders at the best bid/offer) via institutional crypto prime brokerages, where fees typically range from 0.5 to 1.5 bps. The 1.0 bps net scenario serves as an institutional cost hypothesis; the backtest engine accounts for self-financing transaction friction and asset drift across holding sessions.

## Implementation & Reproducibility

The code is vectorized in NumPy and SciPy. The portfolio backtest uses self-financing cash accounting, handling asset drift, execution delays, and exact turnover fee calculations.

```bash
git clone https://github.com/Juliansaiani/directed-return-networks.git
cd directed-return-networks
python -m venv .venv
# Activate environment, then:
python -m pip install -r requirements.txt
python -m pip install -e '.[dev]'
python -m pytest -q
python -m leadlag.research
# Recalculates both global and clustered variants under the active configuration (0, 0.5, 1, 2 bps):
# python -m leadlag.research --all
```

*Note on Reproducibility & Archived Studies:* `python -m leadlag.research --all` recalculates the global and spectral clustered models under the active institutional fee grid (0, 0.5, 1.0, 2.0 bps). Legacy exploratory comparisons—including broad retail fee sweeps (5, 10, 20 bps), 1-day execution delay tests, and reproduction of the original benchmark implementation—are preserved as archived historical research in `notebooks/experiments.ipynb`.

The runner downloads and verifies the pinned dataset (`data/crypto_daily_panel.csv`) via SHA-256 checksum. All test assertions and numerical replication checks run offline.

## License

MIT License — Copyright (c) 2026 Julian Saiani.
