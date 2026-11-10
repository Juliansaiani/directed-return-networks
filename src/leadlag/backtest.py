"""Self-financing long/short accounting with explicit timing conventions."""
import numpy as np
import pandas as pd


def cost_fraction(drift, target, rate):
    fee = 0.
    for _ in range(100):
        turnover = np.abs(target*(1-fee)-drift).sum()
        updated = rate*turnover
        if abs(updated-fee) < 1e-14:
            return float(updated), float(turnover)
        fee = updated
    raise ValueError('Cost equation failed to converge')


def simulate(prices, targets, cost_bps=0, extra_delay=0):
    """Day-t targets execute at close t+delay, after that close's earned P&L.

    delay=0 is an idealized same-close research convention, not a tradability claim.
    Missing marks use the most recent observation; stale closes are counted.
    Funding, cash interest, borrow availability and borrow fees are excluded.
    """
    returns = prices.ffill().pct_change(fill_method=None)
    targets = targets.reindex(index=prices.index, columns=prices.columns, fill_value=0)
    active = np.flatnonzero(targets.abs().sum(axis=1).to_numpy() > 0)
    if not len(active):
        raise ValueError('No nonzero targets')
    start = active[0]
    orders = targets.shift(extra_delay).fillna(0).to_numpy()
    holdings = np.zeros(prices.shape[1]); rows = []
    for t in range(start, len(prices)):
        r = returns.iloc[t].to_numpy()
        if np.any((holdings != 0) & ~np.isfinite(r)):
            raise ValueError('No valuation for held asset')
        gross = float(holdings @ np.nan_to_num(r))
        if gross <= -1:
            raise ValueError('Portfolio insolvency')
        drift = holdings*(1+np.nan_to_num(r))/(1+gross)
        target = orders[t].copy()
        if t == len(prices)-1:
            target[:] = 0
        fee, turnover = cost_fraction(drift, target, cost_bps/1e4)
        holdings = target
        rows.append(dict(date=prices.index[t], gross_return=gross, net_return=(1+gross)*(1-fee)-1,
                         turnover=turnover, transaction_drag=(1+gross)*fee,
                         gross_exposure=float(np.abs(holdings).sum()), net_exposure=float(holdings.sum()),
                         stale_held_marks=int(((drift != 0) & prices.iloc[t].isna().to_numpy()).sum())))
    return pd.DataFrame(rows)


def metrics(frame, annualization=365.25):
    r = frame.net_return.to_numpy()
    nav = np.r_[1., np.cumprod(1+r)]
    vol = r.std(ddof=1)*np.sqrt(annualization)
    return dict(days=len(r), total_return=float(nav[-1]-1), cagr=float(nav[-1]**(annualization/len(r))-1),
                volatility=float(vol), sharpe=float(r.mean()*annualization/vol) if vol > 0 else np.nan,
                sharpe_rf_2pct=float((r.mean()*annualization-.02)/vol) if vol > 0 else np.nan,
                max_drawdown=float(np.min(nav/np.maximum.accumulate(nav)-1)),
                mean_daily_turnover=float(frame.turnover.mean()), stale_held_marks=int(frame.stale_held_marks.sum()))
