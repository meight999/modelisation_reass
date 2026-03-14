import numpy as np
from scipy import stats


def sample_from_dist(dist_name, params, n_samples):
    """Tire n_samples sévérités depuis la distribution calibrée."""
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
    """Tire un entier depuis la loi de fréquence."""
    if dist_name == 'poisson':
        return int(stats.poisson.rvs(params['lambda']))
    elif dist_name == 'neg_binomial':
        return int(stats.nbinom.rvs(params['r'], params['p']))
    elif dist_name == 'geometric':
        return int(max(stats.geom.rvs(params['p']) - 1, 0))
    return 0


def simuler_depuis_distributions(
    n_sims,
    below_sev_dist, below_sev_params,
    below_freq_dist, below_freq_params,
    above_sev_dist, above_sev_params,
    above_freq_dist, above_freq_params,
    seed=42,
):
    """
    Génère n_sims années de sinistres par simulation fréquence × sévérité.

    Chaque année est un dict {'below': [sev1, sev2, ...], 'above': [sev1, ...]},
    avec below = sinistres attritionnels (sous le seuil) et above = sinistres graves.
    Les deux pools sont conservés séparément pour permettre l'application
    correcte des traités de réassurance par nature de sinistre.
    """
    np.random.seed(seed)
    simulations = []
    for _ in range(n_sims):
        annee = {'below': [], 'above': []}

        # Sinistres attritionnels (sous le seuil)
        if below_freq_params and below_sev_params:
            n_b = sample_freq(below_freq_dist, below_freq_params)
            if n_b > 0:
                sev_b = sample_from_dist(below_sev_dist, below_sev_params, n_b)
                annee['below'] = sev_b.tolist()

        # Sinistres graves (au-dessus du seuil)
        if above_freq_params and above_sev_params:
            n_a = sample_freq(above_freq_dist, above_freq_params)
            if n_a > 0:
                sev_a = sample_from_dist(above_sev_dist, above_sev_params, n_a)
                annee['above'] = sev_a.tolist()

        simulations.append(annee)
    return simulations


def _appliquer_traite_sinistres(sinistres, traite):
    """
    Applique un traité de réassurance à un vecteur de sinistres (numpy array).
    Retourne le vecteur net (charge retenue après cession).

    - QP  : rétention = taux_retention × montant brut par sinistre
    - XS  : net = brut - min(max(brut - priorite, 0), portee)  par sinistre
    """
    if len(sinistres) == 0:
        return sinistres
    c = np.asarray(sinistres, dtype=float)
    if traite['type'] == 'QP':
        taux = float(traite['taux_retention'])
        if not (0.0 < taux <= 1.0):
            raise ValueError(f"Taux de rétention QP invalide : {taux} (attendu dans ]0, 1])")
        return c * taux
    elif traite['type'] == 'XS':
        prio = float(traite['priorite'])
        portee = float(traite['portee'])
        if prio < 0 or portee <= 0:
            raise ValueError(f"Paramètres XS invalides : priorité={prio}, portée={portee}")
        cession = np.minimum(np.maximum(c - prio, 0.0), portee)
        return c - cession
    else:
        raise ValueError(f"Type de traité inconnu : {traite['type']}")


def compute_charges(simulations, liste_traites):
    """
    Calcule le vecteur complet des charges nettes annuelles après application du programme.
    Utilisé par appliquer_programme et stats_programme.
    """
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


def appliquer_programme(simulations, liste_traites):
    """Retourne (espérance, écart-type) des charges nettes annuelles."""
    charges = compute_charges(simulations, liste_traites)
    return float(np.mean(charges)), float(np.std(charges, ddof=1))


def stats_programme(simulations, liste_traites):
    """
    Retourne (espérance, écart-type, VaR95, VaR99, TVaR99) des charges nettes.
    TVaR99 = moyenne conditionnelle au-delà du quantile 99%.
    """
    charges = compute_charges(simulations, liste_traites)
    esp  = float(np.mean(charges))
    std  = float(np.std(charges, ddof=1))
    var95 = float(np.percentile(charges, 95))
    var99 = float(np.percentile(charges, 99))
    tail  = charges[charges >= var99]
    tvar99 = float(np.mean(tail)) if len(tail) > 0 else var99
    return esp, std, var95, var99, tvar99


def compute_ceded_charges(simulations, liste_traites):
    """
    Retourne (gross_arr, net_arr) : charge brute et charge nette par simulation.
    La différence gross - net = montant cédé.
    """
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


def compute_oep_curve(charges):
    """
    Retourne (return_periods, sorted_charges) pour la courbe d'excédance de pertes.
    Période de retour = n_simulations / rang (du plus grand au plus petit).
    """
    n = len(charges)
    sorted_charges = np.sort(charges)[::-1]
    ranks = np.arange(1, n + 1)
    return_periods = n / ranks
    return return_periods, sorted_charges


def compute_heatmap(simulations, prio_list, portee_list):
    """
    Calcule la matrice des charges nettes moyennes pour une grille (priorité × portée).
    Rows = portée, Cols = priorité.
    """
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
