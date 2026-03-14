import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
import base64
import io
from scipy import stats
from scipy.optimize import minimize
from scipy.special import gammaln

print("Démarrage de l'application fusionnée...")

# ============================================================
# BACKEND — SÉVÉRITÉ
# ============================================================

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
    try:
        sample = np.random.choice(data, size=min(5000, len(data)), replace=False) if len(data) > 5000 else data
        if dist_name == 'gamma':
            shape, loc, scale = stats.gamma.fit(sample, floc=0)
            params = {'shape': shape, 'scale': scale}
            loglik = np.sum(stats.gamma.logpdf(data, shape, loc=0, scale=scale))
        elif dist_name == 'lognorm':
            shape, loc, scale = stats.lognorm.fit(sample, floc=0)
            params = {'shape': shape, 'scale': scale}
            loglik = np.sum(stats.lognorm.logpdf(data, shape, loc=0, scale=scale))
        elif dist_name == 'weibull':
            shape, loc, scale = stats.weibull_min.fit(sample, floc=0)
            params = {'shape': shape, 'scale': scale}
            loglik = np.sum(stats.weibull_min.logpdf(data, shape, loc=0, scale=scale))
        elif dist_name == 'pareto':
            params = fit_pareto(sample)
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

# ============================================================
# BACKEND — FRÉQUENCE
# ============================================================

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

FREQ_DIST_NAMES = {'poisson': 'Poisson', 'neg_binomial': 'Binomiale Négative', 'geometric': 'Géométrique'}
FREQ_COLORS = {'poisson': '#E55039', 'neg_binomial': '#2E86C1', 'geometric': '#D4AC0D'}
SEV_DIST_NAMES = {'gamma': 'Gamma', 'lognorm': 'Lognormale', 'weibull': 'Weibull', 'pareto': 'Pareto'}
SEV_COLORS = {'gamma': '#E55039', 'lognorm': '#2E86C1', 'weibull': '#D4AC0D', 'pareto': '#7D3C98'}

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

# ============================================================
# BACKEND — RÉASSURANCE
# ============================================================

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


def appliquer_programme(simulations, liste_traites):
    """
    Applique un programme de réassurance (stack de traités) aux simulations.

    Les traités sont appliqués séquentiellement sur chaque sinistre individuel,
    pour chaque pool (below/above) séparément, puis on somme la charge nette annuelle.

    simulations : liste de dicts {'below': [...], 'above': [...]}
    liste_traites : liste de dicts décrivant chaque couche du programme

    Retourne (espérance, écart-type) des charges nettes annuelles.
    """
    charges = []
    for annee in simulations:
        # Compatibilité : si l'année est un dict (nouveau format) ou une liste (ancien format)
        if isinstance(annee, dict):
            below = np.asarray(annee.get('below', []), dtype=float)
            above = np.asarray(annee.get('above', []), dtype=float)
        else:
            # Ancien format (liste plate) — fallback
            below = np.asarray(annee, dtype=float)
            above = np.array([], dtype=float)

        # Appliquer chaque traité séquentiellement sur les deux pools
        for traite in liste_traites:
            below = _appliquer_traite_sinistres(below, traite)
            above = _appliquer_traite_sinistres(above, traite)

        charge_nette = np.sum(below) + np.sum(above)
        charges.append(charge_nette)

    charges = np.array(charges, dtype=float)
    return float(np.mean(charges)), float(np.std(charges, ddof=1))


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

# ============================================================
# COMPOSANTS UI RÉUTILISABLES
# ============================================================

PALETTE = {
    'bg': '#0F1923',
    'surface': '#1A2535',
    'surface2': '#243044',
    'accent': '#00D4B4',
    'accent2': '#0099FF',
    'danger': '#FF4D6D',
    'warning': '#FFB703',
    'success': '#06D6A0',
    'text': '#E8EDF5',
    'text_muted': '#7A8BA0',
    'border': '#2D4060',
}

def card(children, style=None, **kwargs):
    base = {
        'backgroundColor': PALETTE['surface'],
        'border': f"1px solid {PALETTE['border']}",
        'borderRadius': '12px',
        'padding': '24px',
    }
    if style: base.update(style)
    return html.Div(children, style=base, **kwargs)

def section_title(text, color=None):
    return html.Div([
        html.Span(text, style={
            'fontSize': '13px',
            'fontWeight': '700',
            'letterSpacing': '2px',
            'textTransform': 'uppercase',
            'color': color or PALETTE['accent'],
        })
    ], style={'borderBottom': f"1px solid {PALETTE['border']}", 'paddingBottom': '12px', 'marginBottom': '18px'})

def stat_badge(label, value, color=None):
    return html.Div([
        html.Div(value, style={'fontSize': '22px', 'fontWeight': '700', 'color': color or PALETTE['accent'], 'fontFamily': "'Courier New', monospace"}),
        html.Div(label, style={'fontSize': '11px', 'color': PALETTE['text_muted'], 'letterSpacing': '1px', 'textTransform': 'uppercase', 'marginTop': '2px'}),
    ], style={
        'backgroundColor': PALETTE['surface2'],
        'border': f"1px solid {PALETTE['border']}",
        'borderRadius': '8px',
        'padding': '14px 18px',
        'minWidth': '130px',
        'textAlign': 'center',
    })

def btn_primary(text, id, style=None):
    base = {
        'backgroundColor': PALETTE['accent'],
        'color': '#000',
        'border': 'none',
        'borderRadius': '8px',
        'padding': '10px 22px',
        'cursor': 'pointer',
        'fontWeight': '700',
        'fontSize': '13px',
        'letterSpacing': '1px',
        'textTransform': 'uppercase',
        'width': '100%',
    }
    if style: base.update(style)
    return html.Button(text, id=id, n_clicks=0, style=base)

def btn_secondary(text, id, color=None, style=None):
    base = {
        'backgroundColor': 'transparent',
        'color': color or PALETTE['accent2'],
        'border': f"1px solid {color or PALETTE['accent2']}",
        'borderRadius': '8px',
        'padding': '8px 16px',
        'cursor': 'pointer',
        'fontWeight': '600',
        'fontSize': '12px',
        'width': '100%',
    }
    if style: base.update(style)
    return html.Button(text, id=id, n_clicks=0, style=base)

def make_table(data, columns, highlight_first=False):
    cond = [
        {'if': {'row_index': 'odd'}, 'backgroundColor': PALETTE['surface2']},
    ]
    if highlight_first:
        cond.append({'if': {'row_index': 0}, 'backgroundColor': '#1A3A2A', 'color': PALETTE['success'], 'fontWeight': '700'})
    return dash_table.DataTable(
        data=data, columns=columns,
        style_table={'borderRadius': '8px', 'overflow': 'hidden', 'border': f"1px solid {PALETTE['border']}"},
        style_cell={'textAlign': 'center', 'padding': '10px 14px', 'fontSize': '13px',
                    'backgroundColor': PALETTE['surface'], 'color': PALETTE['text'],
                    'border': f"1px solid {PALETTE['border']}", 'fontFamily': "'Courier New', monospace"},
        style_header={'backgroundColor': PALETTE['surface2'], 'color': PALETTE['accent'],
                      'fontWeight': '700', 'fontSize': '12px', 'letterSpacing': '1px',
                      'textTransform': 'uppercase', 'border': f"1px solid {PALETTE['border']}"},
        style_data_conditional=cond,
    )

def plotly_layout(title="", height=450):
    return dict(
        title=dict(text=title, font=dict(color=PALETTE['text'], size=15, family="'Courier New', monospace")),
        paper_bgcolor=PALETTE['surface'],
        plot_bgcolor=PALETTE['surface2'],
        font=dict(color=PALETTE['text_muted'], size=12),
        height=height,
        margin=dict(l=50, r=30, t=50, b=50),
        xaxis=dict(gridcolor=PALETTE['border'], linecolor=PALETTE['border'], zerolinecolor=PALETTE['border']),
        yaxis=dict(gridcolor=PALETTE['border'], linecolor=PALETTE['border'], zerolinecolor=PALETTE['border']),
        legend=dict(bgcolor=PALETTE['surface'], bordercolor=PALETTE['border'], borderwidth=1,
                    font=dict(color=PALETTE['text'])),
        hovermode='closest',
    )

# ============================================================
# VUES SÉVÉRITÉ
# ============================================================

def view_severite_details(data, fits_data, threshold, segment_label):
    if fits_data is None or data is None:
        return html.Div("Analysez d'abord les données.", style={'color': PALETTE['text_muted'], 'padding': '40px', 'textAlign': 'center'})
    arr = np.array(data)
    badges = html.Div([
        stat_badge("Observations", str(len(arr))),
        stat_badge("Moyenne", f"{np.mean(arr):,.0f}"),
        stat_badge("Médiane", f"{np.median(arr):,.0f}"),
        stat_badge("Écart-type", f"{np.std(arr):,.0f}"),
        stat_badge("Min", f"{np.min(arr):,.0f}"),
        stat_badge("Max", f"{np.max(arr):,.0f}"),
        stat_badge("CV", f"{np.std(arr)/np.mean(arr):.3f}"),
        stat_badge("Q75", f"{np.percentile(arr, 75):,.0f}"),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '12px', 'marginBottom': '24px'})

    params_rows = []
    for dist, result in fits_data.items():
        row = {'Modèle': SEV_DIST_NAMES[dist]}
        for k, v in result['params'].items():
            row[k.capitalize()] = f"{v:.4f}"
        row['LogLik'] = f"{result['loglik']:.2f}"
        row['AIC'] = f"{result['aic']:.2f}"
        row['BIC'] = f"{result['bic']:.2f}"
        params_rows.append(row)

    params_rows_sorted = sorted(params_rows, key=lambda x: float(x['AIC']))
    cols_set = set()
    for r in params_rows_sorted: cols_set.update(r.keys())
    ordered_cols = ['Modèle'] + sorted(c for c in cols_set if c not in ('Modèle', 'AIC', 'BIC', 'LogLik')) + ['LogLik', 'AIC', 'BIC']
    cols = [{'name': c, 'id': c} for c in ordered_cols if c in cols_set]

    return html.Div([badges, make_table(params_rows_sorted, cols, highlight_first=True)])

def view_severite_ecdf(data, fits_data, threshold):
    if fits_data is None or data is None:
        return html.Div("Analysez d'abord les données.", style={'color': PALETTE['text_muted'], 'padding': '40px'})
    arr = np.array(data)
    x_emp = np.sort(arr); y_emp = np.arange(1, len(arr)+1)/len(arr)
    x_range = np.linspace(np.min(arr), np.max(arr), 500)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_emp, y=y_emp, mode='lines', name='Empirique',
                             line=dict(color=PALETTE['text'], width=3)))
    for dist, result in fits_data.items():
        p = result['params']
        if dist == 'gamma': y = stats.gamma.cdf(x_range, p['shape'], scale=p['scale'])
        elif dist == 'lognorm': y = stats.lognorm.cdf(x_range, p['shape'], scale=p['scale'])
        elif dist == 'weibull': y = stats.weibull_min.cdf(x_range, p['shape'], scale=p['scale'])
        elif dist == 'pareto': y = pareto_cdf(x_range, p['shape'], p['scale'])
        fig.add_trace(go.Scatter(x=x_range, y=y, mode='lines', name=SEV_DIST_NAMES[dist],
                                 line=dict(color=SEV_COLORS[dist], width=2)))
    layout = plotly_layout(f"ECDF — Seuil : {threshold:,}", height=480)
    layout['xaxis']['title'] = "Montant du sinistre"
    layout['yaxis']['title'] = "Probabilité cumulée"
    fig.update_layout(layout)

    comp = []
    for dist, result in fits_data.items():
        ks_stat, ad_stat, ks_pval = compute_gof_stats(arr, result, dist)
        comp.append({'Modèle': SEV_DIST_NAMES[dist], 'AIC': f"{result['aic']:.2f}",
                     'BIC': f"{result['bic']:.2f}", 'KS': f"{ks_stat:.4f}",
                     'KS p-val': f"{ks_pval:.4f}" if ks_pval >= 0.0001 else f"{ks_pval:.2e}",
                     'AD': f"{ad_stat:.4f}"})
    comp_sorted = sorted(comp, key=lambda x: float(x['AIC']))
    return html.Div([
        dcc.Graph(figure=fig),
        html.Div([
            html.Span("⭐ Meilleur AIC : ", style={'color': PALETTE['text_muted'], 'fontSize': '13px'}),
            html.Span(comp_sorted[0]['Modèle'], style={'color': PALETTE['success'], 'fontWeight': '700'}),
        ], style={'marginBottom': '12px'}),
        make_table(comp_sorted, [{'name': c, 'id': c} for c in comp_sorted[0].keys()], highlight_first=True),
    ])

def view_severite_qq(data, fits_data, threshold):
    if fits_data is None or data is None:
        return html.Div("Analysez d'abord les données.", style={'color': PALETTE['text_muted'], 'padding': '40px'})
    arr = np.array(data)
    arr = arr[arr > 0]  # log scale requires strictly positive values
    sample = np.random.choice(arr, size=min(1500, len(arr)), replace=False)
    q_emp = np.sort(sample.astype(float))
    n = len(q_emp); p = np.linspace(1/(n+1), n/(n+1), n)
    fig = go.Figure()
    all_pts = []
    for dist, result in fits_data.items():
        pp = result['params']
        if dist == 'gamma': q_theo = stats.gamma.ppf(p, pp['shape'], scale=pp['scale'])
        elif dist == 'lognorm': q_theo = stats.lognorm.ppf(p, pp['shape'], scale=pp['scale'])
        elif dist == 'weibull': q_theo = stats.weibull_min.ppf(p, pp['shape'], scale=pp['scale'])
        elif dist == 'pareto': q_theo = pareto_quantile(p, pp['shape'], pp['scale'])
        else: continue
        q_theo = np.asarray(q_theo, dtype=float)
        mask = np.isfinite(q_theo) & np.isfinite(q_emp) & (q_theo > 0) & (q_emp > 0)
        fig.add_trace(go.Scatter(x=q_theo[mask], y=q_emp[mask], mode='markers',
                                 name=SEV_DIST_NAMES[dist],
                                 marker=dict(size=5, opacity=0.7, color=SEV_COLORS[dist])))
        all_pts.extend(q_theo[mask].tolist()); all_pts.extend(q_emp[mask].tolist())
    if all_pts:
        lo, hi = np.nanpercentile(all_pts, 1), np.nanpercentile(all_pts, 99)
        lo = max(lo, 1e-6)  # éviter 0 en log
        fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode='lines', name='y = x',
                                 line=dict(color=PALETTE['warning'], dash='dash', width=2)))
    layout = plotly_layout("QQ-Plots — Théorique vs Empirique (échelle log)", height=480)
    layout['xaxis']['title'] = "Quantiles théoriques (log)"
    layout['xaxis']['type'] = 'log'
    layout['yaxis']['title'] = "Quantiles empiriques (log)"
    layout['yaxis']['type'] = 'log'
    fig.update_layout(layout)

    probs = [0.50, 0.75, 0.90, 0.95, 0.99]
    q_emp_t = np.quantile(arr, probs)
    quant_rows = [{'Modèle': 'Empirique', **{f'Q{int(p*100)}': f"{q_emp_t[i]:,.2f}" for i, p in enumerate(probs)}}]
    for dist, result in fits_data.items():
        pp = result['params']
        if dist == 'gamma': qt = [stats.gamma.ppf(p, pp['shape'], scale=pp['scale']) for p in probs]
        elif dist == 'lognorm': qt = [stats.lognorm.ppf(p, pp['shape'], scale=pp['scale']) for p in probs]
        elif dist == 'weibull': qt = [stats.weibull_min.ppf(p, pp['shape'], scale=pp['scale']) for p in probs]
        elif dist == 'pareto': qt = [pareto_quantile(p, pp['shape'], pp['scale']) for p in probs]
        row = {'Modèle': SEV_DIST_NAMES[dist]}
        for i, p in enumerate(probs):
            err = (qt[i]-q_emp_t[i])/q_emp_t[i]*100 if q_emp_t[i] != 0 else 0
            row[f'Q{int(p*100)}'] = f"{qt[i]:,.2f} ({err:+.1f}%)"
        quant_rows.append(row)
    return html.Div([
        dcc.Graph(figure=fig),
        html.H4("Tableau des Quantiles", style={'color': PALETTE['accent'], 'marginTop': '20px', 'fontSize': '13px', 'letterSpacing': '2px', 'textTransform': 'uppercase'}),
        make_table(quant_rows, [{'name': c, 'id': c} for c in quant_rows[0].keys()]),
    ])

# ============================================================
# VUES FRÉQUENCE
# ============================================================

def view_freq_details(counts, fits):
    if counts is None:
        return html.Div("Sélectionnez une colonne de date pour l'analyse de fréquence.", style={'color': PALETTE['text_muted'], 'padding': '40px', 'textAlign': 'center'})
    arr = np.array(counts)
    mean_c = np.mean(arr); var_c = np.var(arr, ddof=1) if len(arr)>1 else 0
    badges = html.Div([
        stat_badge("Années", str(len(arr))),
        stat_badge("Moy. annuelle", f"{mean_c:.2f}"),
        stat_badge("Variance", f"{var_c:.2f}"),
        stat_badge("Dispersion", f"{var_c/mean_c:.3f}" if mean_c > 0 else "—"),
        stat_badge("Min", str(int(np.min(arr)))),
        stat_badge("Max", str(int(np.max(arr)))),
        stat_badge("Médiane", f"{np.median(arr):.1f}"),
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '12px', 'marginBottom': '24px'})

    if fits is None:
        return html.Div([badges, html.P("Ajustement impossible (données insuffisantes).", style={'color': PALETTE['text_muted']})])

    rows = []
    for dist, result in fits.items():
        row = {'Modèle': FREQ_DIST_NAMES[dist]}
        for k, v in result['params'].items():
            row[k.capitalize()] = f"{v:.4f}"
        row['LogLik'] = f"{result['loglik']:.2f}"
        row['AIC'] = f"{result['aic']:.2f}"
        row['BIC'] = f"{result['bic']:.2f}"
        rows.append(row)
    rows_sorted = sorted(rows, key=lambda x: float(x['AIC']))
    cols_set = set()
    for r in rows_sorted: cols_set.update(r.keys())
    ordered = ['Modèle'] + sorted(c for c in cols_set if c not in ('Modèle','AIC','BIC','LogLik')) + ['LogLik','AIC','BIC']
    cols = [{'name': c, 'id': c} for c in ordered if c in cols_set]
    return html.Div([badges, make_table(rows_sorted, cols, highlight_first=True)])

def view_freq_cmf(counts, fits, labels):
    """Affiche la fonction de répartition cumulée empirique (ECDF) vs CDF théoriques."""
    if counts is None:
        return html.Div("Sélectionnez une colonne de date.", style={'color': PALETTE['text_muted'], 'padding': '40px'})
    arr = np.array(counts)
    x_max = max(int(np.max(arr)) + 2, 5)
    x_vals = np.arange(0, x_max + 1)

    # ECDF empirique : proportion cumulée d'années avec ≤ k sinistres
    hist, _ = np.histogram(arr, bins=np.arange(-0.5, x_max + 1.5))
    ecdf = np.cumsum(hist) / len(arr)

    fig = go.Figure()
    # Tracé empirique en escalier
    fig.add_trace(go.Scatter(
        x=x_vals, y=ecdf[:len(x_vals)],
        mode='lines+markers', name='Empirique (ECDF)',
        line=dict(color=PALETTE['accent'], width=3, shape='hv'),
        marker=dict(size=8, color=PALETTE['accent']),
    ))

    if fits:
        for dist, result in fits.items():
            cdf = get_freq_cmf(dist, result['params'], x_vals)
            fig.add_trace(go.Scatter(
                x=x_vals, y=cdf,
                mode='lines+markers', name=FREQ_DIST_NAMES[dist],
                line=dict(color=FREQ_COLORS[dist], width=2, shape='hv'),
                marker=dict(size=6),
            ))

    layout = plotly_layout("CDF de fréquence annuelle — Empirique vs Théorique", height=450)
    layout['xaxis']['title'] = "Sinistres / an"
    layout['yaxis']['title'] = "Probabilité cumulée F(k)"
    layout['yaxis']['range'] = [0, 1.02]
    fig.update_layout(layout)

    if not fits:
        return dcc.Graph(figure=fig)

    # Tableau de critères (AIC, BIC, KS discret)
    comp = []
    for dist, result in fits.items():
        # Kolmogorov-Smirnov discret : max |ECDF_emp - CDF_théo|
        cdf_theo = get_freq_cmf(dist, result['params'], x_vals)
        ks_stat = np.max(np.abs(ecdf[:len(x_vals)] - cdf_theo[:len(ecdf)]))

        # Chi² avec regroupement des cellules attendues < 5
        pmf_emp = hist / len(arr)
        obs = pmf_emp * len(arr)
        exp = get_freq_pmf(dist, result['params'], x_vals) * len(arr)
        m_obs, m_exp, acc_o, acc_e = [], [], 0, 0
        for o, e in zip(obs, exp):
            acc_o += o; acc_e += e
            if acc_e >= 5:
                m_obs.append(acc_o); m_exp.append(acc_e)
                acc_o, acc_e = 0, 0
        if not m_exp:
            m_obs.append(acc_o); m_exp.append(max(acc_e, 1e-9))
        elif acc_e > 0:
            m_obs[-1] += acc_o; m_exp[-1] += acc_e
        try:
            chi2 = sum((o - e) ** 2 / e for o, e in zip(m_obs, m_exp) if e > 0)
            dof = max(1, len(m_obs) - 1 - len(result['params']))
            pval = 1 - stats.chi2.cdf(chi2, dof)
        except Exception:
            chi2, pval = float('nan'), float('nan')

        comp.append({
            'Modèle': FREQ_DIST_NAMES[dist],
            'AIC': f"{result['aic']:.2f}",
            'BIC': f"{result['bic']:.2f}",
            'KS (discret)': f"{ks_stat:.4f}",
            'Chi²': f"{chi2:.3f}" if np.isfinite(chi2) else 'N/A',
            'p-val Chi²': f"{pval:.4f}" if np.isfinite(pval) else 'N/A',
        })

    comp_sorted = sorted(comp, key=lambda x: float(x['AIC']))
    return html.Div([
        dcc.Graph(figure=fig),
        html.Div([
            html.Span("⭐ Meilleur AIC : ", style={'color': PALETTE['text_muted'], 'fontSize': '13px'}),
            html.Span(comp_sorted[0]['Modèle'], style={'color': PALETTE['success'], 'fontWeight': '700'}),
        ], style={'marginBottom': '12px'}),
        make_table(comp_sorted, [{'name': c, 'id': c} for c in comp_sorted[0].keys()], highlight_first=True),
    ])

def view_freq_ts(counts, fits, labels):
    if counts is None:
        return html.Div("Sélectionnez une colonne de date.", style={'color': PALETTE['text_muted'], 'padding': '40px'})
    arr = np.array(counts); mean_c = np.mean(arr)
    x_labels = labels if labels else list(range(len(arr)))
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x_labels, y=arr.tolist(), name='Sinistres/an',
                         marker_color=f"rgba(0,153,255,0.4)", marker_line_color=PALETTE['accent2'], marker_line_width=1.2))
    fig.add_trace(go.Scatter(x=x_labels, y=[mean_c]*len(arr), mode='lines',
                             name=f"Moyenne ({mean_c:.1f})", line=dict(color=PALETTE['danger'], width=2, dash='dash')))
    layout = plotly_layout("Évolution temporelle de la fréquence annuelle", height=430)
    layout['xaxis']['title'] = "Année"
    layout['yaxis']['title'] = "Nombre de sinistres"
    layout['barmode'] = 'overlay'
    fig.update_layout(layout)

    if not fits:
        return dcc.Graph(figure=fig)
    probs = [0.25, 0.50, 0.75, 0.90, 0.95]
    q_emp = np.quantile(arr, probs)
    quant_rows = [{'Modèle': 'Empirique', **{f'Q{int(p*100)}': f"{q_emp[i]:.1f}" for i, p in enumerate(probs)}}]
    for dist, result in fits.items():
        row = {'Modèle': FREQ_DIST_NAMES[dist]}
        for i, p in enumerate(probs):
            try:
                if dist == 'poisson': qt = stats.poisson.ppf(p, result['params']['lambda'])
                elif dist == 'neg_binomial': qt = stats.nbinom.ppf(p, result['params']['r'], result['params']['p'])
                elif dist == 'geometric': qt = stats.geom.ppf(p, result['params']['p']) - 1
                else: qt = float('nan')
                err = (qt-q_emp[i])/q_emp[i]*100 if q_emp[i] != 0 else 0
                row[f'Q{int(p*100)}'] = f"{qt:.0f} ({err:+.1f}%)"
            except: row[f'Q{int(p*100)}'] = 'N/A'
        quant_rows.append(row)
    return html.Div([
        dcc.Graph(figure=fig),
        html.H4("Tableau des Quantiles", style={'color': PALETTE['accent'], 'marginTop': '20px', 'fontSize': '13px', 'letterSpacing': '2px'}),
        make_table(quant_rows, [{'name': c, 'id': c} for c in quant_rows[0].keys()]),
    ])

# ============================================================
# APPLICATION DASH
# ============================================================

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Sinistre — Modélisation & Réassurance"

# Styles globaux injectés via un composant caché
GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background-color: #0F1923 !important; font-family: 'Space Grotesk', sans-serif; }
.tab-selected { background-color: #00D4B4 !important; color: #000 !important; font-weight: 700 !important; border-top: 3px solid #00D4B4 !important; }
.tab { background-color: #1A2535 !important; color: #7A8BA0 !important; border: 1px solid #2D4060 !important; }
::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: #0F1923; } ::-webkit-scrollbar-thumb { background: #2D4060; border-radius: 3px; }
input[type=number]::-webkit-inner-spin-button { opacity: 0.3; }

/* ---- Dropdown Dash : contrôle (valeur sélectionnée) ---- */
.Select-control { background-color: #243044 !important; border: 1px solid #2D4060 !important; border-radius: 6px !important; }
.Select-value-label { color: #E8EDF5 !important; font-size: 13px !important; }
.Select-placeholder { color: #7A8BA0 !important; font-size: 13px !important; }
.Select-arrow { border-color: #7A8BA0 transparent transparent !important; }
.Select.is-focused > .Select-control { border-color: #00D4B4 !important; box-shadow: 0 0 0 1px #00D4B4 !important; }
.Select-input > input { color: #E8EDF5 !important; }

/* ---- Menu déroulant (liste d'options) ---- */
.Select-menu-outer { background-color: #1E2D42 !important; border: 1px solid #2D4060 !important; border-radius: 6px !important; box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important; z-index: 9999 !important; }
.Select-menu { background-color: #1E2D42 !important; }
.Select-option { background-color: #1E2D42 !important; color: #C8D6E8 !important; font-size: 13px !important; padding: 10px 14px !important; }
.Select-option:hover, .Select-option.is-focused { background-color: #243044 !important; color: #E8EDF5 !important; }
.Select-option.is-selected { background-color: #00D4B4 !important; color: #000 !important; font-weight: 600 !important; }
.VirtualizedSelectFocusedOption { background-color: #243044 !important; color: #E8EDF5 !important; }
.VirtualizedSelectSelectedOption { background-color: #00D4B4 !important; color: #000 !important; }

/* ---- Multi-select tags ---- */
.Select-value { background-color: #243044 !important; border-color: #2D4060 !important; color: #E8EDF5 !important; }
.Select-value-icon { color: #7A8BA0 !important; border-right-color: #2D4060 !important; }
.Select-value-icon:hover { background-color: #FF4D6D !important; color: #fff !important; }
"""

# NAV TABS PRINCIPALE
NAV_TABS = html.Div([
    html.Div([
        html.Div([
            html.Span("◈", style={'color': PALETTE['accent'], 'fontSize': '22px', 'marginRight': '10px'}),
            html.Span("Sinistre", style={'color': PALETTE['text'], 'fontSize': '20px', 'fontWeight': '700', 'letterSpacing': '2px', 'fontFamily': "'JetBrains Mono', monospace"}),
        ], style={'display': 'flex', 'alignItems': 'center'}),
        html.Div([
            html.Button("Modélisation", id='nav-modelisation', n_clicks=0, style={
                'backgroundColor': PALETTE['accent'], 'color': '#000', 'border': 'none',
                'padding': '8px 20px', 'borderRadius': '6px', 'cursor': 'pointer',
                'fontWeight': '700', 'fontSize': '13px', 'letterSpacing': '1px', 'marginRight': '8px'
            }),
            html.Button("Réassurance", id='nav-reassurance', n_clicks=0, style={
                'backgroundColor': 'transparent', 'color': PALETTE['text_muted'],
                'border': f"1px solid {PALETTE['border']}", 'padding': '8px 20px',
                'borderRadius': '6px', 'cursor': 'pointer', 'fontWeight': '600', 'fontSize': '13px', 'letterSpacing': '1px'
            }),
        ], style={'display': 'flex'}),
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
              'maxWidth': '1600px', 'margin': '0 auto', 'padding': '0 30px'}),
], style={'backgroundColor': PALETTE['surface'], 'padding': '18px 0',
          'borderBottom': f"1px solid {PALETTE['border']}", 'position': 'sticky', 'top': '0', 'zIndex': '1000'})

# ============================================================
# PAGE MODÉLISATION
# ============================================================

PAGE_MODELISATION = html.Div([
    html.Div([
        # COLONNE GAUCHE - Configuration
        html.Div([
            card([
                section_title("Configuration"),
                html.Label("Fichier (Excel / CSV)", style={'color': PALETTE['text_muted'], 'fontSize': '12px', 'display': 'block', 'marginBottom': '8px'}),
                dcc.Upload(id='upload-data', children=html.Div([
                    html.Div("↑", style={'fontSize': '28px', 'color': PALETTE['accent']}),
                    html.Div("Glisser-déposer ou cliquer", style={'fontSize': '13px', 'color': PALETTE['text_muted']}),
                ], style={'textAlign': 'center'}), style={
                    'border': f"2px dashed {PALETTE['border']}", 'borderRadius': '8px',
                    'padding': '20px', 'cursor': 'pointer', 'marginBottom': '8px',
                    'backgroundColor': PALETTE['surface2'],
                }),
                html.Div(id='upload-status', style={'color': PALETTE['success'], 'fontSize': '12px', 'marginBottom': '16px'}),

                html.Label("Colonne des montants", style={'color': PALETTE['text_muted'], 'fontSize': '12px', 'display': 'block', 'marginBottom': '6px'}),
                dcc.Dropdown(id='column-name', options=[], placeholder='Sélectionner…',
                             style={'marginBottom': '14px'},
                             className='dark-dropdown'),

                html.Label("Colonne de date (optionnel)", style={'color': PALETTE['text_muted'], 'fontSize': '12px', 'display': 'block', 'marginBottom': '6px'}),
                dcc.Dropdown(id='date-column', options=[], placeholder='Pour l\'analyse de fréquence',
                             style={'marginBottom': '14px'}),

                html.Label("Année de départ (optionnel)", style={'color': PALETTE['text_muted'], 'fontSize': '12px', 'display': 'block', 'marginBottom': '6px'}),
                dcc.Input(id='start-date-input', type='number', placeholder='ex: 2015', min=1900, max=2100,
                          style={'width': '100%', 'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                                 'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '8px 12px', 'marginBottom': '14px',
                                 'fontSize': '13px', 'fontFamily': "'JetBrains Mono', monospace"}),

                html.Label("Seuil de séparation", style={'color': PALETTE['text_muted'], 'fontSize': '12px', 'display': 'block', 'marginBottom': '6px'}),
                dcc.Input(id='threshold', type='number', value=30000,
                          style={'width': '100%', 'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                                 'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '8px 12px', 'marginBottom': '20px',
                                 'fontSize': '13px', 'fontFamily': "'JetBrains Mono', monospace"}),

                btn_primary("▶  Analyser", id='analyze-button'),
            ], style={'marginBottom': '16px'}),

            html.Div(id='data-info-card'),
        ], style={'width': '280px', 'flexShrink': '0'}),

        # COLONNE DROITE - Résultats
        html.Div([
            # SEGMENT SOUS LE SEUIL - Sévérité
            card([
                html.Div([
                    html.Div("▼", style={'color': PALETTE['success'], 'marginRight': '8px', 'fontSize': '18px'}),
                    html.Span("Sévérité — Sinistres SOUS le seuil", style={'color': PALETTE['success'], 'fontWeight': '700', 'fontSize': '15px', 'letterSpacing': '1px'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
                dcc.Tabs(id='below-tabs', value='below-details', children=[
                    dcc.Tab(label='Paramètres', value='below-details'),
                    dcc.Tab(label='ECDF & Critères', value='below-ecdf-criteria'),
                    dcc.Tab(label='QQ & Quantiles', value='below-qq-quantiles'),
                ], colors={"border": PALETTE['border'], "primary": PALETTE['accent'], "background": PALETTE['surface2']}),
                html.Div(id='below-content', style={'minHeight': '300px', 'paddingTop': '20px'}),
            ], style={'marginBottom': '16px', 'borderLeft': f"3px solid {PALETTE['success']}"}),

            # SEGMENT SOUS LE SEUIL - Fréquence
            card([
                html.Div([
                    html.Div("∿", style={'color': '#1abc9c', 'marginRight': '8px', 'fontSize': '22px'}),
                    html.Span("Fréquence — Sinistres SOUS le seuil", style={'color': '#1abc9c', 'fontWeight': '700', 'fontSize': '15px', 'letterSpacing': '1px'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
                dcc.Tabs(id='below-freq-tabs', value='below-freq-details', children=[
                    dcc.Tab(label='Paramètres', value='below-freq-details'),
                    dcc.Tab(label='CDF & Critères', value='below-freq-cmf'),
                    dcc.Tab(label='Série temporelle', value='below-freq-ts'),
                ], colors={"border": PALETTE['border'], "primary": '#1abc9c', "background": PALETTE['surface2']}),
                html.Div(id='below-freq-content', style={'minHeight': '300px', 'paddingTop': '20px'}),
            ], style={'marginBottom': '16px', 'borderLeft': '3px solid #1abc9c'}),

            # SEGMENT AU-DESSUS DU SEUIL - Sévérité
            card([
                html.Div([
                    html.Div("▲", style={'color': PALETTE['danger'], 'marginRight': '8px', 'fontSize': '18px'}),
                    html.Span("Sévérité — Sinistres AU-DESSUS du seuil", style={'color': PALETTE['danger'], 'fontWeight': '700', 'fontSize': '15px', 'letterSpacing': '1px'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
                dcc.Tabs(id='above-tabs', value='above-details', children=[
                    dcc.Tab(label='Paramètres', value='above-details'),
                    dcc.Tab(label='ECDF & Critères', value='above-ecdf-criteria'),
                    dcc.Tab(label='QQ & Quantiles', value='above-qq-quantiles'),
                ], colors={"border": PALETTE['border'], "primary": PALETTE['danger'], "background": PALETTE['surface2']}),
                html.Div(id='above-content', style={'minHeight': '300px', 'paddingTop': '20px'}),
            ], style={'marginBottom': '16px', 'borderLeft': f"3px solid {PALETTE['danger']}"}),

            # SEGMENT AU-DESSUS DU SEUIL - Fréquence
            card([
                html.Div([
                    html.Div("∿", style={'color': '#e74c3c', 'marginRight': '8px', 'fontSize': '22px'}),
                    html.Span("Fréquence — Sinistres AU-DESSUS du seuil", style={'color': '#e74c3c', 'fontWeight': '700', 'fontSize': '15px', 'letterSpacing': '1px'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
                dcc.Tabs(id='above-freq-tabs', value='above-freq-details', children=[
                    dcc.Tab(label='Paramètres', value='above-freq-details'),
                    dcc.Tab(label='CDF & Critères', value='above-freq-cmf'),
                    dcc.Tab(label='Série temporelle', value='above-freq-ts'),
                ], colors={"border": PALETTE['border'], "primary": '#e74c3c', "background": PALETTE['surface2']}),
                html.Div(id='above-freq-content', style={'minHeight': '300px', 'paddingTop': '20px'}),
            ], style={'borderLeft': '3px solid #e74c3c'}),
        ], style={'flex': '1', 'minWidth': '0'}),

    ], style={'display': 'flex', 'gap': '20px', 'padding': '24px', 'maxWidth': '1600px', 'margin': '0 auto'}),

    # (stores au niveau du layout racine)
])

# ============================================================
# PAGE RÉASSURANCE
# ============================================================

PAGE_REASSURANCE = html.Div([
    html.Div([
        # COLONNE GAUCHE
        html.Div([
            card([
                section_title("1 — Modèle de simulation", PALETTE['accent2']),

                # Bandeau d'info / lois sélectionnées automatiquement
                html.Div(id='r-model-status-banner'),

                html.Label("Nombre de simulations", style={'color': PALETTE['text_muted'], 'fontSize': '12px', 'display': 'block', 'marginBottom': '4px'}),
                dcc.Input(id='r-nb-sims', type='number', value=1000, min=100, max=50000, step=100,
                          style={'width': '100%', 'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                                 'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '8px 12px', 'marginBottom': '12px',
                                 'fontFamily': "'JetBrains Mono', monospace"}),

                btn_primary("⚙  Générer Simulations", id='r-btn-simuler'),
                html.Div(id='r-sim-status', style={'color': PALETTE['success'], 'fontSize': '12px', 'marginTop': '8px', 'textAlign': 'center'}),
            ], style={'marginBottom': '16px'}),

            card([
                section_title("2 — Configurer Traité", PALETTE['warning']),
                dcc.Dropdown(id='r-type-traite',
                             options=[{'label': 'Quote-Part (QP)', 'value': 'QP'}, {'label': 'Excess of Loss (XS)', 'value': 'XS'}],
                             value='XS', style={'marginBottom': '10px'}),

                html.Div(id='r-container-qp', children=[
                    html.Label("Rétention %", style={'color': PALETTE['text_muted'], 'fontSize': '12px'}),
                    dcc.Input(id='r-in-qp-taux', type='number', value=0.8, step=0.05,
                              style={'width': '100%', 'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                                     'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '8px 12px', 'marginBottom': '8px',
                                     'fontFamily': "'JetBrains Mono', monospace"}),
                ], style={'display': 'none'}),

                html.Div(id='r-container-xs', children=[
                    html.Label("Priorité (€)", style={'color': PALETTE['text_muted'], 'fontSize': '12px'}),
                    dcc.Input(id='r-in-xs-prio', type='number', value=100000,
                              style={'width': '100%', 'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                                     'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '8px 12px', 'marginBottom': '8px',
                                     'fontFamily': "'JetBrains Mono', monospace"}),
                    html.Label("Portée (€)", style={'color': PALETTE['text_muted'], 'fontSize': '12px'}),
                    dcc.Input(id='r-in-xs-portee', type='number', value=500000,
                              style={'width': '100%', 'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                                     'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '8px 12px', 'marginBottom': '8px',
                                     'fontFamily': "'JetBrains Mono', monospace"}),
                ], style={'display': 'block'}),

                html.Div([
                    btn_secondary("+ Ajouter couche", id='r-btn-add-layer',
                                  style={'width': '48%', 'display': 'inline-block', 'backgroundColor': 'transparent',
                                         'color': PALETTE['warning'], 'border': f"1px solid {PALETTE['warning']}",
                                         'borderRadius': '6px', 'padding': '8px', 'cursor': 'pointer', 'fontWeight': '600', 'fontSize': '12px'}),
                    btn_secondary("– Retirer", id='r-btn-remove-layer',
                                  style={'width': '48%', 'display': 'inline-block', 'float': 'right', 'backgroundColor': 'transparent',
                                         'color': PALETTE['text_muted'], 'border': f"1px solid {PALETTE['border']}",
                                         'borderRadius': '6px', 'padding': '8px', 'cursor': 'pointer', 'fontWeight': '600', 'fontSize': '12px'}),
                ], style={'marginTop': '8px', 'marginBottom': '10px', 'overflow': 'hidden'}),

                html.Div(id='r-current-stack-display', style={
                    'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                    'borderRadius': '6px', 'padding': '10px', 'fontSize': '12px',
                    'color': PALETTE['warning'], 'fontFamily': "'JetBrains Mono', monospace",
                    'minHeight': '36px', 'marginBottom': '12px',
                }),

                dcc.Input(id='r-prog-name', type='text', placeholder="Nom du programme (ex: Programme A)",
                          style={'width': '100%', 'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                                 'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '8px 12px', 'marginBottom': '10px',
                                 'fontFamily': "'JetBrains Mono', monospace"}),
                btn_primary("✓  Valider & Tracer", id='r-btn-save-prog'),
            ], style={'marginBottom': '16px'}),

            card([
                section_title("3 — Filtres & Gestion", PALETTE['danger']),
                html.Label("Zone cible — Écart-type (€)", style={'color': PALETTE['text_muted'], 'fontSize': '12px', 'display': 'block', 'marginBottom': '6px'}),
                html.Div([
                    dcc.Input(id='r-std-min', type='number', placeholder="Min",
                              style={'width': '48%', 'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                                     'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '8px', 'fontFamily': "'JetBrains Mono', monospace"}),
                    dcc.Input(id='r-std-max', type='number', placeholder="Max",
                              style={'width': '48%', 'float': 'right', 'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                                     'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '8px', 'fontFamily': "'JetBrains Mono', monospace"}),
                ], style={'overflow': 'hidden', 'marginBottom': '14px'}),

                html.Label("Supprimer un programme", style={'color': PALETTE['text_muted'], 'fontSize': '12px', 'display': 'block', 'marginBottom': '6px'}),
                html.Div([
                    html.Div(dcc.Dropdown(id='r-prog-to-delete', placeholder="Choisir…"), style={'width': '65%', 'display': 'inline-block'}),
                    html.Button('Suppr.', id='r-btn-delete-prog', n_clicks=0, style={
                        'width': '30%', 'float': 'right', 'backgroundColor': 'transparent',
                        'color': PALETTE['danger'], 'border': f"1px solid {PALETTE['danger']}",
                        'borderRadius': '6px', 'padding': '8px', 'cursor': 'pointer', 'fontWeight': '700', 'fontSize': '12px'
                    }),
                ], style={'overflow': 'hidden', 'marginBottom': '10px'}),
                html.Button('✕  Tout vider (sauf Brut)', id='r-btn-reset', n_clicks=0, style={
                    'width': '100%', 'backgroundColor': 'transparent', 'color': PALETTE['text_muted'],
                    'border': f"1px solid {PALETTE['border']}", 'borderRadius': '6px', 'padding': '8px',
                    'cursor': 'pointer', 'fontWeight': '600', 'fontSize': '12px',
                }),
            ]),
        ], style={'width': '280px', 'flexShrink': '0'}),

        # COLONNE DROITE
        html.Div([
            card([
                dcc.Graph(id='r-frontiere-graph'),
            ], style={'marginBottom': '16px'}),

            card([
                section_title("Tous les programmes testés"),
                html.Div(id='r-programs-table-container'),
            ], style={'marginBottom': '16px'}),

            card([
                section_title("Programmes dans la zone cible", PALETTE['success']),
                html.Div(id='r-filtered-programs-table-container'),
            ], style={'borderLeft': f"3px solid {PALETTE['success']}"}),
        ], style={'flex': '1', 'minWidth': '0'}),

    ], style={'display': 'flex', 'gap': '20px', 'padding': '24px', 'maxWidth': '1600px', 'margin': '0 auto'}),

    # (stores au niveau du layout racine)
])

# ============================================================
# LAYOUT PRINCIPAL
# ============================================================

# Injection CSS via index_string (html.Style n'existe pas dans dash.html)
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Sinistre</title>
        {%favicon%}
        {%css%}
        <style>
''' + GLOBAL_CSS + '''
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div([
    NAV_TABS,
    # Stores partagés entre modélisation et réassurance — niveau racine = persistent
    dcc.Store(id='current-page', data='modelisation'),
    dcc.Store(id='stored-data'),
    dcc.Store(id='below-fits'),
    dcc.Store(id='above-fits'),
    dcc.Store(id='below-data-store'),
    dcc.Store(id='above-data-store'),
    dcc.Store(id='below-freq-store'),
    dcc.Store(id='above-freq-store'),
    # Stores réassurance
    dcc.Store(id='r-simulations-store'),
    dcc.Store(id='r-current-stack-store', data=[]),
    dcc.Store(id='r-saved-programs-store', data=[]),
    # Pages rendues une seule fois, visibilité gérée par display
    html.Div(PAGE_MODELISATION, id='page-modelisation', style={'display': 'block'}),
    html.Div(PAGE_REASSURANCE, id='page-reassurance', style={'display': 'none'}),
], style={'backgroundColor': PALETTE['bg'], 'minHeight': '100vh', 'fontFamily': "'Space Grotesk', sans-serif", 'color': PALETTE['text']})

# ============================================================
# CALLBACKS NAVIGATION
# ============================================================

@app.callback(
    [Output('page-modelisation', 'style'),
     Output('page-reassurance', 'style'),
     Output('nav-modelisation', 'style'),
     Output('nav-reassurance', 'style'),
     Output('current-page', 'data')],
    [Input('nav-modelisation', 'n_clicks'), Input('nav-reassurance', 'n_clicks')],
    State('current-page', 'data'),
    prevent_initial_call=False
)
def navigate(n_mod, n_rea, current):
    ctx = callback_context
    style_active = {'backgroundColor': PALETTE['accent'], 'color': '#000', 'border': 'none',
                    'padding': '8px 20px', 'borderRadius': '6px', 'cursor': 'pointer',
                    'fontWeight': '700', 'fontSize': '13px', 'letterSpacing': '1px', 'marginRight': '8px'}
    style_inactive = {'backgroundColor': 'transparent', 'color': PALETTE['text_muted'],
                      'border': f"1px solid {PALETTE['border']}", 'padding': '8px 20px',
                      'borderRadius': '6px', 'cursor': 'pointer', 'fontWeight': '600', 'fontSize': '13px', 'letterSpacing': '1px'}

    show = {'display': 'block'}
    hide = {'display': 'none'}

    if not ctx.triggered or ctx.triggered[0]['prop_id'] == '.':
        return show, hide, style_active, style_inactive, 'modelisation'

    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'nav-reassurance':
        return hide, show, style_inactive, {**style_active, 'marginRight': '0'}, 'reassurance'
    return show, hide, style_active, style_inactive, 'modelisation'

# ============================================================
# CALLBACKS MODÉLISATION
# ============================================================

@app.callback(
    [Output('stored-data', 'data'), Output('column-name', 'options'),
     Output('date-column', 'options'), Output('upload-status', 'children')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def load_data(contents, filename):
    if contents is None: return None, [], [], ""
    try:
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded)) if filename.endswith(('.xlsx', '.xls')) else pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        opts = [{'label': c, 'value': c} for c in df.columns]
        date_opts = [{'label': '(aucune)', 'value': ''}] + opts
        return df.to_json(date_format='iso', orient='split'), opts, date_opts, f"✓ {filename} ({len(df):,} lignes)"
    except Exception as e:
        return None, [], [], f"Erreur : {str(e)}"

@app.callback(
    [Output('data-info-card', 'children'),
     Output('below-fits', 'data'), Output('below-data-store', 'data'),
     Output('above-fits', 'data'), Output('above-data-store', 'data'),
     Output('below-freq-store', 'data'), Output('above-freq-store', 'data')],
    Input('analyze-button', 'n_clicks'),
    [State('stored-data', 'data'), State('column-name', 'value'),
     State('date-column', 'value'), State('start-date-input', 'value'), State('threshold', 'value')]
)
def analyze_data(n_clicks, json_data, col, date_col, start_date, threshold):
    empty = (html.Div(), None, None, None, None, None, None)
    if not n_clicks or not json_data or not col: return empty
    try:
        df = pd.read_json(io.StringIO(json_data), orient='split')
        data = df[col].dropna()
        data = data[data > 0]
        if start_date and date_col and date_col in df.columns:
            ds = pd.to_datetime(df.loc[data.index, date_col], errors='coerce')
            data = data[ds.dt.year >= int(start_date)]
        below = data[data < threshold].values
        above = data[data >= threshold].values
        below_fits = analyze_segment_data(below)
        above_fits = analyze_segment_data(above)

        below_freq = above_freq = None
        if date_col and date_col in df.columns:
            di = df[col].dropna(); di = di[di > 0]
            if start_date:
                try:
                    ds_tmp = pd.to_datetime(df.loc[di.index, date_col], errors='coerce')
                    di = di[ds_tmp.dt.year >= int(start_date)]
                except: pass
            ds = df.loc[di.index, date_col]
            bc, bl = compute_counts_from_dates(ds, di < threshold)
            ac, al = compute_counts_from_dates(ds, di >= threshold)
            if bc is not None:
                below_freq = {'counts': bc.tolist(), 'labels': bl, 'fits': analyze_frequency(bc)}
            if ac is not None:
                above_freq = {'counts': ac.tolist(), 'labels': al, 'fits': analyze_frequency(ac)}

        total = len(below) + len(above)
        info = card([
            section_title("Résumé des données"),
            html.Div([
                stat_badge("Total sinistres", f"{total:,}"),
                stat_badge("Sous le seuil", f"{len(below):,}", PALETTE['success']),
                stat_badge("Au-dessus", f"{len(above):,}", PALETTE['danger']),
                stat_badge("Seuil", f"{threshold:,} €", PALETTE['warning']),
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '8px'}),
        ])
        return info, below_fits, below.tolist(), above_fits, above.tolist(), below_freq, above_freq
    except Exception as e:
        return card([html.P(f"Erreur : {str(e)}", style={'color': PALETTE['danger']})]), None, None, None, None, None, None

@app.callback(Output('below-content', 'children'),
              [Input('below-tabs', 'value'), Input('below-fits', 'data'), Input('below-data-store', 'data'), Input('threshold', 'value')])
def render_below(tab, fits, data, threshold):
    if tab == 'below-details': return view_severite_details(data, fits, threshold, "sous")
    elif tab == 'below-ecdf-criteria': return view_severite_ecdf(data, fits, threshold)
    elif tab == 'below-qq-quantiles': return view_severite_qq(data, fits, threshold)

@app.callback(Output('above-content', 'children'),
              [Input('above-tabs', 'value'), Input('above-fits', 'data'), Input('above-data-store', 'data'), Input('threshold', 'value')])
def render_above(tab, fits, data, threshold):
    if tab == 'above-details': return view_severite_details(data, fits, threshold, "au-dessus")
    elif tab == 'above-ecdf-criteria': return view_severite_ecdf(data, fits, threshold)
    elif tab == 'above-qq-quantiles': return view_severite_qq(data, fits, threshold)

@app.callback(Output('below-freq-content', 'children'),
              [Input('below-freq-tabs', 'value'), Input('below-freq-store', 'data')])
def render_below_freq(tab, store):
    if not store:
        return html.Div("Sélectionnez une colonne de date pour l'analyse de fréquence.", style={'color': PALETTE['text_muted'], 'padding': '40px', 'textAlign': 'center'})
    c, l, f = np.array(store['counts']), store.get('labels'), store.get('fits')
    if tab == 'below-freq-details': return view_freq_details(c, f)
    elif tab == 'below-freq-cmf': return view_freq_cmf(c, f, l)
    elif tab == 'below-freq-ts': return view_freq_ts(c, f, l)

@app.callback(Output('above-freq-content', 'children'),
              [Input('above-freq-tabs', 'value'), Input('above-freq-store', 'data')])
def render_above_freq(tab, store):
    if not store:
        return html.Div("Sélectionnez une colonne de date pour l'analyse de fréquence.", style={'color': PALETTE['text_muted'], 'padding': '40px', 'textAlign': 'center'})
    c, l, f = np.array(store['counts']), store.get('labels'), store.get('fits')
    if tab == 'above-freq-details': return view_freq_details(c, f)
    elif tab == 'above-freq-cmf': return view_freq_cmf(c, f, l)
    elif tab == 'above-freq-ts': return view_freq_ts(c, f, l)

# ============================================================
# CALLBACKS RÉASSURANCE
# ============================================================

SEV_DIST_LABELS = {'gamma': 'Gamma', 'lognorm': 'Lognormale', 'weibull': 'Weibull', 'pareto': 'Pareto'}
FREQ_DIST_LABELS = {'poisson': 'Poisson', 'neg_binomial': 'Binomiale Négative', 'geometric': 'Géométrique'}

def _best_dist(fits_dict):
    """Retourne la clé de la meilleure distribution selon l'AIC."""
    if not fits_dict:
        return None
    return min(fits_dict.items(), key=lambda x: x[1].get('aic', 9999))[0]

def _make_law_row(label, dist_key, label_map, color):
    """Ligne d'affichage d'une loi automatiquement sélectionnée."""
    if not dist_key:
        return html.Div([
            html.Span(f"{label} : ", style={'color': PALETTE['text_muted'], 'fontSize': '12px'}),
            html.Span("Non disponible", style={'color': PALETTE['text_muted'], 'fontSize': '12px', 'fontStyle': 'italic'}),
        ], style={'marginBottom': '6px'})
    return html.Div([
        html.Span(f"{label} : ", style={'color': PALETTE['text_muted'], 'fontSize': '12px'}),
        html.Span(label_map.get(dist_key, dist_key), style={
            'color': color, 'fontSize': '13px', 'fontWeight': '700',
            'fontFamily': "'JetBrains Mono', monospace",
            'backgroundColor': f"{color}18",
            'padding': '2px 8px', 'borderRadius': '4px',
            'border': f"1px solid {color}44",
        }),
    ], style={'marginBottom': '6px'})

@app.callback(
    Output('r-model-status-banner', 'children'),
    [Input('below-fits', 'data'), Input('above-fits', 'data'),
     Input('below-freq-store', 'data'), Input('above-freq-store', 'data')]
)
def r_update_banner(below_fits, above_fits, below_freq_store, above_freq_store):
    """Affiche les lois sélectionnées automatiquement par AIC."""
    below_freq_fits = below_freq_store.get('fits') if below_freq_store else None
    above_freq_fits = above_freq_store.get('fits') if above_freq_store else None

    has_model = bool(below_fits or above_fits)

    if not has_model:
        return html.Div([
            html.Span("⚠ ", style={'fontSize': '16px'}),
            html.Span("Aucune modélisation disponible. Allez sur la page ", style={'fontSize': '12px'}),
            html.Strong("Modélisation", style={'color': PALETTE['accent']}),
            html.Span(" et cliquez sur Analyser.", style={'fontSize': '12px'}),
        ], style={
            'backgroundColor': '#2a1f00', 'border': f"1px solid {PALETTE['warning']}",
            'borderRadius': '6px', 'padding': '10px 14px', 'marginBottom': '14px',
            'color': PALETTE['warning'], 'fontSize': '12px',
        })

    # Sélection automatique de la meilleure loi par AIC
    bsd = _best_dist(below_fits)
    bfd = _best_dist(below_freq_fits)
    asd = _best_dist(above_fits)
    afd = _best_dist(above_freq_fits)

    return html.Div([
        html.Div([
            html.Span("✓ Lois sélectionnées automatiquement par ", style={'fontSize': '12px', 'color': PALETTE['success']}),
            html.Strong("AIC", style={'color': PALETTE['accent']}),
        ], style={'marginBottom': '10px'}),

        html.Div("▼  SOUS LE SEUIL", style={
            'color': PALETTE['success'], 'fontSize': '10px', 'fontWeight': '700',
            'letterSpacing': '1.5px', 'marginBottom': '6px',
        }),
        _make_law_row("Sévérité", bsd, SEV_DIST_LABELS, PALETTE['success']),
        _make_law_row("Fréquence", bfd, FREQ_DIST_LABELS, '#1abc9c'),

        html.Div("▲  AU-DESSUS DU SEUIL", style={
            'color': PALETTE['danger'], 'fontSize': '10px', 'fontWeight': '700',
            'letterSpacing': '1.5px', 'marginBottom': '6px', 'marginTop': '10px',
        }),
        _make_law_row("Sévérité", asd, SEV_DIST_LABELS, PALETTE['danger']),
        _make_law_row("Fréquence", afd, FREQ_DIST_LABELS, '#e74c3c'),
    ], style={
        'backgroundColor': '#0a1f15', 'border': f"1px solid {PALETTE['success']}44",
        'borderRadius': '6px', 'padding': '12px 14px', 'marginBottom': '14px',
    })


@app.callback(
    [Output('r-simulations-store', 'data'), Output('r-saved-programs-store', 'data'), Output('r-sim-status', 'children')],
    Input('r-btn-simuler', 'n_clicks'),
    [State('r-nb-sims', 'value'),
     State('below-fits', 'data'), State('above-fits', 'data'),
     State('below-freq-store', 'data'), State('above-freq-store', 'data')],
    prevent_initial_call=True
)
def r_run_simulations(n, n_sims, below_fits, above_fits, below_freq_store, above_freq_store):
    if not n:
        return dash.no_update, dash.no_update, dash.no_update

    # Sélection automatique de la meilleure loi par AIC
    bsd = _best_dist(below_fits)
    asd = _best_dist(above_fits)
    below_freq_fits = below_freq_store.get('fits') if below_freq_store else None
    above_freq_fits = above_freq_store.get('fits') if above_freq_store else None
    bfd = _best_dist(below_freq_fits)
    afd = _best_dist(above_freq_fits)

    bsev_params = below_fits[bsd]['params'] if below_fits and bsd else None
    asev_params = above_fits[asd]['params'] if above_fits and asd else None
    bfreq_params = below_freq_fits[bfd]['params'] if below_freq_fits and bfd else None
    afreq_params = above_freq_fits[afd]['params'] if above_freq_fits and afd else None

    if not bsev_params and not asev_params:
        return dash.no_update, dash.no_update, "⚠ Aucune distribution disponible. Lancez d'abord la modélisation."

    n_sims = int(n_sims or 1000)

    sims = simuler_depuis_distributions(
        n_sims,
        bsd, bsev_params,
        bfd, bfreq_params,
        asd, asev_params,
        afd, afreq_params,
    )

    e, s = appliquer_programme(sims, [])

    # Description détaillée du modèle utilisé
    desc_parts = []
    if bsd and bsev_params: desc_parts.append(f"Sév.↓ {SEV_DIST_LABELS.get(bsd, bsd)}")
    if bfd and bfreq_params: desc_parts.append(f"Fréq.↓ {FREQ_DIST_LABELS.get(bfd, bfd)}")
    if asd and asev_params: desc_parts.append(f"Sév.↑ {SEV_DIST_LABELS.get(asd, asd)}")
    if afd and afreq_params: desc_parts.append(f"Fréq.↑ {FREQ_DIST_LABELS.get(afd, afd)}")

    status = f"✓ {n_sims:,} simulations générées | {' · '.join(desc_parts)}"
    brut_entry = [{'id': 'brut', 'name': 'BRUT (sans réassurance)', 'esp': e, 'std': s,
                   'desc': f"Brut — {' | '.join(desc_parts)}"}]
    return sims, brut_entry, status

@app.callback(
    [Output('r-container-qp', 'style'), Output('r-container-xs', 'style')],
    Input('r-type-traite', 'value')
)
def r_toggle_inputs(t):
    if t == 'QP': return {'display': 'block'}, {'display': 'none'}
    return {'display': 'none'}, {'display': 'block'}

@app.callback(
    [Output('r-current-stack-store', 'data'), Output('r-current-stack-display', 'children')],
    [Input('r-btn-add-layer', 'n_clicks'), Input('r-btn-remove-layer', 'n_clicks')],
    [State('r-type-traite', 'value'), State('r-in-qp-taux', 'value'), State('r-in-xs-prio', 'value'),
     State('r-in-xs-portee', 'value'), State('r-current-stack-store', 'data')],
    prevent_initial_call=True
)
def r_manage_stack(n_add, n_remove, t, val_qp, val_prio, val_portee, stack):
    ctx = callback_context
    if not ctx.triggered: return dash.no_update
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    new_stack = (stack or []).copy()
    if trigger == 'r-btn-add-layer':
        if t == 'QP': new_stack.append({'type': 'QP', 'taux_retention': val_qp})
        elif t == 'XS': new_stack.append({'type': 'XS', 'priorite': val_prio, 'portee': val_portee})
    elif trigger == 'r-btn-remove-layer' and new_stack:
        new_stack.pop()
    desc = formater_description(new_stack) if new_stack else "Aucune couche — programme brut"
    return new_stack, desc

@app.callback(
    [Output('r-saved-programs-store', 'data', allow_duplicate=True),
     Output('r-current-stack-store', 'data', allow_duplicate=True),
     Output('r-prog-to-delete', 'options')],
    [Input('r-btn-save-prog', 'n_clicks'), Input('r-btn-delete-prog', 'n_clicks'), Input('r-btn-reset', 'n_clicks')],
    [State('r-current-stack-store', 'data'), State('r-prog-name', 'value'),
     State('r-saved-programs-store', 'data'), State('r-simulations-store', 'data'), State('r-prog-to-delete', 'value')],
    prevent_initial_call=True
)
def r_manage_programs(n_save, n_del, n_reset, stack, name, saved, sims, prog_to_del):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    current = (saved or []).copy()
    if trigger == 'r-btn-reset':
        current = [p for p in current if p['id'] == 'brut']
        return current, [], [{'label': p['name'], 'value': p['id']} for p in current if p['id'] != 'brut']
    if trigger == 'r-btn-delete-prog' and prog_to_del:
        current = [p for p in current if p['id'] != prog_to_del]
        return current, dash.no_update, [{'label': p['name'], 'value': p['id']} for p in current if p['id'] != 'brut']
    if trigger == 'r-btn-save-prog' and sims:
        e, s = appliquer_programme(sims, stack or [])
        new_id = f"prog_{len(current)}_{np.random.randint(9999)}"
        p_name = name if name else f"Programme {len(current)}"
        current.append({'id': new_id, 'name': p_name, 'esp': e, 'std': s, 'desc': formater_description(stack or [])})
        return current, [], [{'label': p['name'], 'value': p['id']} for p in current if p['id'] != 'brut']
    return dash.no_update, dash.no_update, dash.no_update

@app.callback(
    [Output('r-frontiere-graph', 'figure'),
     Output('r-programs-table-container', 'children'),
     Output('r-filtered-programs-table-container', 'children')],
    [Input('r-saved-programs-store', 'data'), Input('r-std-min', 'value'), Input('r-std-max', 'value')]
)
def r_render_visuals(progs, std_min, std_max):
    if not progs:
        empty_fig = go.Figure()
        empty_fig.update_layout(plotly_layout("Frontière Efficace — Espérance vs Écart-type"))
        return empty_fig, html.Div("Aucun programme.", style={'color': PALETTE['text_muted']}), html.Div()

    df_p = pd.DataFrame(progs)
    brut = df_p[df_p['id'] == 'brut']
    others = df_p[df_p['id'] != 'brut']
    has_target = std_min is not None or std_max is not None
    s_min = std_min or 0; s_max = std_max or float('inf')

    df_cible = pd.DataFrame(); df_hors = pd.DataFrame()
    if has_target and not others.empty:
        mask = (others['std'] >= s_min) & (others['std'] <= s_max)
        df_cible = others[mask]; df_hors = others[~mask]
    else:
        df_cible = others

    fig = go.Figure()
    if has_target and std_min is not None and std_max is not None:
        fig.add_hrect(y0=s_min, y1=s_max, line_width=0, fillcolor=PALETTE['success'], opacity=0.07, layer="below")
        fig.add_hline(y=s_min, line_dash='dot', line_color=PALETTE['success'], opacity=0.5)
        fig.add_hline(y=s_max, line_dash='dot', line_color=PALETTE['success'], opacity=0.5)
    if not brut.empty:
        fig.add_trace(go.Scatter(x=brut['esp'], y=brut['std'], mode='markers+text',
                                 name="Brut", text=["BRUT"], textposition="top center",
                                 marker=dict(size=18, color=PALETTE['danger'], symbol='x', line=dict(width=3, color=PALETTE['danger'])),
                                 textfont=dict(color=PALETTE['danger'], size=12, family="'JetBrains Mono', monospace")))
    if not df_cible.empty:
        pt_color = PALETTE['success'] if has_target else PALETTE['accent2']
        fig.add_trace(go.Scatter(x=df_cible['esp'], y=df_cible['std'], mode='markers+text',
                                 name="Dans la cible" if has_target else "Programmes",
                                 text=df_cible['name'], textposition="top center",
                                 marker=dict(size=12, color=pt_color, line=dict(width=1.5, color=PALETTE['text'])),
                                 textfont=dict(color=pt_color, size=11, family="'JetBrains Mono', monospace")))
    if not df_hors.empty:
        fig.add_trace(go.Scatter(x=df_hors['esp'], y=df_hors['std'], mode='markers+text',
                                 name="Hors cible", text=df_hors['name'], textposition="top center",
                                 marker=dict(size=10, color=PALETTE['text_muted'], line=dict(width=1, color=PALETTE['border'])),
                                 textfont=dict(color=PALETTE['text_muted'], size=10)))
    layout = plotly_layout("Frontière Efficace — Espérance vs Écart-type", height=500)
    layout['xaxis']['title'] = "Espérance (€)"
    layout['yaxis']['title'] = "Écart-type (€)"
    fig.update_layout(layout)

    def creer_table_reas(df):
        if df.empty: return html.Div("Aucun programme.", style={'color': PALETTE['text_muted']})
        rows = df.copy()
        rows['esp'] = rows['esp'].apply(lambda x: f"{x:,.0f} €")
        rows['std'] = rows['std'].apply(lambda x: f"{x:,.0f} €")
        cols = [{'name': 'Programme', 'id': 'name'}, {'name': 'Structure', 'id': 'desc'},
                {'name': 'Espérance', 'id': 'esp'}, {'name': 'Écart-type', 'id': 'std'}]
        return make_table(rows.to_dict('records'), cols)

    table_all = creer_table_reas(df_p)
    table_filtered = creer_table_reas(df_cible) if has_target else html.Div(
        "Définissez un écart-type Min/Max pour filtrer les résultats.",
        style={'color': PALETTE['text_muted'], 'fontSize': '13px'})

    return fig, table_all, table_filtered

if __name__ == '__main__':
    print("Lancement sur http://127.0.0.1:8050")
    app.run(debug=True, port=8050)
