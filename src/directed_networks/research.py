"""Download the pinned reference snapshot and run a fixed replication study."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
from importlib.metadata import version
import urllib.request
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from .signals import target_weights
from .backtest import simulate, metrics


def build_targets(prices, config, clustered):
    targets = pd.DataFrame(0., index=prices.index, columns=prices.columns)
    for t in range(config['window'], len(prices)-1):
        history = prices.iloc[:t+1]
        window = history.iloc[-config['window']-1:]
        if window.notna().all().sum() >= config['min_assets']:
            targets.iloc[t] = target_weights(history, config, clustered)
    return targets


def load_prices(root, config):
    path = root/'data/crypto_daily_panel.csv'
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        url = config.get('data_url') or "https://raw.githubusercontent.com/Juliansaiani/directed-return-networks/main/data/crypto_daily_panel.csv"
        with urllib.request.urlopen(url, timeout=60) as response:
            path.write_bytes(response.read())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != config['price_sha256']:
        raise ValueError('Price snapshot differs from the recorded reference')
    prices = pd.read_csv(path, index_col=0, parse_dates=True)
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError('Dates must be unique and sorted')
    if (prices <= 0).any().any():
        raise ValueError('Nonpositive price')
    return prices


def uncertainty(daily, config, block=30, repetitions=2000, cost_tiers=(0, 1)):
    frames = []
    for cost in cost_tiers:
        sub = daily.query('cost_bps == @cost and extra_delay == 0')
        if sub.empty:
            continue
        panel = sub.pivot(index='date', columns='mode', values='net_return')
        values = panel.to_numpy(); n = len(values)
        rng = np.random.default_rng(config['seed']); estimates = []
        for _ in range(repetitions):
            starts = rng.integers(0, n, size=int(np.ceil(n/block)))
            sample = values[((starts[:,None]+np.arange(block)) % n).ravel()[:n]]
            estimates.append(sample.mean(axis=0)/sample.std(axis=0, ddof=1)*np.sqrt(config['annualization']))
        frames.append(pd.DataFrame(dict(mode=panel.columns, cost_bps=float(cost),
                                        lower_95=np.quantile(estimates,.025,axis=0),
                                        upper_95=np.quantile(estimates,.975,axis=0),
                                        block_days=block, repetitions=repetitions)))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=['mode', 'cost_bps', 'lower_95', 'upper_95', 'block_days', 'repetitions']
    )


def run(root, include_clustered=False):
    """Run research pipeline.

    Evaluates the global strategy (and optionally the exploratory clustered variant
    when include_clustered=True) across the configured cost_bps grid (0–10 bps).
    """
    root = root.resolve(); config = json.loads((root/'config.json').read_text())
    prices = load_prices(root, config)
    output = root/'artifacts';output.mkdir(exist_ok=True)
    frames, target_hashes = [], {}
    modes = [('global', False), ('clustered', True)] if include_clustered else [('global', False)]
    for mode, clustered in modes:
        target_path = output/f'{mode}_targets.csv'
        cache_manifest = root/'data/target_cache.json'
        cache = json.loads(cache_manifest.read_text()) if cache_manifest.exists() else {}
        config_hash = hashlib.sha256((root/'config.json').read_bytes()).hexdigest()
        source_hash = hashlib.sha256((Path(__file__).parent/'signals.py').read_bytes()).hexdigest()
        if target_path.exists() and cache.get(mode) == [config_hash, source_hash, hashlib.sha256(target_path.read_bytes()).hexdigest()]:
            targets = pd.read_csv(target_path, index_col=0, parse_dates=True)
        else:
            print('Building targets:', mode, flush=True)
            targets = build_targets(prices, config, clustered)
            targets.to_csv(target_path)
            cache[mode] = [config_hash, source_hash, hashlib.sha256(target_path.read_bytes()).hexdigest()]
            cache_manifest.write_text(json.dumps(cache, indent=2))
        target_hashes[mode] = hashlib.sha256(target_path.read_bytes()).hexdigest()
        for delay in config['extra_execution_days']:
            for cost in config['cost_bps']:
                frame = simulate(prices, targets, cost, delay)
                frame['mode'] = mode;frame['extra_delay'] = delay;frame['cost_bps'] = cost
                frames.append(frame)
    daily = pd.concat(frames, ignore_index=True)
    if config.get('start_date'):
        daily = daily[daily['date'] >= config['start_date']].reset_index(drop=True)
    rows = []
    for (mode, delay, cost), frame in daily.groupby(['mode','extra_delay','cost_bps']):
        rows.append(dict(mode=mode, extra_delay=delay, cost_bps=cost, **metrics(frame)))
    scores = pd.DataFrame(rows)
    scores.to_csv(output/'scores.csv', index=False)
    daily.to_csv(output/'daily.csv', index=False)
    
    subperiods = []
    regime_map = {
        '2021': '2021 (Bull Market)',
        '2022': '2022 (Bear Market)',
        '2023': '2023 (Recovery)',
    }
    for cost in [0.0, 1.0]:
        df_sub = daily.query(f'cost_bps == {cost} and extra_delay == 0').copy()
        years = df_sub['date'].astype(str).str[:4]
        df_sub['period'] = years.map(regime_map).fillna(years)
        for (mode, period), frame in df_sub.groupby(['mode', 'period'], sort=False):
            subperiods.append(dict(mode=mode, cost_bps=cost, period=period, **metrics(frame)))
    pd.DataFrame(subperiods).to_csv(output/'subperiods.csv', index=False)
    
    uncertainty(daily, config).to_csv(output/'uncertainty.csv', index=False)
    bench_df, bench_series = compute_benchmarks(daily, prices)
    bench_df.to_csv(output/'benchmarks.csv', index=False)
    manifest = dict(config=config, python=platform.python_version(),
        packages={name:version(name) for name in ['numpy','pandas','scipy','scikit-learn','matplotlib','threadpoolctl']},
        price_sha256=config['price_sha256'],
        price_rows=len(prices), assets=len(prices.columns), first_price=str(prices.index.min()), last_price=str(prices.index.max()),
        evaluation_start=str(daily.date.min()), evaluation_end=str(daily.date.max()), evaluation_days=len(daily.query("mode == 'global' and cost_bps == 0 and extra_delay == 0")),
        valuation_gaps=int((prices.ffill().notna() & prices.isna()).sum().sum()), target_hashes=target_hashes,
        sharpe='Arithmetic mean daily portfolio return divided by sample standard deviation, annualized by sqrt(365.25); zero cash rate',
        uncertainty_method='Fixed-length 30-day circular block bootstrap (2,000 resamplings); quantifies sample variability without establishing cross-regime stationarity',
        benchmark_methodology='100% long annual-rebalanced (Jan 1) fixed-target baskets with intra-year price drift (Large-Cap Crypto Index: 62% BTC / 26% ETH / 12% across 8 large-caps [XRP, LTC, LINK, XLM, ADA, ATOM, EOS, TRX]; Core Crypto Index: 70% BTC / 30% ETH; Bitcoin: 100% BTC)',
        data_provenance=config.get('data_provenance', {}),
        changes=['Vectorized exact level-2 path areas', 'Absolute-degree Hermitian normalization',
                 'Market hedge universe observed at decision date', 'Explicit entry, rebalance and liquidation costs', 'One-day execution-delay sensitivity'],
        limitations=['Retrospective 57-asset panel', 'No untouched post-2023 out-of-sample holdout',
                     'Idealized same-close execution in zero-delay variants', 'Funding, borrow fees and availability excluded',
                     'Missing prices carried forward for valuation, not evidence of executable fills',
                     'Dollar-neutral weights do not imply market-beta neutrality',
                     'Fixed-length 30-day circular block bootstrap does not by itself prove stability across all regimes'])
    (output/'run.json').write_text(json.dumps(manifest, indent=2)+'\n')
    plot(daily, prices, output, bench_series=bench_series)
    print(scores.to_string(index=False), flush=True)


def _series_stats(ret):
    n_years = len(ret) / 365.25
    nav = np.cumprod(1.0 + ret)
    vol = float(ret.std(ddof=1) * np.sqrt(365.25))
    sharpe = float(ret.mean() * 365.25 / (vol + 1e-12))
    cagr = float(nav[-1] ** (1.0 / n_years) - 1.0)
    tot = float(nav[-1] - 1.0)
    dd_full = np.r_[1.0, nav] / np.maximum.accumulate(np.r_[1.0, nav]) - 1.0
    dd = dd_full[1:]
    return nav, dd, sharpe, cagr, tot, vol, float(dd.min())


def _annual_rebalanced_basket(rets, target_weights):
    """Simulate a 100% long basket reset on Jan 1 with daily price-driven weight drift."""
    cols = list(target_weights.keys())
    base = np.array([target_weights[c] for c in cols], dtype=float)
    mat = rets[cols].to_numpy(dtype=float)
    dates = rets.index
    weights = base.copy()
    out = np.empty(len(dates), dtype=float)
    for i in range(len(dates)):
        if i > 0 and dates[i].year != dates[i - 1].year:
            weights = base.copy()
        day_r = mat[i]
        port_r = float(weights @ day_r)
        out[i] = port_r
        weights = weights * (1.0 + day_r) / (1.0 + port_r)
    return out


def compute_benchmarks(daily, prices):
    frame_gross = daily.query("mode == 'global' and cost_bps == 0 and extra_delay == 0").sort_values('date')
    if frame_gross.empty:
        raise ValueError('No global gross observations for benchmarks')

    dates = pd.DatetimeIndex(pd.to_datetime(frame_gross.date))
    prev_candidates = prices.index[prices.index < dates[0]]
    start_slice = prev_candidates[-1] if len(prev_candidates) else dates[0]

    # Simple daily returns (ffill missing marks at 0% return after delisting)
    sub_ff = prices.loc[start_slice:dates[-1]].ffill()
    rets = sub_ff.pct_change(fill_method=None).reindex(dates).fillna(0.0)

    # 1. Large-Cap Crypto Index (62% BTC, 26% ETH, 12% across 8 altcoins; rebalanced Jan 1 with drift)
    lc_cols = [c for c in ['XRP', 'LTC', 'LINK', 'XLM', 'ADA', 'ATOM', 'EOS', 'TRX'] if c in rets.columns]
    lc_weights = {'BTC': 0.62, 'ETH': 0.26, **{c: 0.12 / len(lc_cols) for c in lc_cols}}
    lc_ret = _annual_rebalanced_basket(rets, lc_weights)

    # 2. Core Crypto Index (70% BTC / 30% ETH; rebalanced Jan 1 with drift)
    core_ret = _annual_rebalanced_basket(rets, {'BTC': 0.70, 'ETH': 0.30})

    # 3. Bitcoin (Spot Buy & Hold)
    btc_ret = rets['BTC'].to_numpy()

    specs = [
        ('large_cap', 'Large-Cap Crypto Index', 'Annual Rebal 62/26/12 with Drift (100% Long)', lc_ret),
        ('core_crypto', 'Core Crypto Index', 'Annual Rebal BTC / ETH 70/30 with Drift (100% Long)', core_ret),
        ('btc', 'Bitcoin', 'Spot Buy & Hold (100% Long)', btc_ret),
    ]
    rows, series = [], {}
    for key, name, construction, ret in specs:
        nav, dd, sharpe, cagr, tot, vol, worst = _series_stats(ret)
        rows.append(dict(
            benchmark=name, construction=construction,
            days=len(ret), total_return=tot, cagr=cagr, volatility=vol,
            sharpe=sharpe, max_drawdown=worst,
        ))
        series[key] = dict(name=name, nav=nav, dd=dd, sharpe=sharpe, cagr=cagr, tot=tot, vol=vol, worst=worst)
    return pd.DataFrame(rows), series


def plot(daily, prices, output, bench_series=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import PercentFormatter

    frame_gross = daily.query("mode == 'global' and cost_bps == 0 and extra_delay == 0").sort_values('date')
    frame_net = daily.query("mode == 'global' and cost_bps == 1 and extra_delay == 0").sort_values('date')
    frame_net2 = daily.query("mode == 'global' and cost_bps == 2 and extra_delay == 0").sort_values('date')
    if frame_gross.empty:
        raise ValueError('No global gross observations to plot')

    if bench_series is None:
        _, bench_series = compute_benchmarks(daily, prices)

    dates = pd.DatetimeIndex(pd.to_datetime(frame_gross.date))
    ret_g = frame_gross.net_return.to_numpy()
    nav_g, dd_g, sharpe_g, cagr_g, tot_g, _, worst_g = _series_stats(ret_g)
    label_g = f'Directed Network — Gross (0 bps): {tot_g:+.1%} | CAGR {cagr_g:+.1%} | Sharpe {sharpe_g:.2f}'

    nav_n = dd_n = ret_n = None
    if not frame_net.empty:
        ret_n = frame_net.net_return.to_numpy()
        nav_n, dd_n, sharpe_n, cagr_n, tot_n, _, worst_n = _series_stats(ret_n)
        label_n = f'Directed Network — Net (1 bp): {tot_n:+.1%} | CAGR {cagr_n:+.1%} | Sharpe {sharpe_n:.2f}'

    lc = bench_series['large_cap']
    label_lc = f"Large-Cap Crypto Index: {lc['tot']:+.1%} | CAGR {lc['cagr']:+.1%} | Sharpe {lc['sharpe']:.2f}"

    core = bench_series['core_crypto']
    label_core = f"Core Crypto Index: {core['tot']:+.1%} | CAGR {core['cagr']:+.1%} | Sharpe {core['sharpe']:.2f}"

    btc = bench_series['btc']
    label_btc = f"Bitcoin: {btc['tot']:+.1%} | CAGR {btc['cagr']:+.1%} | Sharpe {btc['sharpe']:.2f}"

    # Market regime metadata & dynamic annual strategy stats
    regimes = [
        ('2021', '2021-01-01', '2022-01-01', '2021-07-02', '2021: Bull Market', '#2ca02c', '#edf7ed', 0.045),
        ('2022', '2022-01-01', '2023-01-01', '2022-07-02', '2022: Bear Market Crash', '#d62728', '#fdecea', 0.055),
        ('2023', '2023-01-01', '2023-12-31', '2023-07-02', '2023: Market Recovery', '#1f77b4', '#e8f4fd', 0.045),
    ]
    ref_frame = frame_net if not frame_net.empty else frame_gross
    ref_tag = 'Net' if not frame_net.empty else 'Gross'
    ref_dates = pd.DatetimeIndex(pd.to_datetime(ref_frame.date))
    ref_ret = ref_frame.net_return.to_numpy()
    regime_labels = []
    for yr, r_start, r_end, r_mid, r_title, r_edge, r_face, r_alpha in regimes:
        mask = ref_dates.year == int(yr)
        if mask.any():
            r_sub = ref_ret[mask]
            _, _, r_sh, _, r_tot, _, r_dd = _series_stats(r_sub)
            regime_labels.append((r_start, r_end, r_mid, r_title, r_edge, r_face, r_alpha, r_tot, r_sh, r_dd))

    # Figure 1: Cumulative Performance (overview.png)
    with plt.rc_context():
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12.5, 6.8))
        for r_start, r_end, r_mid, r_title, r_edge, r_face, r_alpha, r_tot, r_sh, _ in regime_labels:
            ax.axvspan(pd.Timestamp(r_start), pd.Timestamp(r_end), color=r_edge, alpha=r_alpha)
            ax.text(pd.Timestamp(r_mid), 0.965, f'{r_title}\n{ref_tag} {r_tot:+.1%} | Sharpe {r_sh:.2f}',
                    transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=9.2, fontweight='bold',
                    color='#222222', bbox=dict(boxstyle='round,pad=0.38', facecolor=r_face, edgecolor=r_edge, alpha=0.92, lw=1.0))

        for boundary in ['2022-01-01', '2023-01-01']:
            ax.axvline(pd.Timestamp(boundary), color='#666666', linestyle='--', lw=0.9, alpha=0.55)

        ax.plot(dates, nav_g, color='#1f77b4', lw=2.2, label=label_g)
        if nav_n is not None:
            ax.plot(dates, nav_n, color='#2ca02c', lw=2.0, linestyle='--', label=label_n)
            ax.fill_between(dates, nav_n, nav_g, color='#ff7f0e', alpha=0.14,
                            label='1 bp Institutional Execution Friction')
        ax.plot(dates, lc['nav'], color='#9467bd', lw=1.8, linestyle='-.', label=label_lc)
        ax.plot(dates, core['nav'], color='#6c757d', lw=1.6, linestyle=(0, (3, 1, 1, 1, 1, 1)), label=label_core)
        ax.plot(dates, btc['nav'], color='#8c564b', lw=1.6, linestyle=':', label=label_btc)

        ax.axhline(1.0, color='black', lw=0.8, linestyle=':', alpha=0.6)
        ax.set_title(
            f'Directed Return Networks: Cumulative Performance Across Crypto Market Regimes ({dates[0].date()} to {dates[-1].date()})',
            fontsize=12.5, fontweight='bold', pad=12)
        ax.set_ylabel('Growth of $1.00', fontsize=10.5)
        y_low = min(float(btc['nav'].min()) * 0.85, float(lc['nav'].min()) * 0.85, float(core['nav'].min()) * 0.85, 0.45)
        y_top = max(float(nav_g.max()), float(lc['nav'].max()), float(core['nav'].max())) * 1.18
        ax.set_ylim(y_low, y_top)
        ax.set_xlim(dates[0], dates[-1])
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend(fontsize=8.6, loc='upper center', bbox_to_anchor=(0.5, -0.09), ncol=2, frameon=True, edgecolor='#dddddd')
        fig.tight_layout()
        fig.savefig(output / 'overview.png', dpi=200, bbox_inches='tight')
        plt.close(fig)

    # Figure 2: Drawdown Dynamics (drawdowns.png)
    with plt.rc_context():
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12.5, 5.6))
        for r_start, r_end, r_mid, r_title, r_edge, r_face, r_alpha, _, _, r_dd in regime_labels:
            ax.axvspan(pd.Timestamp(r_start), pd.Timestamp(r_end), color=r_edge, alpha=r_alpha)
            ax.text(pd.Timestamp(r_mid), 0.965, f'{r_title}\n{ref_tag} Max DD {r_dd:.1%}',
                    transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=9.0, fontweight='bold',
                    color='#222222', bbox=dict(boxstyle='round,pad=0.35', facecolor=r_face, edgecolor=r_edge, alpha=0.92, lw=1.0))

        for boundary in ['2022-01-01', '2023-01-01']:
            ax.axvline(pd.Timestamp(boundary), color='#666666', linestyle='--', lw=0.9, alpha=0.55)

        ax.plot(dates, dd_g, color='#1f77b4', lw=1.6, label=f'Directed Network — Gross (0 bps) | Max DD: {worst_g:.1%}')
        if dd_n is not None:
            ax.plot(dates, dd_n, color='#2ca02c', lw=1.5, linestyle='--', label=f'Directed Network — Net (1 bp) | Max DD: {worst_n:.1%}')
            ax.fill_between(dates, dd_n, 0, color='#2ca02c', alpha=0.10)
        else:
            ax.fill_between(dates, dd_g, 0, color='#1f77b4', alpha=0.12)
        ax.plot(dates, lc['dd'], color='#9467bd', lw=1.5, linestyle='-.', label=f"Large-Cap Crypto Index | Max DD: {lc['worst']:.1%}")
        ax.plot(dates, core['dd'], color='#6c757d', lw=1.4, linestyle=(0, (3, 1, 1, 1, 1, 1)), label=f"Core Crypto Index | Max DD: {core['worst']:.1%}")
        ax.plot(dates, btc['dd'], color='#8c564b', lw=1.4, linestyle=':', label=f"Bitcoin | Max DD: {btc['worst']:.1%}")

        ax.axhline(0, color='black', lw=0.7)
        ax.set_title(
            f'Underwater Drawdown Dynamics Across Crypto Market Regimes ({dates[0].date()} to {dates[-1].date()})',
            fontsize=12.5, fontweight='bold', pad=12)
        ax.set_ylabel('Drawdown (%)', fontsize=10.5)
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        min_dd = min(worst_g, worst_n if dd_n is not None else 0, lc['worst'], core['worst'], btc['worst'])
        y_bot = min(-0.10, np.floor(min_dd / 0.10) * 0.10)
        ax.set_ylim(y_bot, 0.12)
        ax.set_yticks(np.round(np.arange(y_bot, 0.001, 0.10), 2))
        ax.set_xlim(dates[0], dates[-1])
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend(fontsize=8.6, loc='upper center', bbox_to_anchor=(0.5, -0.10), ncol=2, frameon=True, edgecolor='#dddddd')
        fig.tight_layout()
        fig.savefig(output / 'drawdowns.png', dpi=200, bbox_inches='tight')
        plt.close(fig)

    # Figure 3: Large-Cap Crypto Index Volatility-Matched Cumulative Performance (leveraged_overview.png)
    target_vol = lc['vol']
    lev_g = target_vol / float(ret_g.std(ddof=1) * np.sqrt(365.25))
    ret_g_lev = ret_g * lev_g
    nav_g_lev, dd_g_lev, sharpe_g_lev, cagr_g_lev, tot_g_lev, _, worst_g_lev = _series_stats(ret_g_lev)
    label_g_lev = f'Directed Network — Gross (0 bps, {lev_g:.2f}x): {tot_g_lev:+.1%} | CAGR {cagr_g_lev:+.1%} | Sharpe {sharpe_g_lev:.2f}'

    nav_n1_lev = dd_n1_lev = ret_n1_lev = None
    worst_n1_lev = 0.0
    lev_ref = lev_g
    if ret_n is not None:
        lev_n1 = target_vol / float(ret_n.std(ddof=1) * np.sqrt(365.25))
        lev_ref = lev_n1
        ret_n1_lev = ret_n * lev_n1
        nav_n1_lev, dd_n1_lev, sharpe_n1_lev, cagr_n1_lev, tot_n1_lev, _, worst_n1_lev = _series_stats(ret_n1_lev)
        label_n1_lev = f'Directed Network — Net (1 bp, {lev_n1:.2f}x): {tot_n1_lev:+.1%} | CAGR {cagr_n1_lev:+.1%} | Sharpe {sharpe_n1_lev:.2f}'

    nav_n2_lev = dd_n2_lev = None
    worst_n2_lev = 0.0
    if not frame_net2.empty:
        ret_n2 = frame_net2.net_return.to_numpy()
        lev_n2 = target_vol / float(ret_n2.std(ddof=1) * np.sqrt(365.25))
        ret_n2_lev = ret_n2 * lev_n2
        nav_n2_lev, dd_n2_lev, sharpe_n2_lev, cagr_n2_lev, tot_n2_lev, _, worst_n2_lev = _series_stats(ret_n2_lev)
        label_n2_lev = f'Directed Network — Net (2 bps, {lev_n2:.2f}x): {tot_n2_lev:+.1%} | CAGR {cagr_n2_lev:+.1%} | Sharpe {sharpe_n2_lev:.2f}'

    ref_ret_lev = ret_n1_lev if ret_n1_lev is not None else ret_g_lev
    regime_labels_lev = []
    for yr, r_start, r_end, r_mid, r_title, r_edge, r_face, r_alpha in regimes:
        mask = ref_dates.year == int(yr)
        if mask.any():
            r_sub = ref_ret_lev[mask]
            _, _, r_sh, _, r_tot, _, r_dd = _series_stats(r_sub)
            regime_labels_lev.append((r_start, r_end, r_mid, r_title, r_edge, r_face, r_alpha, r_tot, r_sh, r_dd))

    with plt.rc_context():
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12.5, 6.8))
        for r_start, r_end, r_mid, r_title, r_edge, r_face, r_alpha, r_tot, r_sh, _ in regime_labels_lev:
            ax.axvspan(pd.Timestamp(r_start), pd.Timestamp(r_end), color=r_edge, alpha=r_alpha)
            ax.text(pd.Timestamp(r_mid), 0.965, f'{r_title}\n{ref_tag} ({lev_ref:.2f}x) {r_tot:+.1%} | Sharpe {r_sh:.2f}',
                    transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=9.0, fontweight='bold',
                    color='#222222', bbox=dict(boxstyle='round,pad=0.38', facecolor=r_face, edgecolor=r_edge, alpha=0.92, lw=1.0))

        for boundary in ['2022-01-01', '2023-01-01']:
            ax.axvline(pd.Timestamp(boundary), color='#666666', linestyle='--', lw=0.9, alpha=0.55)

        ax.plot(dates, nav_g_lev, color='#1f77b4', lw=2.2, label=label_g_lev)
        if nav_n1_lev is not None:
            ax.plot(dates, nav_n1_lev, color='#2ca02c', lw=2.0, linestyle='--', label=label_n1_lev)
            ax.fill_between(dates, nav_n1_lev, nav_g_lev, color='#ff7f0e', alpha=0.14,
                            label='1 bp Institutional Execution Friction')
        if nav_n2_lev is not None:
            ax.plot(dates, nav_n2_lev, color='#17becf', lw=1.8, linestyle='-.', label=label_n2_lev)
        ax.plot(dates, lc['nav'], color='#9467bd', lw=1.7, linestyle=(0, (5, 2)), label=label_lc)
        ax.plot(dates, core['nav'], color='#6c757d', lw=1.5, linestyle=(0, (3, 1, 1, 1, 1, 1)), label=label_core)
        ax.plot(dates, btc['nav'], color='#8c564b', lw=1.6, linestyle=':', label=label_btc)

        ax.axhline(1.0, color='black', lw=0.8, linestyle=':', alpha=0.6)
        ax.set_title(
            f'Directed Return Networks (Vol-Matched to Large-Cap Crypto Index {target_vol:.1%}, {dates[0].date()} to {dates[-1].date()})',
            fontsize=12.5, fontweight='bold', pad=12)
        ax.set_ylabel('Growth of $1.00', fontsize=10.5)
        y_low = min(float(btc['nav'].min()) * 0.85, float(lc['nav'].min()) * 0.85, float(core['nav'].min()) * 0.85, 0.45)
        y_top = float(nav_g_lev.max()) * 1.18
        ax.set_ylim(y_low, y_top)
        ax.set_xlim(dates[0], dates[-1])
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend(fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.09), ncol=2, frameon=True, edgecolor='#dddddd')
        fig.tight_layout()
        fig.savefig(output / 'leveraged_overview.png', dpi=200, bbox_inches='tight')
        plt.close(fig)

    # Figure 4: Volatility-Matched Underwater Drawdowns (leveraged_drawdowns.png)
    with plt.rc_context():
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12.5, 5.6))
        for r_start, r_end, r_mid, r_title, r_edge, r_face, r_alpha, _, _, r_dd in regime_labels_lev:
            ax.axvspan(pd.Timestamp(r_start), pd.Timestamp(r_end), color=r_edge, alpha=r_alpha)
            ax.text(pd.Timestamp(r_mid), 0.965, f'{r_title}\n{ref_tag} ({lev_ref:.2f}x) Max DD {r_dd:.1%}',
                    transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=9.0, fontweight='bold',
                    color='#222222', bbox=dict(boxstyle='round,pad=0.35', facecolor=r_face, edgecolor=r_edge, alpha=0.92, lw=1.0))

        for boundary in ['2022-01-01', '2023-01-01']:
            ax.axvline(pd.Timestamp(boundary), color='#666666', linestyle='--', lw=0.9, alpha=0.55)

        ax.plot(dates, dd_g_lev, color='#1f77b4', lw=1.6,
                label=f'Directed Network — Gross (0 bps, {lev_g:.2f}x) | Max DD: {worst_g_lev:.1%}')
        if dd_n1_lev is not None:
            ax.plot(dates, dd_n1_lev, color='#2ca02c', lw=1.5, linestyle='--',
                    label=f'Directed Network — Net (1 bp, {lev_n1:.2f}x) | Max DD: {worst_n1_lev:.1%}')
            ax.fill_between(dates, dd_n1_lev, 0, color='#2ca02c', alpha=0.10)
        else:
            ax.fill_between(dates, dd_g_lev, 0, color='#1f77b4', alpha=0.12)
        if dd_n2_lev is not None:
            ax.plot(dates, dd_n2_lev, color='#17becf', lw=1.4, linestyle='-.',
                    label=f'Directed Network — Net (2 bps, {lev_n2:.2f}x) | Max DD: {worst_n2_lev:.1%}')
        ax.plot(dates, lc['dd'], color='#9467bd', lw=1.5, linestyle=(0, (5, 2)),
                label=f"Large-Cap Crypto Index | Max DD: {lc['worst']:.1%}")
        ax.plot(dates, core['dd'], color='#6c757d', lw=1.4, linestyle=(0, (3, 1, 1, 1, 1, 1)),
                label=f"Core Crypto Index | Max DD: {core['worst']:.1%}")
        ax.plot(dates, btc['dd'], color='#8c564b', lw=1.4, linestyle=':',
                label=f"Bitcoin | Max DD: {btc['worst']:.1%}")

        ax.axhline(0, color='black', lw=0.7)
        ax.set_title(
            f'Volatility-Matched Underwater Drawdowns (at Large-Cap Index {target_vol:.1%} Vol, {dates[0].date()} to {dates[-1].date()})',
            fontsize=12.5, fontweight='bold', pad=12)
        ax.set_ylabel('Drawdown (%)', fontsize=10.5)
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        min_dd_lev = min(worst_g_lev, worst_n1_lev if dd_n1_lev is not None else 0,
                         worst_n2_lev if dd_n2_lev is not None else 0, lc['worst'], core['worst'], btc['worst'])
        y_bot_lev = min(-0.10, np.floor(min_dd_lev / 0.10) * 0.10)
        ax.set_ylim(y_bot_lev, 0.14)
        ax.set_yticks(np.round(np.arange(y_bot_lev, 0.001, 0.10), 2))
        ax.set_xlim(dates[0], dates[-1])
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend(fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, -0.10), ncol=2, frameon=True, edgecolor='#dddddd')
        fig.tight_layout()
        fig.savefig(output / 'leveraged_drawdowns.png', dpi=200, bbox_inches='tight')
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--all', action='store_true', help='Evaluate both global and clustered partitions under active config (0, 0.5, 1, 2 bps)')
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        run(args.root, include_clustered=args.all)


if __name__ == '__main__':
    main()
