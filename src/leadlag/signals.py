"""Level-two signatures and Hermitian clustering of directed lead-lag scores.

Adapted from the method in ARahimiQuant/lead-lag-portfolios (MIT).
The vectorized signature calculation and absolute-degree normalization are explicit changes.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def levy_matrix(prices):
    returns = prices.pct_change(fill_method=None).dropna()
    volatility = returns.std(ddof=1)
    if len(returns) < 3 or (volatility <= 0).any():
        raise ValueError('Need nonconstant, complete return paths')
    z = ((returns-returns.mean())/volatility).to_numpy()
    starts = z[:-1]-z[0]
    steps = np.diff(z, axis=0)
    areas = .5*(starts.T@steps-steps.T@starts)
    return pd.DataFrame(areas, index=returns.columns, columns=returns.columns)


def normalized_hermitian(matrix):
    matrix = np.asarray(matrix, dtype=float)
    if not np.isfinite(matrix).all() or not np.allclose(matrix, -matrix.T, atol=1e-12):
        raise ValueError('Lead-lag matrix must be finite and antisymmetric')
    degree = np.abs(matrix).sum(axis=1)
    inverse = np.divide(1, np.sqrt(degree), out=np.zeros_like(degree), where=degree > 1e-14)
    return 1j*matrix*inverse[:,None]*inverse[None,:]


def spectral_clusters(matrix, config):
    h = normalized_hermitian(matrix)
    values, vectors = np.linalg.eigh(h)
    order = np.argsort(np.abs(values))[::-1]
    best_score, best_labels = -np.inf, None
    for k in range(config['cluster_min'], config['cluster_max']+1):
        if k >= len(matrix):
            continue
        selected = vectors[:, order[:2*(k//2)]]
        features = np.column_stack([selected.real, selected.imag])
        labels = KMeans(n_clusters=k, random_state=config['seed'], n_init=10).fit_predict(features)
        if len(np.unique(labels)) < 2:
            continue
        score = silhouette_score(features, labels)
        if score > best_score:
            best_score, best_labels = score, labels
    if best_labels is None:
        raise ValueError('No valid spectral partition')
    return best_labels


def leaders_followers(score, fraction, labels=None):
    groups = [score.columns] if labels is None else [score.columns[labels==k] for k in np.unique(labels)]
    leaders, followers = [], []
    for names in groups:
        ranking = score.loc[names,names].mean(axis=1).sort_values(kind='stable')
        count = int(fraction*len(ranking))
        if count:
            leaders.extend(ranking.index[-count:])
            followers.extend(ranking.index[:count])
    return leaders, followers


def target_weights(history, config, clustered=False):
    window = history.iloc[-config['window']-1:].dropna(axis=1)
    target = pd.Series(0., index=history.columns)
    if len(window) != config['window']+1 or window.shape[1] < config['min_assets']:
        return target
    score = levy_matrix(window)
    labels = spectral_clusters(score.to_numpy(), config) if clustered else None
    leaders, followers = leaders_followers(score, config['selection_fraction'], labels)
    if not leaders or not followers:
        return target
    returns = history.ffill().pct_change(fill_method=None).iloc[-1]
    market = history.columns[returns.notna() & history.iloc[-1].notna()]
    sign = 1 if returns[leaders].mean() > 0 else -1
    target[followers] += sign/len(followers)
    target[market] -= sign/len(market)
    return target
