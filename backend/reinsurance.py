import numpy as np
from scipy import stats


# ─────────────────────────────────────────────────────────────────────────────
# Sampling helpers
# ─────────────────────────────────────────────────────────────────────────────

def sample_from_dist(dist_name, params, n_samples):
    if dist_name == 'gamma':
        return stats.gamma.rvs(params['shape'], scale=params['scale'], size=n_samples)
    elif dist_name == 'lognorm':
        return stats.lognorm.rvs(params['shape'], scale=params['scale'], size=n_samples)
    elif dist_name == 'weibull':
        return stats.weibull_min.rvs(params['shape'], scale=params['scale'], size=n_samples)
    elif dist_name == 'pareto':
        u = np.random.uniform(size=n_samples)
        return params['scale'] / (1 - u) ** (1 / params['shape'])
    return np.array([])


def sample_freq(dist_name, params):
    if dist_name == 'poisson':
        return int(stats.poisson.rvs(params['lambda']))
    elif dist_name == 'neg_binomial':
        return int(stats.nbinom.rvs(params['r'], params['p']))
    elif dist_name == 'geometric':
        return int(max(stats.geom.rvs(params['p']) - 1, 0))
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Simulation
# ─────────────────────────────────────────────────────────────────────────────

def simuler_depuis_distributions(
    n_sims,
    below_sev_dist, below_sev_params,
    below_freq_dist, below_freq_params,
    above_sev_dist, above_sev_params,
    above_freq_dist, above_freq_params,
    seed=42,
):
    np.random.seed(seed)
    simulations = []
    for _ in range(n_sims):
        annee = {'below': [], 'above': []}
        if below_freq_params and below_sev_params:
            n_b = sample_freq(below_freq_dist, below_freq_params)
            if n_b > 0:
                annee['below'] = sample_from_dist(below_sev_dist, below_sev_params, n_b).tolist()
        if above_freq_params and above_sev_params:
            n_a = sample_freq(above_freq_dist, above_freq_params)
            if n_a > 0:
                annee['above'] = sample_from_dist(above_sev_dist, above_sev_params, n_a).tolist()
        simulations.append(annee)
    return simulations


# ─────────────────────────────────────────────────────────────────────────────
# Traités
# ─────────────────────────────────────────────────────────────────────────────

def _appliquer_traite_sinistres(sinistres, traite):
    if len(sinistres) == 0:
        return sinistres
    c = np.asarray(sinistres, dtype=float)
    if traite['type'] == 'QP':
        taux = float(traite['taux_retention'])
        if not (0.0 < taux <= 1.0):
            raise ValueError(f"Taux de rétention QP invalide : {taux}")
        return c * taux
    elif traite['type'] == 'XS':
        prio   = float(traite['priorite'])
        portee = float(traite['portee'])
        if prio < 0 or portee <= 0:
            raise ValueError(f"Paramètres XS invalides : priorité={prio}, portée={portee}")
        cession = np.minimum(np.maximum(c - prio, 0.0), portee)
        return c - cession
    else:
        raise ValueError(f"Type de traité inconnu : {traite['type']}")


def compute_charges(simulations, liste_traites):
    """Vecteur des charges nettes S-R par simulation."""
    charges = []
    for annee in simulations:
        if isinstance(annee, dict):
            below = np.asarray(annee.get('below', []), dtype=float)
            above = np.asarray(annee.get('above', []), dtype=float)
        else:
            below = np.asarray(annee, dtype=float)
            above = np.array([], dtype=float)
        for traite in liste_traites:
            below = _appliquer_traite_sinistres(below, traite)
            above = _appliquer_traite_sinistres(above, traite)
        charges.append(np.sum(below) + np.sum(above))
    return np.array(charges, dtype=float)


def compute_ceded_charges(simulations, liste_traites):
    """Retourne (gross_arr S, net_arr S-R) par simulation."""
    gross_list, net_list = [], []
    for annee in simulations:
        if isinstance(annee, dict):
            below = np.asarray(annee.get('below', []), dtype=float)
            above = np.asarray(annee.get('above', []), dtype=float)
        else:
            below = np.asarray(annee, dtype=float)
            above = np.array([], dtype=float)
        gross_total = float(np.sum(below) + np.sum(above))
        for traite in liste_traites:
            below = _appliquer_traite_sinistres(below, traite)
            above = _appliquer_traite_sinistres(above, traite)
        net_total = float(np.sum(below) + np.sum(above))
        gross_list.append(gross_total)
        net_list.append(net_total)
    return np.array(gross_list, dtype=float), np.array(net_list, dtype=float)


# ─────────────────────────────────────────────────────────────────────────────
# Principe de prime de réassurance (NOUVEAU)
# ─────────────────────────────────────────────────────────────────────────────

PREMIUM_PRINCIPLES = {
    'expected_value': "Valeur espérée  —  P_R = (1+θ)·E[R]",
    'std_deviation':  "Écart-type       —  P_R = E[R] + α·Std(R)",
    'variance':       "Variance         —  P_R = E[R] + α·Var(R)",
}

PREMIUM_DEFAULTS = {
    'expected_value': 0.20,
    'std_deviation':  0.20,
    'variance':       0.01,
}


def compute_premium(R_arr, principle, param):
    """
    Calcule la prime de réassurance P_R.
    R_arr : vecteur des montants cédés R_i = S_i - (S_i - R_i)
    Retourne (P_R, {'E_R', 'Std_R', 'Var_R'})
    """
    R = np.asarray(R_arr, dtype=float)
    E_R   = float(np.mean(R))
    Var_R = float(np.var(R, ddof=1))
    Std_R = float(np.std(R, ddof=1))
    p = float(param)
    if principle == 'expected_value':
        P_R = (1.0 + p) * E_R
    elif principle == 'std_deviation':
        P_R = E_R + p * Std_R
    elif principle == 'variance':
        P_R = E_R + p * Var_R
    else:
        raise ValueError(f"Principe inconnu : {principle}")
    return float(P_R), {'E_R': E_R, 'Std_R': Std_R, 'Var_R': Var_R}


# ─────────────────────────────────────────────────────────────────────────────
# Statistiques complètes brut / cédé / net avec prime (NOUVEAU)
# D = S - R + P_R
# ─────────────────────────────────────────────────────────────────────────────

def _var_tvar(arr, level):
    v = float(np.percentile(arr, level * 100))
    tail = arr[arr >= v]
    tv = float(np.mean(tail)) if len(tail) > 0 else v
    return v, tv


def compute_full_stats(simulations, liste_traites, principle='expected_value',
                       param=0.20, capital=None):
    """
    Retourne toutes les métriques brut/cédé/net avec D = S - R + P_R.

    Clés retournées :
      'gross'         métriques sur S
      'ceded'         métriques sur R
      'net'           métriques sur D = S-R+P_R
      'premium'       {P_R, principle, param, E_R, Std_R, Var_R}
      'profitability' {risk_reduction, cost_of_reins, expected_result_net}
      '_S', '_R', '_D' vecteurs numpy pour les graphiques
    """
    S_arr, net_no_prem = compute_ceded_charges(simulations, liste_traites)
    R_arr = S_arr - net_no_prem

    if liste_traites:
        P_R, meta = compute_premium(R_arr, principle, param)
    else:
        P_R  = 0.0
        meta = {'E_R': 0.0, 'Std_R': 0.0, 'Var_R': 0.0}

    D_arr = net_no_prem + P_R

    def _metrics(arr):
        v95,  tv95  = _var_tvar(arr, 0.95)
        v99,  tv99  = _var_tvar(arr, 0.99)
        v995, _     = _var_tvar(arr, 0.995)
        ruin = float(np.mean(arr > capital)) if capital is not None else None
        return {
            'mean':   float(np.mean(arr)),
            'std':    float(np.std(arr, ddof=1)),
            'var':    float(np.var(arr, ddof=1)),
            'var95':  v95,  'tvar95':  tv95,
            'var99':  v99,  'tvar99':  tv99,
            'var995': v995,
            'ruin':   ruin,
        }

    gross_m = _metrics(S_arr)
    ceded_m = _metrics(R_arr)
    net_m   = _metrics(D_arr)

    return {
        'gross':   gross_m,
        'ceded':   ceded_m,
        'net':     net_m,
        'premium': {
            'P_R':       P_R,
            'principle': principle,
            'param':     float(param),
            'E_R':       meta['E_R'],
            'Std_R':     meta['Std_R'],
            'Var_R':     meta['Var_R'],
        },
        'profitability': {
            'risk_reduction':      gross_m['tvar99'] - net_m['tvar99'],
            'cost_of_reins':       P_R,
            'expected_result_net': gross_m['mean'] - net_m['mean'],
        },
        '_S': S_arr,
        '_R': R_arr,
        '_D': D_arr,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Fonctions historiques — conservées pour compatibilité
# ─────────────────────────────────────────────────────────────────────────────

def appliquer_programme(simulations, liste_traites):
    charges = compute_charges(simulations, liste_traites)
    return float(np.mean(charges)), float(np.std(charges, ddof=1))


def stats_programme(simulations, liste_traites):
    """Retourne (esp, std, var95, var99, var995, tvar99) — 6 valeurs — sur S-R."""
    charges = compute_charges(simulations, liste_traites)
    esp    = float(np.mean(charges))
    std    = float(np.std(charges, ddof=1))
    var95  = float(np.percentile(charges, 95))
    var99  = float(np.percentile(charges, 99))
    var995 = float(np.percentile(charges, 99.5))
    tail   = charges[charges >= var99]
    tvar99 = float(np.mean(tail)) if len(tail) > 0 else var99
    return esp, std, var95, var99, var995, tvar99


def compute_return_period_values(charges, return_periods=(5, 10, 20, 50, 100, 200)):
    n = len(charges)
    sorted_ch = np.sort(charges)[::-1]
    result = {}
    for rp in return_periods:
        idx = max(0, min(n - 1, int(round(n / rp)) - 1))
        result[rp] = float(sorted_ch[idx])
    return result


def compute_oep_curve(charges):
    n = len(charges)
    sorted_charges = np.sort(charges)[::-1]
    ranks = np.arange(1, n + 1)
    return_periods = n / ranks
    return return_periods, sorted_charges


def compute_heatmap(simulations, prio_list, portee_list):
    matrix = np.zeros((len(portee_list), len(prio_list)))
    for j, prio in enumerate(prio_list):
        for i, portee in enumerate(portee_list):
            traite = [{'type': 'XS', 'priorite': float(prio), 'portee': float(portee)}]
            ch = compute_charges(simulations, traite)
            matrix[i, j] = float(np.mean(ch))
    return matrix


def formater_description(stack):
    if not stack:
        return "Brut (sans réassurance)"
    parts = []
    for t in stack:
        if t['type'] == 'QP':
            parts.append(f"QP {float(t['taux_retention'])*100:.0f}%")
        else:
            parts.append(f"XS {float(t['portee'])/1000:.0f}k xs {float(t['priorite'])/1000:.0f}k")
    return " + ".join(parts)
