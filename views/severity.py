import numpy as np
from dash import dcc, html
import plotly.graph_objs as go
from scipy import stats

from config import PALETTE, SEV_DIST_NAMES, SEV_COLORS
from backend.severity import pareto_pdf, pareto_cdf, pareto_quantile, compute_gof_stats
from components.ui import stat_badge, make_table, plotly_layout


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
    layout = plotly_layout(f"ECDF — Seuil : {threshold:,.0f} €", height=480)
    layout['xaxis']['title'] = "Montant du sinistre (€)"
    layout['xaxis']['tickformat'] = ',.0f'
    layout['xaxis']['exponentformat'] = 'none'
    layout['yaxis']['title'] = "Probabilité cumulée F(x)"
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
    layout = plotly_layout("QQ-Plot — Quantiles théoriques vs empiriques (échelle log)", height=480)
    layout['xaxis']['title'] = "Quantiles théoriques (log)"
    layout['xaxis']['type'] = 'log'
    layout['xaxis']['exponentformat'] = 'e'
    layout['yaxis']['title'] = "Quantiles empiriques (log)"
    layout['yaxis']['type'] = 'log'
    layout['yaxis']['exponentformat'] = 'e'
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


def view_severite_histogram(data, fits_data, threshold):
    if fits_data is None or data is None:
        return html.Div("Analysez d'abord les données.", style={'color': PALETTE['text_muted'], 'padding': '40px'})
    arr = np.array(data)
    x_min = np.min(arr)
    x_max = np.percentile(arr, 99)  # tronquer à P99 pour lisibilité
    x_range = np.linspace(x_min, x_max, 600)
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=arr[arr <= x_max], histnorm='probability density', name='Données',
        nbinsx=50, marker_color='rgba(0,212,180,0.2)',
        marker_line_color=PALETTE['accent'], marker_line_width=0.8,
    ))
    for dist, result in fits_data.items():
        p = result['params']
        if dist == 'gamma':      y = stats.gamma.pdf(x_range, p['shape'], scale=p['scale'])
        elif dist == 'lognorm':  y = stats.lognorm.pdf(x_range, p['shape'], scale=p['scale'])
        elif dist == 'weibull':  y = stats.weibull_min.pdf(x_range, p['shape'], scale=p['scale'])
        elif dist == 'pareto':   y = pareto_pdf(x_range, p['shape'], p['scale'])
        else: continue
        fig.add_trace(go.Scatter(x=x_range, y=y, mode='lines', name=SEV_DIST_NAMES[dist],
                                 line=dict(color=SEV_COLORS[dist], width=2)))
    layout = plotly_layout(f"Histogramme & densités ajustées (tronqué P99) — Seuil : {threshold:,.0f} €", height=480)
    layout['xaxis']['title'] = "Montant du sinistre (€)"
    layout['xaxis']['tickformat'] = ',.0f'
    layout['xaxis']['exponentformat'] = 'none'
    layout['yaxis']['title'] = "Densité de probabilité"
    fig.update_layout(layout)
    return dcc.Graph(figure=fig)
