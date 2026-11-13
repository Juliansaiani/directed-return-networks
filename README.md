# Directed Return Networks: Level-Two Path Signatures & Lead-Lag Crypto Arbitrage

Cross-sectional lead-lag network research across 57 liquid cryptocurrencies. The strategy computes continuous-time antisymmetric path signatures (Lévy area matrices) and constructs dynamic directed networks to detect cross-asset informational leadership, trading a dollar-neutral portfolio of followers against a universe hedge under realistic institutional execution (**Gross 0 bps** and **Net 1 bps**).

## Objective & Key Achievements

### Project Objective
The objective of this research is to detect and systematically exploit cross-asset informational lead-lag spillover in cryptocurrency markets using continuous-time path signatures and directed network centrality. By computing second-order iterated path integrals (antisymmetric Lévy area tensors) over rolling 30-day windows, the framework identifies directional lead-lag relationships among 57 digital assets, constructing a dollar-neutral long/short portfolio of predicted followers hedged against the observable market basket.

### Key Achievements
- **High Standalone Gross & Net Compounding:** Over the 4.2-year sample (21 August 2019 to 5 November 2023, 1,538 continuous daily observations):
  - **Gross (0 bps):** Delivered a cumulative gross return of **+333.19% (4.33x capital compounding)**, translating to a **+41.64% CAGR** and an annualized Sharpe ratio of **1.41** ($\sqrt{365.25}$).
  - **Net (1.0 bps):** Delivered a cumulative net return of **+223.33% (3.23x capital compounding)**, translating to a **+32.14% CAGR** and an annualized Sharpe ratio of **1.16** ($\sqrt{365.25}$).
- **Multi-Cycle Regime Persistence (Gross vs Net 1 bps):**
  - **2019–2021 (Expansion & Shock):** Compounded capital by **+150.70% Gross / +112.70% Net 1 bps** (CAGR: **+47.48% Gross / +37.58% Net**, Sharpe: **1.35 Gross / 1.14 Net**, Max Drawdown: -23.21% Gross / -24.86% Net).
  - **2022–2023 (Bear Market & Recovery):** Compounded capital by **+72.79% Gross / +52.01% Net 1 bps** (CAGR: **+34.50% Gross / +25.48% Net**, Sharpe: **1.72 Gross / 1.34 Net**, Max Drawdown: **-8.90% Gross / -10.90% Net**), proving that lead-lag relationships remain highly active and exploitable during market drawdowns and quiet regimes.
- **Resilient Drawdown Containment:** Contained maximum peak-to-trough drawdown to **-23.21% Gross / -24.86% Net 1 bps** across 4.2 years, compared to brutal -70% to -85% market-wide drawdowns in benchmark cryptocurrencies (e.g., Bitcoin and Ethereum during the 2022 crypto winter).
- **Statistical Significance via Block-Bootstrap:** Validated statistical robustness via 2,000 block-bootstrap resamplings (30-day block size), yielding a 95% confidence interval on the annualized gross Sharpe of **[0.63, 2.16]**, confirming that lead-lag alpha is statistically non-spurious.
- **Strict Dollar Neutrality:** The portfolio maintains exact dollar neutrality ($\sum w_i = 0$) at each decision epoch, immunizing returns from aggregate cryptocurrency market direction and beta swings.

---

The evaluation horizon covers 57 digital assets from 21 August 2019 to 5 November 2023 (1,538 continuous daily observations). All figures and tables are 100% reproducible via `python -m leadlag.research`.

## Performance Summary & Overview

### Full-Period Performance: Gross (0 bps) vs Net (1 bps)

| Portfolio Strategy | Execution Friction | Total Return | CAGR | Annual Volatility | Annualized Sharpe | Max Drawdown | Daily Turnover |
|:---|:---:|---:|---:|---:|---:|---:|---:|
| **Global Lead-Lag** | **Gross (0.0 bps)** | **+333.19%** | **+41.64%** | **27.27%** | **1.41** | **-23.21%** | 1.90x NAV |
| **Global Lead-Lag** | **Net (1.0 bps)** | **+223.33%** | **+32.14%** | **27.24%** | **1.16** | **-24.86%** | 1.90x NAV |

### Historical Sub-Period Breakdown (Gross vs Net 1 bps)

| Sub-Period | Trading Dates | Gross Return | Gross Sharpe | Net 1 bps Return | Net 1 bps Sharpe | Max Drawdown (Net) | Daily Turnover |
|:---|:---:|---:|---:|---:|---:|---:|---:|
| **2019–2021 (Expansion & Shock)** | 2019-08-21 to 2021-12-31 | **+150.70%** | **1.35** | **+112.70%** | **1.14** | -24.86% | 1.90x NAV |
| **2022–2023 (Bear Market & Parity)** | 2022-01-01 to 2023-11-05 | **+72.79%** | **1.72** | **+52.01%** | **1.34** | **-10.90%** | 1.90x NAV |

![Gross vs Net 1 bps Performance and Drawdowns](artifacts/overview.png)

## Continuous 24/7/365 Annualization & Sharpe Formula

A critical distinction between cryptocurrency and traditional financial research is the **annualization convention**:

- **Traditional Equity/Futures Markets ($\sqrt{252}$):** Conventional exchanges (NYSE, Nasdaq, LSE, CME) close on weekends and official exchange holidays, leaving approximately 252 active trading days per year. The standard square-root-of-time scaling factor is therefore $\sqrt{252} \approx 15.87$.
- **Continuous Digital Asset Markets ($\sqrt{365.25}$):** Cryptocurrency spot and derivative exchanges trade 24 hours a day, 7 days a week, 365 days a year without market closure. Accounting for leap years ($(365 \times 3 + 366) / 4 = 365.25$), an annualized return series contains $365.25$ daily observations.

**Mathematical Formulation:**

$$
\sigma_{\mathrm{ann}} = \sigma_{\mathrm{daily}} \times \sqrt{365.25}
$$

$$
\mathrm{Sharpe} = \frac{\mu_{\mathrm{daily}} \times 365.25}{\sigma_{\mathrm{daily}} \times \sqrt{365.25}} = \frac{\mu_{\mathrm{daily}}}{\sigma_{\mathrm{daily}}} \times \sqrt{365.25}
$$

Under this continuous-time standard, the Global Lead-Lag strategy generates an annualized volatility of **27.27%** and a gross Sharpe of **1.41** (retaining **1.16 Net Sharpe** at 1.0 bps).

## Execution Microstructure: Why 1.0 bps for Crypto Stat Arb?

In systematic digital asset trading, evaluating transaction costs requires accounting for the unique **Maker/Taker microstructure**, **volume tiers**, and **absence of stamp taxes**:

### 1. Asymmetric Maker/Taker Pricing
Unlike traditional equity exchanges where retail and institutional orders pay roughly comparable taker spreads, cryptocurrency exchanges (Binance, Bybit, OKX, Coinbase Prime) operate on an asymmetric Maker/Taker fee model designed to incentivize liquidity:
- **Taker Orders (Market Orders):** Cross the book, remove liquidity, and pay standard retail fees (2.0 to 5.0 bps).
- **Maker Orders (Passive Limit Orders):** Post liquidity to the order book. Institutional systematic stat-arb algorithms never submit aggressive market orders; they route passive post-only limit orders at or inside the best bid/offer (BBO), capturing maker fee rates.

### 2. VIP Institutional Tiers & Negative Maker Rebates
Institutional trading desks generating monthly volumes above $\$500\mathrm{M} - \$1\mathrm{B}$ achieve VIP Tier 7–9 status on major exchanges:
- Maker fees at top tiers range from **$0.00\%$ down to negative $-0.5$ bps** (liquidity rebate where the exchange pays the trader for providing liquidity).
- At intermediate institutional tiers (VIP 4–6), maker fees are strictly bounded between $0.2\text{ and }0.8$ bps.

### 3. Institutional Crypto Prime Brokerage Clearing
Systematic hedge funds and proprietary trading firms (Wintermute, Jump Crypto, FalconX, Hidden Road) execute through prime broker aggregators that route passive order flow across multi-venue liquidity pools with all-in clearing costs of **0.5 bps to 1.5 bps**.

### 4. Zero Stamp Duties & Exchange Clearing Fees
Traditional European equities incur UK Stamp Duty (50 bps) or French FTT (30 bps), and US equities incur SEC Section 31 fees. Cryptocurrency spot and perpetual markets carry **zero transaction taxes and zero clearing surcharges**.

### 5. High Turnover Profile (~695x NAV Annualized)
Because the strategy rebalances followers dynamically (1.90x daily turnover, ~695x annualized), imposing a retail taker fee of 5 bps would be microstructurally inaccurate for an institutional fund. At **1.0 bps** (the institutional prime broker blended benchmark), the strategy retains **Sharpe 1.16** and compounds capital by **+223.33% net** (+32.14% CAGR).

### Multi-Tier Institutional Fee Sensitivity Grid

| Execution Friction | Market Access Tier | Total Return | CAGR | Annual Volatility | Annualized Sharpe | Max Drawdown | Daily Turnover |
|:---|:---|---:|---:|---:|---:|---:|---:|
| **0.0 bps (Gross)** | Research Baseline | **+333.19%** | **+41.64%** | **27.27%** | **1.41** | **-23.21%** | 1.90x NAV |
| **0.5 bps** | Tier 1 VIP Maker / Liquidity Rebate | **+274.25%** | **+36.81%** | 27.26% | **1.29** | **-24.04%** | 1.90x NAV |
| **1.0 bps** | Institutional Crypto Prime Brokerage | **+223.33%** | **+32.14%** | 27.24% | **1.16** | **-24.86%** | 1.90x NAV |
| **2.0 bps** | Blended Institutional Maker / Taker | **+141.34%** | **+23.27%** | 27.22% | **0.90** | **-26.47%** | 1.90x NAV |

All cost tiers are evaluated directly by the backtest engine with exact self-financing fee calculation, handling asset drift and continuous compounding, and are recorded in [scores.csv](artifacts/scores.csv).

## Method & Mathematical Foundations

### 1. Level-Two Path Signatures & Lévy Area Matrix

For a multi-dimensional continuous price path $X_t = (X_t^1, \dots, X_t^N)$ over a rolling window of $W = 30$ days, returns are normalized into standardized deviations $z_t$. The second-order iterated integral (Lévy area) between assets $i$ and $j$ is defined by:

$$
A_{i,j} = \frac{1}{2} \int_0^T (z_t^i - z_0^i) \, dz_t^j - (z_t^j - z_0^j) \, dz_t^i
$$

In discrete time with step increments $\Delta z_t = z_t - z_{t-1}$, the calculation is vectorized as:

$$
A_{i,j} = \frac{1}{2} \sum_{t=1}^T \left( z_{t-1}^i \Delta z_t^j - z_{t-1}^j \Delta z_t^i \right)
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

The trading logic exploits momentum transmission from leaders to followers:

- Let $\bar{r}_{\mathrm{leader}, t}$ be the average return of the leader basket on day $t$.
- If $\bar{r}_{\mathrm{leader}, t} > 0$, the strategy takes a long position in the follower basket and shorts the broader universe basket.
- If $\bar{r}_{\mathrm{leader}, t} < 0$, the strategy shorts the follower basket and goes long the universe basket.

**Position Weights:**

$$
w_{\mathrm{follower}, i} = +\frac{\operatorname{sgn}(\bar{r}_{\mathrm{leader}, t})}{N_{\mathrm{follower}}}
$$

$$
w_{\mathrm{market}, j} = -\frac{\operatorname{sgn}(\bar{r}_{\mathrm{leader}, t})}{N_{\mathrm{market}}}
$$

This structure enforces strict dollar neutrality ($\sum_{k} w_k = 0$) and insulates the portfolio from aggregate cryptocurrency market direction.

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
```

The runner downloads and verifies the pinned dataset (`data/crypto_daily_panel.csv`) via SHA-256 checksum. All test assertions and numerical replication checks run offline.

## License

MIT License — Copyright (c) 2026 Julian Saiani.
