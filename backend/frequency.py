import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.special import gammaln


def fit_poisson(counts):
    lam = np.mean(counts)
    loglik = np.sum(stats.poisson.logpmf(counts, lam))
    n = len(counts)
    return {'lambda': lam}, loglik, 2-2*loglik, np.log(n)-2*loglik


def fit_negative_binomial(counts):
    mean = np.mean(counts); var = np.var(counts)
    r_init = max(0.1, mean**2/max(var-mean, 0.01))
    def neg_loglik(params):
        r = params[0]
        if r <= 0: return np.inf
        p = r/(r+mean)
        return -np.sum(gammaln(r+counts)-gammaln(r)-gammaln(counts+1)+r*np.log(p)+counts*np.log(1-p))
    result = minimize(neg_loglik, [r_init], method='L-BFGS-B', bounds=[(0.01, 1e4)])
    if not result.success: return None, None, None, None
    r = result.x[0]; p = r/(r+mean); loglik = -result.fun; n = len(counts)
    return {'r': r, 'p': p, 'mean': mean}, loglik, 4-2*loglik, 2*np.log(n)-2*loglik


def fit_geometric(counts):
    p = 1/(1+np.mean(counts))
    loglik = np.sum(stats.geom.logpmf(counts+1, p))
    n = len(counts)
    return {'p': p}, loglik, 2-2*loglik, np.log(n)-2*loglik


def analyze_frequency(counts):
    if counts is None or len(counts) < 3:
        return None
    counts = np.array(counts, dtype=float)
    results = {}
    for name, fn in [('poisson', fit_poisson), ('neg_binomial', fit_negative_binomial), ('geometric', fit_geometric)]:
        try:
            params, loglik, aic, bic = fn(counts)
            if params and np.isfinite(loglik):
                results[name] = {'params': params, 'loglik': loglik, 'aic': aic, 'bic': bic}
        except Exception:
            pass
    return results if results else None


def compute_counts_from_dates(dates_series, threshold_mask, start_date=None):
    dates = pd.to_datetime(dates_series, errors='coerce')
    # Aligner les deux séries sur le même index
    common_index = dates.index.intersection(threshold_mask.index)
    dates = dates.loc[common_index]
    threshold_mask = threshold_mask.loc[common_index]

    valid_mask = ~dates.isna()
    if start_date:
        try:
            valid_mask = valid_mask & (dates.dt.year >= int(start_date))
        except Exception:
            pass

    filtered_dates = dates[valid_mask & threshold_mask]
    if len(filtered_dates) == 0:
        return None, None

    period_counts = filtered_dates.dt.to_period('Y').value_counts().sort_index()
    if len(period_counts) > 1:
        all_periods = pd.period_range(period_counts.index.min(), period_counts.index.max(), freq='Y')
        period_counts = period_counts.reindex(all_periods, fill_value=0)
    return period_counts.values, [str(p) for p in period_counts.index]


def get_freq_pmf(dist_name, params, x_vals):
    """Retourne la PMF pour les x_vals donnés."""
    try:
        if dist_name == 'poisson':
            return stats.poisson.pmf(x_vals, params['lambda'])
        elif dist_name == 'neg_binomial':
            return stats.nbinom.pmf(x_vals, params['r'], params['p'])
        elif dist_name == 'geometric':
            return stats.geom.pmf(x_vals + 1, params['p'])
    except Exception:
        pass
    return np.zeros(len(x_vals))


def get_freq_cmf(dist_name, params, x_vals):
    """Retourne la CDF cumulée pour les x_vals donnés."""
    try:
        if dist_name == 'poisson':
            return stats.poisson.cdf(x_vals, params['lambda'])
        elif dist_name == 'neg_binomial':
            return stats.nbinom.cdf(x_vals, params['r'], params['p'])
        elif dist_name == 'geometric':
            return stats.geom.cdf(x_vals + 1, params['p'])
    except Exception:
        pass
    return np.zeros(len(x_vals))
