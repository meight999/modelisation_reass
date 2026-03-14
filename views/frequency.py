import numpy as np
from dash import dcc, html
import plotly.graph_objs as go
from scipy import stats

from config import PALETTE, FREQ_DIST_NAMES, FREQ_COLORS
from backend.frequency import get_freq_pmf, get_freq_cmf
from components.ui import stat_badge, make_table, plotly_layout


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
    layout['xaxis']['title'] = "Nombre de sinistres / an"
    layout['xaxis']['tickformat'] = 'd'
    layout['yaxis']['title'] = "Probabilité cumulée F(k)"
    layout['yaxis']['range'] = [0, 1.05]
    layout['yaxis']['tickformat'] = '.0%'
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
    layout['xaxis']['type'] = 'category'
    layout['yaxis']['title'] = "Nombre de sinistres / an"
    layout['yaxis']['tickformat'] = 'd'
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
