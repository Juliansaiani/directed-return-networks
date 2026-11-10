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
    for mode, clustered in [('global',False), ('clustered',True)]:
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
    gross = daily.query('cost_bps == 0 and extra_delay == 0').copy()
    gross['period'] = np.where(gross.date <= config['early_period_end'], '2019-2021', '2022-2023')
    subperiods = [dict(mode=mode, period=period, **metrics(frame)) for (mode,period),frame in gross.groupby(['mode','period'])]
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

    frame = daily.query("mode == 'global' and cost_bps == 0 and extra_delay == 0").sort_values('date')
    if frame.empty:
        raise ValueError('No global gross observations to plot')
    dates = pd.DatetimeIndex(pd.to_datetime(frame.date))
    nav = np.r_[1., np.cumprod(1+frame.net_return.to_numpy())]
    drawdown = (nav/np.maximum.accumulate(nav)-1)[1:]
    worst = int(np.argmin(drawdown))

    with plt.rc_context({'font.size':10, 'axes.titleweight':'semibold',
                         'axes.spines.top':False, 'axes.spines.right':False,
                         'axes.spines.left':False, 'axes.edgecolor':'#cbd5e1',
                         'text.color':'#1e293b', 'axes.labelcolor':'#475569',
                         'xtick.color':'#64748b', 'ytick.color':'#64748b'}):
        fig, axes = plt.subplots(2,1,figsize=(11,6.3),sharex=True,
                                 gridspec_kw={'height_ratios':[2,1]},layout='constrained')
        fig.suptitle('Directed Return Networks',fontsize=17,x=.065,ha='left')
        axes[0].set_title('Global portfolio · gross historical simulation · idealized same-close execution',
                          loc='left',fontsize=10,fontweight='normal',color='#64748b',pad=12)
        axes[0].plot(dates,100*nav[1:],color='#2563eb',linewidth=1.5)
        axes[0].set_ylabel('Portfolio value\ninitial = 100',labelpad=12)
        axes[0].yaxis.set_major_locator(MaxNLocator(nbins=4))

        axes[1].fill_between(dates,drawdown,0,color='#dc6b6b',alpha=.35,linewidth=0)
        axes[1].plot(dates,drawdown,color='#b54b4b',linewidth=.65)
        axes[1].axhline(0,color='#94a3b8',linewidth=.8)
        axes[1].set_ylabel('Drawdown',labelpad=12)
        axes[1].set_title('Drawdown from the running peak',loc='left',fontsize=10,fontweight='normal',pad=10)
        axes[1].text(1,1.055,f'Maximum: {drawdown[worst]:.2%}',transform=axes[1].transAxes,
                      ha='right',va='bottom',fontsize=10,color='#9f3535')
        axes[1].yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
        axes[1].set_ylim(min(-.05,np.floor(drawdown.min()/.05)*.05),.012)
        axes[1].yaxis.set_major_locator(MultipleLocator(.05))
        axes[1].scatter(dates[worst],drawdown[worst],s=20,color='#9f3535',zorder=3)
        axes[1].annotate(f'{drawdown[worst]:.2%}',
                         xy=(dates[worst],drawdown[worst]),xytext=(10,8),
                         textcoords='offset points',fontsize=9,color='#9f3535',
                         arrowprops={'arrowstyle':'-','color':'#9f3535','linewidth':.8},
                         bbox={'facecolor':'white','edgecolor':'none','alpha':.8,'pad':2})
        locator = mdates.MonthLocator(bymonth=[1,7])
        axes[1].xaxis.set_major_locator(locator)
        axes[1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        for ax in axes:
            ax.set_axisbelow(True)
            ax.grid(axis='y',color='#e2e8f0',linewidth=.7)
            ax.tick_params(axis='both',which='both',length=0,pad=6)
            ax.margins(x=.01)
        fig.savefig(output/'directed-return-networks.png',dpi=180,facecolor='white');plt.close(fig)


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd())
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        run(args.root)


if __name__ == '__main__':
    main()
