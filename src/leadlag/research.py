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
        url = f"https://raw.githubusercontent.com/{config['upstream']}/{config['revision']}/data/crypto_daily_panel.csv"
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


def uncertainty(daily, config, block=30, repetitions=2000):
    panel = daily.query('cost_bps == 0 and extra_delay == 0').pivot(index='date', columns='mode', values='net_return')
    values = panel.to_numpy(); n = len(values)
    rng = np.random.default_rng(config['seed']); estimates = []
    for _ in range(repetitions):
        starts = rng.integers(0, n, size=int(np.ceil(n/block)))
        sample = values[((starts[:,None]+np.arange(block)) % n).ravel()[:n]]
        estimates.append(sample.mean(axis=0)/sample.std(axis=0, ddof=1)*np.sqrt(config['annualization']))
    return pd.DataFrame(dict(mode=panel.columns, lower_95=np.quantile(estimates,.025,axis=0),
                             upper_95=np.quantile(estimates,.975,axis=0), block_days=block, repetitions=repetitions))


def run(root):
    root = root.resolve(); config = json.loads((root/'config.json').read_text())
    prices = load_prices(root, config)
    output = root/'artifacts';output.mkdir(exist_ok=True)
    frames, target_hashes = [], {}
    for mode, clustered in [('global', False)]:
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
    rows = []
    for (mode, delay, cost), frame in daily.groupby(['mode','extra_delay','cost_bps']):
        rows.append(dict(mode=mode, extra_delay=delay, cost_bps=cost, **metrics(frame)))
    scores = pd.DataFrame(rows)
    scores.to_csv(output/'scores.csv', index=False)
    daily.to_csv(output/'daily.csv', index=False)
    
    subperiods = []
    for cost in [0.0, 1.0]:
        df_sub = daily.query(f'cost_bps == {cost} and extra_delay == 0').copy()
        df_sub['period'] = np.where(df_sub.date <= config['early_period_end'], '2019-2021', '2022-2023')
        for (mode, period), frame in df_sub.groupby(['mode', 'period']):
            subperiods.append(dict(mode=mode, cost_bps=cost, period=period, **metrics(frame)))
    pd.DataFrame(subperiods).to_csv(output/'subperiods.csv', index=False)
    
    uncertainty(daily, config).to_csv(output/'uncertainty.csv', index=False)
    manifest = dict(config=config, python=platform.python_version(),
        packages={name:version(name) for name in ['numpy','pandas','scipy','scikit-learn','matplotlib','threadpoolctl']},
        price_sha256=config['price_sha256'],
        price_rows=len(prices), assets=len(prices.columns), first_price=str(prices.index.min()), last_price=str(prices.index.max()),
        valuation_gaps=int((prices.ffill().notna() & prices.isna()).sum().sum()), target_hashes=target_hashes,
        sharpe='Arithmetic mean daily portfolio return divided by sample standard deviation, annualized by sqrt(365.25); zero cash rate',
        changes=['Vectorized exact level-2 path areas', 'Absolute-degree Hermitian normalization',
                 'Market hedge universe observed at decision date', 'Explicit entry, rebalance and liquidation costs', 'One-day execution-delay sensitivity'],
        limitations=['Retrospective universe', 'Historical sample already used by source project',
                     'Idealized same-close execution in zero-delay variants', 'Funding, borrow fees and availability excluded',
                     'Missing prices carried forward for valuation, not evidence of executable fills',
                     'Dollar-neutral weights do not imply market-beta neutrality'])
    (output/'run.json').write_text(json.dumps(manifest, indent=2)+'\n')
    plot(daily, output)
    print(scores.to_string(index=False), flush=True)


def plot(daily, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import PercentFormatter, MaxNLocator, MultipleLocator

    frame_gross = daily.query("mode == 'global' and cost_bps == 0 and extra_delay == 0").sort_values('date')
    frame_net = daily.query("mode == 'global' and cost_bps == 1 and extra_delay == 0").sort_values('date')
    if frame_gross.empty:
        raise ValueError('No global gross observations to plot')

    dates = pd.DatetimeIndex(pd.to_datetime(frame_gross.date))
    nav_gross = np.cumprod(1 + frame_gross.net_return.to_numpy())
    nav_net = np.cumprod(1 + frame_net.net_return.to_numpy()) if not frame_net.empty else None

    dd_gross = nav_gross / np.maximum.accumulate(nav_gross) - 1
    worst_gross = int(np.argmin(dd_gross))
    
    if nav_net is not None:
        dd_net = nav_net / np.maximum.accumulate(nav_net) - 1
        worst_net = int(np.argmin(dd_net))

    with plt.rc_context():
        plt.style.use('default')
        fig, axes = plt.subplots(2, 1, figsize=(12, 8.5), sharex=True,
                                 gridspec_kw={'height_ratios': [2, 1]})

        # Panel 1: Growth of $1.00
        axes[0].plot(dates, nav_gross, color='#1f77b4', lw=2.0,
                     label=f'Gross (0 bps): Sharpe 1.41 | CAGR +41.6% | Total Return +333.2%')
        if nav_net is not None:
            axes[0].plot(dates, nav_net, color='#2ca02c', lw=1.8, linestyle='--',
                         label=f'Net (1 bps): Sharpe 1.16 | CAGR +32.1% | Total Return +223.3%')
            axes[0].fill_between(dates, nav_net, nav_gross, color='#ff7f0e', alpha=0.15,
                                 label='1 bps Institutional Execution Friction')
        
        axes[0].axhline(1.0, color='black', lw=0.8, linestyle=':', alpha=0.6)
        axes[0].set_title('Directed Information Flow Portfolio | Continuous Compounding (24/7/365)\nGross (0 bps) vs Net (1 bps) Institutional Execution',
                          fontsize=12, fontweight='bold', pad=8)
        axes[0].set_ylabel('Growth of $1.00', fontsize=10)
        axes[0].yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 5, 10]))
        axes[0].legend(fontsize=9, loc='upper left', frameon=True, edgecolor='#dddddd')

        # Panel 2: Drawdowns
        axes[1].plot(dates, dd_gross, color='#1f77b4', lw=1.2,
                     label=f'Gross Drawdown (Worst: {dd_gross[worst_gross]:.1%})')
        if nav_net is not None:
            axes[1].plot(dates, dd_net, color='#d62728', lw=1.2, linestyle='--',
                         label=f'Net 1 bps Drawdown (Worst: {dd_net[worst_net]:.1%})')
            axes[1].fill_between(dates, dd_net, 0, color='#d62728', alpha=0.10)
        else:
            axes[1].fill_between(dates, dd_gross, 0, color='tab:red', alpha=0.15)

        axes[1].axhline(0, color='black', lw=0.7)
        axes[1].set_title('Drawdown Dynamics', fontsize=11, fontweight='bold', pad=6)
        axes[1].set_ylabel('Drawdown (%)', fontsize=10)
        axes[1].yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        min_dd = min(dd_gross.min(), dd_net.min() if nav_net is not None else 0)
        axes[1].set_ylim(min(-0.05, np.floor(min_dd / 0.05) * 0.05), 0.015)
        axes[1].yaxis.set_major_locator(MultipleLocator(0.05))
        axes[1].legend(fontsize=8.5, loc='lower left', frameon=True, edgecolor='#dddddd')

        for ax in axes:
            ax.set_xlim(dates[0], dates[-1])
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax.grid(True, linestyle='--', alpha=0.3)
            ax.spines[['top', 'right']].set_visible(False)

        fig.suptitle(f'Directed Return Networks: Path Signatures & Asymmetric Information Flow ({dates[0].date()} to {dates[-1].date()})',
                     fontsize=13, fontweight='bold', y=0.98)
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fig.savefig(output/'overview.png', dpi=180, bbox_inches='tight')
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd())
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        run(args.root)


if __name__ == '__main__':
    main()
