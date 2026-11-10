import numpy as np
import pandas as pd
import pytest
from leadlag.signals import levy_matrix, normalized_hermitian, target_weights
from leadlag.research import build_targets
from leadlag.backtest import simulate, cost_fraction


def config():
    return dict(window=12, min_assets=10, selection_fraction=.2, cluster_min=3, cluster_max=4, seed=42)


def prices():
    rng = np.random.default_rng(55)
    return pd.DataFrame(100*np.exp(rng.normal(0,.02,(45,16)).cumsum(axis=0)),
                        index=pd.date_range('2020-01-01',periods=45))


def test_vectorized_areas_match_independent_signature_recursion():
    p = prices().iloc[:25]
    r = p.pct_change().dropna();z = ((r-r.mean())/r.std()).to_numpy()
    area = levy_matrix(p).to_numpy()
    for i in range(16):
        for j in range(i+1,16):
            path = z[:,[i,j]]
            first, second = np.zeros(2), np.zeros((2,2))
            for step in np.diff(path,axis=0):
                second += np.outer(first,step)+.5*np.outer(step,step)
                first += step
            assert area[i,j] == pytest.approx(.5*(second[0,1]-second[1,0]),abs=1e-12)
    np.testing.assert_allclose(area,-area.T,atol=1e-12)
    np.testing.assert_array_equal(area.diagonal(),0)


def test_areas_are_invariant_to_price_units():
    p = prices()
    changed = p*np.arange(1,17)
    np.testing.assert_allclose(levy_matrix(p),levy_matrix(changed),atol=1e-12)


def test_normalization_is_hermitian_and_handles_isolated_nodes():
    a = levy_matrix(prices()).to_numpy().copy()
    a[0,:] = 0;a[:,0] = 0
    h = normalized_hermitian(a)
    np.testing.assert_allclose(h,h.conj().T,atol=1e-12)
    assert np.isfinite(h).all()
    np.testing.assert_array_equal(h[0],0)
    with pytest.raises(ValueError):
        normalized_hermitian(np.ones((4,4)))


@pytest.mark.parametrize('clustered',[False,True])
def test_future_prices_cannot_change_past_targets(clustered):
    p = prices();changed = p.copy();changed.iloc[-5:] *= 1.4
    a = build_targets(p,config(),clustered)
    b = build_targets(changed,config(),clustered)
    pd.testing.assert_frame_equal(a.iloc[:-5],b.iloc[:-5])
    np.testing.assert_allclose(a.sum(axis=1),0,atol=1e-12)
    assert a.abs().sum(axis=1).max() <= 2+1e-12


def test_not_yet_listed_asset_has_zero_weight():
    p = prices();p.iloc[:30,0] = np.nan
    targets = build_targets(p,config(),False)
    np.testing.assert_array_equal(targets.iloc[:30,0],0)


def test_delay_changes_first_earned_return_and_final_liquidation_pays_cost():
    p = pd.DataFrame({'A':[100,102,104.04,106.1208], 'B':[100]*4},index=pd.date_range('2020-01-01',periods=4))
    targets = pd.DataFrame({'A':[.5,.5,.5,0], 'B':[-.5,-.5,-.5,0]},index=p.index)
    immediate = simulate(p,targets,10,0)
    delayed = simulate(p,targets,10,1)
    assert immediate.gross_return.iloc[0] == 0
    assert immediate.gross_return.iloc[1] == pytest.approx(.01)
    assert delayed.gross_return.iloc[:2].sum() == 0
    assert delayed.gross_return.iloc[2] == pytest.approx(.01)
    assert immediate.transaction_drag.iloc[0] > 0
    assert immediate.transaction_drag.iloc[-1] > 0
    assert immediate.gross_exposure.iloc[-1] == 0


def test_self_financing_cost_equation():
    drift = np.array([.4,-.2]);target = np.array([-.3,.3])
    fee,turnover = cost_fraction(drift,target,.001)
    assert fee == pytest.approx(turnover*.001)
    assert turnover == pytest.approx(np.abs(target*(1-fee)-drift).sum())


def test_nonzero_holdings_with_no_valuation_are_rejected():
    p = pd.DataFrame({'A':[np.nan,np.nan,100], 'B':[100,100,100]},index=pd.date_range('2020-01-01',periods=3))
    targets = pd.DataFrame({'A':[.5,.5,0], 'B':[-.5,-.5,0]},index=p.index)
    with pytest.raises(ValueError,match='valuation'):
        simulate(p,targets)
