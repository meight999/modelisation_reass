import numpy as np
from scipy import stats
from scipy.optimize import minimize


def pareto_pdf(x, shape, scale):
    return shape * scale**shape / (x**(shape + 1))


def pareto_cdf(x, shape, scale):
    return 1 - (scale / x)**shape


def pareto_quantile(p, shape, scale):
    return scale / (1 - p)**(1/shape)


def fit_pareto(data):
    scale = np.min(data)
    def neg_loglik(params):
        s = params[0]
        if s <= 0: return np.inf
        return -np.sum(np.log(pareto_pdf(data, s, scale)))
    result = minimize(neg_loglik, [1.5], method='L-BFGS-B', bounds=[(0.1, 10)])
    if result.success:
        return {'shape': result.x[0], 'scale': scale}
    return None


def safe_fit_distribution(data, dist_name):
    # MLE sur TOUTES les données — sous-échantillonner biaise les estimateurs
    try:
        if dist_name == 'gamma':
            shape, loc, scale = stats.gamma.fit(data, floc=0)
            params = {'shape': shape, 'scale': scale}
            loglik = np.sum(stats.gamma.logpdf(data, shape, loc=0, scale=scale))
        elif dist_name == 'lognorm':
            shape, loc, scale = stats.lognorm.fit(data, floc=0)
            params = {'shape': shape, 'scale': scale}
            loglik = np.sum(stats.lognorm.logpdf(data, shape, loc=0, scale=scale))
        elif dist_name == 'weibull':
            shape, loc, scale = stats.weibull_min.fit(data, floc=0)
            params = {'shape': shape, 'scale': scale}
            loglik = np.sum(stats.weibull_min.logpdf(data, shape, loc=0, scale=scale))
        elif dist_name == 'pareto':
            params = fit_pareto(data)
            if params is None:
                return None
            loglik = np.sum(np.log(pareto_pdf(data, params['shape'], params['scale'])))
        else:
            return None
        if not np.isfinite(loglik):
            return None
        k = len(params); n = len(data)
        return {'params': params, 'loglik': loglik, 'aic': 2*k - 2*loglik, 'bic': k*np.log(n) - 2*loglik}
    except Exception:
        return None


def compute_gof_stats(data, fit_result, dist_name):
    params = fit_result['params']
    sorted_data = np.sort(data)
    if dist_name == 'gamma':
        ks_stat, ks_pval = stats.kstest(data, lambda x: stats.gamma.cdf(x, params['shape'], scale=params['scale']))
        cdf_vals = stats.gamma.cdf(sorted_data, params['shape'], scale=params['scale'])
    elif dist_name == 'lognorm':
        ks_stat, ks_pval = stats.kstest(data, lambda x: stats.lognorm.cdf(x, params['shape'], scale=params['scale']))
        cdf_vals = stats.lognorm.cdf(sorted_data, params['shape'], scale=params['scale'])
    elif dist_name == 'weibull':
        ks_stat, ks_pval = stats.kstest(data, lambda x: stats.weibull_min.cdf(x, params['shape'], scale=params['scale']))
        cdf_vals = stats.weibull_min.cdf(sorted_data, params['shape'], scale=params['scale'])
    elif dist_name == 'pareto':
        ks_stat, ks_pval = stats.kstest(data, lambda x: pareto_cdf(x, params['shape'], params['scale']))
        cdf_vals = np.array([pareto_cdf(x, params['shape'], params['scale']) for x in sorted_data])
    else:
        return float('nan'), float('nan'), float('nan')
    cdf_vals = np.clip(cdf_vals, 1e-10, 1-1e-10)
    n = len(data); i = np.arange(1, n+1)
    ad_stat = -n - np.sum((2*i-1)/n*(np.log(cdf_vals)+np.log(1-cdf_vals[::-1])))
    return ks_stat, ad_stat, ks_pval


def analyze_segment_data(data):
    if len(data) < 20: return None
    fits = {}
    for dist in ['gamma', 'lognorm', 'weibull', 'pareto']:
        r = safe_fit_distribution(data, dist)
        if r: fits[dist] = r
    return fits if fits else None
