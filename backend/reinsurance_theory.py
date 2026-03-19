"""
Theoretical reinsurance optimization.
Scenario 1: Expected Value Premium  → Stop-Loss optimal
Scenario 2: Variance Premium        → Quote-Share optimal
"""
import numpy as np
from scipy import stats, optimize


# ─── Distribution helpers ─────────────────────────────────────────────────────

def _dist(name, p):
    if name == 'exponential':
        return stats.expon(scale=p['mean'])
    elif name == 'lognormal':
        return stats.lognorm(s=p['sigma'], scale=np.exp(p['mu']))
    elif name == 'gamma':
        return stats.gamma(a=p['alpha'], scale=p['beta'])
    raise ValueError(f"Unknown dist: {name}")


def moments(name, p):
    d = _dist(name, p)
    return float(d.mean()), float(d.var())


def sample(name, p, n=8000, seed=42):
    np.random.seed(seed)
    return _dist(name, p).rvs(n)


def _ppf(name, p, q):
    return float(_dist(name, p).ppf(min(q, 0.99999)))


def _pdf(name, p, x):
    return _dist(name, p).pdf(x)


def _cdf(name, p, x):
    return _dist(name, p).cdf(x)


# ─── E[(S-b)_+] — closed form for Expo & LN ─────────────────────────────────

def e_sl(name, p, b):
    if b <= 0:
        return moments(name, p)[0]
    if name == 'exponential':
        m = p['mean']
        return float(m * np.exp(-b / m))
    elif name == 'lognormal':
        mu, sig = p['mu'], p['sigma']
        mean_s = np.exp(mu + sig ** 2 / 2)
        lb = np.log(max(b, 1e-10))
        d1 = (mu + sig ** 2 - lb) / sig
        d2 = (mu - lb) / sig
        return float(mean_s * stats.norm.cdf(d1) - b * stats.norm.cdf(d2))
    else:  # gamma — numerical
        q_hi = _ppf(name, p, 0.9999)
        xs = np.linspace(b, max(q_hi, b * 1.01 + 1), 2000)
        return float(np.trapezoid((xs - b) * _pdf(name, p, xs), xs))


# ─── E[min(S,b)^2] — closed form for Expo & LN ──────────────────────────────

def _e_min_sq(name, p, b):
    if name == 'exponential':
        m = p['mean']
        return float(2 * m ** 2 * (1 - np.exp(-b / m) * (1 + b / m)))
    elif name == 'lognormal':
        mu, sig = p['mu'], p['sigma']
        lb = np.log(max(b, 1e-10))
        d_below = (lb - mu - 2 * sig ** 2) / sig
        e_s2_below = np.exp(2 * mu + 2 * sig ** 2) * stats.norm.cdf(d_below)
        p_above = 1 - stats.norm.cdf((lb - mu) / sig)
        return float(e_s2_below + b ** 2 * p_above)
    else:  # gamma — numerical ∫_0^b 2x(1-F(x))dx
        xs = np.linspace(0, b, 2000)
        return float(np.trapezoid(2 * xs * (1 - _cdf(name, p, xs)), xs))


def var_retained_sl(name, p, b):
    """Var(min(S, b)) = Var(D) under Stop-Loss."""
    mean_s, _ = moments(name, p)
    er = e_sl(name, p, b)
    e_min = mean_s - er
    e_min2 = _e_min_sq(name, p, b)
    return max(0.0, e_min2 - e_min ** 2)


# ─── E[(S-b)_+^2] — closed form for Expo & LN ───────────────────────────────

def _e_ceded_sq(name, p, b):
    if name == 'exponential':
        m = p['mean']
        return float(2 * m ** 2 * np.exp(-b / m))
    elif name == 'lognormal':
        mu, sig = p['mu'], p['sigma']
        lb = np.log(max(b, 1e-10))
        d0 = (mu - lb) / sig
        d1 = d0 + sig
        d2 = d0 + 2 * sig
        e_s2_above = np.exp(2 * mu + 2 * sig ** 2) * stats.norm.cdf(d2)
        e_s1_above = np.exp(mu + sig ** 2 / 2) * stats.norm.cdf(d1)
        p_above = stats.norm.cdf(d0)
        return float(e_s2_above - 2 * b * e_s1_above + b ** 2 * p_above)
    else:  # gamma — numerical
        q_hi = _ppf(name, p, 0.9999)
        xs = np.linspace(b, max(q_hi, b * 1.01 + 1), 2000)
        return float(np.trapezoid((xs - b) ** 2 * _pdf(name, p, xs), xs))


def var_ceded_sl(name, p, b):
    """Var((S-b)_+) = Var(R) under Stop-Loss."""
    er = e_sl(name, p, b)
    er2 = _e_ceded_sq(name, p, b)
    return max(0.0, er2 - er ** 2)


# ─── Root finding ─────────────────────────────────────────────────────────────

def find_b_from_er(name, p, er_target):
    """Find b s.t. E[(S-b)_+] = er_target."""
    mean_s, _ = moments(name, p)
    if er_target <= 1e-10:
        return float('inf')
    if er_target >= mean_s * 0.9999:
        return 0.0
    try:
        b_hi = _ppf(name, p, 0.99999)
        b = float(optimize.brentq(
            lambda b: e_sl(name, p, b) - er_target,
            0.0, b_hi, xtol=1.0, maxiter=200,
        ))
    except Exception:
        b = mean_s
    return b


def find_b_from_var_r(name, p, var_r_target):
    """Find b s.t. Var((S-b)_+) = var_r_target."""
    _, var_s = moments(name, p)
    if var_r_target <= 0:
        return float('inf')
    if var_r_target >= var_s * 0.9999:
        return 0.0
    try:
        b_hi = _ppf(name, p, 0.9999)
        vc0 = var_ceded_sl(name, p, 0.0)
        if vc0 < var_r_target:
            return 0.0
        b = float(optimize.brentq(
            lambda b: var_ceded_sl(name, p, b) - var_r_target,
            0.0, b_hi, xtol=1.0, maxiter=200,
        ))
    except Exception:
        return None
    return b


# ─── Scenario 1: Expected Value Premium ──────────────────────────────────────

def scenario1(name, p, theta, er_frac):
    """
    theta: chargement θ ∈ [0,1]
    er_frac: E[R]/E[S] ∈ [0,1]
    """
    mean_s, var_s = moments(name, p)
    er_target = er_frac * mean_s
    b_opt = find_b_from_er(name, p, er_target)
    var_sl = var_retained_sl(name, p, b_opt) if np.isfinite(b_opt) else var_s
    # QS with same E[R]: a = er_frac
    a_qs = er_frac
    var_qs = (1 - a_qs) ** 2 * var_s
    return {
        'b_opt': b_opt,
        'var_sl': var_sl,
        'var_qs': var_qs,
        'e_d': mean_s - er_target,
        'a_qs': a_qs,
        'er_target': er_target,
        'premium': (1 + theta) * er_target,
        'mean_s': mean_s,
        'var_s': var_s,
        'gain_pct': (var_qs - var_sl) / var_qs * 100 if var_qs > 0 else 0.0,
    }


# ─── Scenario 2: Variance Premium ────────────────────────────────────────────

def scenario2(name, p, q_frac, alpha_v):
    """
    q_frac: Var(R)/Var(S) ∈ [0,1]
    alpha_v: chargement de variance
    """
    mean_s, var_s = moments(name, p)
    var_r_target = q_frac * var_s
    a_opt = min(float(np.sqrt(q_frac)), 1.0)
    var_qs = (1 - a_opt) ** 2 * var_s
    er_qs = a_opt * mean_s
    premium = er_qs + alpha_v * var_r_target

    b_sl = find_b_from_var_r(name, p, var_r_target)
    if b_sl is not None and np.isfinite(b_sl):
        var_sl = var_retained_sl(name, p, b_sl)
        er_sl = e_sl(name, p, b_sl)
    else:
        var_sl, er_sl, b_sl = None, None, None

    s_arr = sample(name, p)
    cor_qs = 1.0
    cor_sl = None
    if b_sl is not None:
        r_sl = np.maximum(s_arr - b_sl, 0.0)
        if np.std(r_sl) > 0:
            cor_sl = float(np.corrcoef(s_arr, r_sl)[0, 1])

    return {
        'a_opt': a_opt,
        'var_qs': var_qs,
        'var_sl': var_sl,
        'b_sl': b_sl,
        'er_sl': er_sl,
        'cor_qs': cor_qs,
        'cor_sl': cor_sl,
        'e_d': (1 - a_opt) * mean_s,
        'mean_s': mean_s,
        'var_s': var_s,
        'var_r_target': var_r_target,
        'premium': premium,
        'gain_pct': (var_sl - var_qs) / var_sl * 100 if (var_sl and var_sl > 0) else 0.0,
        's_samples': s_arr,
    }
