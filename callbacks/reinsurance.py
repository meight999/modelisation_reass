from server import app
from dash import Input, Output, State, callback_context, html
import dash
import numpy as np
import pandas as pd
import plotly.graph_objs as go

from config import PALETTE, SEV_DIST_NAMES, FREQ_DIST_NAMES
from backend.reinsurance import (
    simuler_depuis_distributions, stats_programme, formater_description
)
from components.ui import make_table, plotly_layout


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
        _make_law_row("Sévérité", bsd, SEV_DIST_NAMES, PALETTE['success']),
        _make_law_row("Fréquence", bfd, FREQ_DIST_NAMES, PALETTE['below_freq']),

        html.Div("▲  AU-DESSUS DU SEUIL", style={
            'color': PALETTE['danger'], 'fontSize': '10px', 'fontWeight': '700',
            'letterSpacing': '1.5px', 'marginBottom': '6px', 'marginTop': '10px',
        }),
        _make_law_row("Sévérité", asd, SEV_DIST_NAMES, PALETTE['danger']),
        _make_law_row("Fréquence", afd, FREQ_DIST_NAMES, PALETTE['above_freq']),
    ], style={
        'backgroundColor': '#0a1f15', 'border': f"1px solid {PALETTE['success']}44",
        'borderRadius': '6px', 'padding': '12px 14px', 'marginBottom': '14px',
    })


@app.callback(
    [Output('r-simulations-store', 'data'), Output('r-saved-programs-store', 'data'), Output('r-sim-status', 'children')],
    Input('r-btn-simuler', 'n_clicks'),
    [State('r-nb-sims', 'value'),
     State('below-fits', 'data'), State('above-fits', 'data'),
     State('below-freq-store', 'data'), State('above-freq-store', 'data'),
     State('r-override-bsev', 'value'), State('r-override-bfreq', 'value'),
     State('r-override-asev', 'value'), State('r-override-afreq', 'value')],
    prevent_initial_call=True
)
def r_run_simulations(n, n_sims, below_fits, above_fits, below_freq_store, above_freq_store,
                      ov_bsev, ov_bfreq, ov_asev, ov_afreq):
    if not n:
        return dash.no_update, dash.no_update, dash.no_update

    below_freq_fits = below_freq_store.get('fits') if below_freq_store else None
    above_freq_fits = above_freq_store.get('fits') if above_freq_store else None

    # Override manuel ou sélection automatique par AIC
    bsd = ov_bsev or _best_dist(below_fits)
    asd = ov_asev or _best_dist(above_fits)
    bfd = ov_bfreq or _best_dist(below_freq_fits)
    afd = ov_afreq or _best_dist(above_freq_fits)

    bsev_params  = below_fits[bsd]['params']       if below_fits       and bsd and bsd in below_fits       else None
    asev_params  = above_fits[asd]['params']        if above_fits       and asd and asd in above_fits        else None
    bfreq_params = below_freq_fits[bfd]['params']   if below_freq_fits  and bfd and bfd in below_freq_fits   else None
    afreq_params = above_freq_fits[afd]['params']   if above_freq_fits  and afd and afd in above_freq_fits   else None

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

    e, s, v95, v99, tv99 = stats_programme(sims, [])

    desc_parts = []
    if bsd and bsev_params:  desc_parts.append(f"Sév.↓ {SEV_DIST_NAMES.get(bsd, bsd)}")
    if bfd and bfreq_params: desc_parts.append(f"Fréq.↓ {FREQ_DIST_NAMES.get(bfd, bfd)}")
    if asd and asev_params:  desc_parts.append(f"Sév.↑ {SEV_DIST_NAMES.get(asd, asd)}")
    if afd and afreq_params: desc_parts.append(f"Fréq.↑ {FREQ_DIST_NAMES.get(afd, afd)}")

    ov_flag = " [override]" if any([ov_bsev, ov_bfreq, ov_asev, ov_afreq]) else ""
    status = f"✓ {n_sims:,} simulations générées{ov_flag} | {' · '.join(desc_parts)}"
    brut_entry = [{'id': 'brut', 'name': 'BRUT (sans réassurance)',
                   'esp': e, 'std': s, 'var95': v95, 'var99': v99, 'tvar99': tv99,
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
        e, s, v95, v99, tv99 = stats_programme(sims, stack or [])
        new_id = f"prog_{len(current)}_{np.random.randint(9999)}"
        p_name = name if name else f"Programme {len(current)}"
        current.append({'id': new_id, 'name': p_name, 'esp': e, 'std': s,
                        'var95': v95, 'var99': v99, 'tvar99': tv99,
                        'desc': formater_description(stack or [])})
        return current, [], [{'label': p['name'], 'value': p['id']} for p in current if p['id'] != 'brut']
    return dash.no_update, dash.no_update, dash.no_update


@app.callback(
    [Output('r-frontiere-graph', 'figure'),
     Output('r-metrics-graph', 'figure'),
     Output('r-programs-table-container', 'children'),
     Output('r-filtered-programs-table-container', 'children')],
    [Input('r-saved-programs-store', 'data'), Input('r-std-min', 'value'), Input('r-std-max', 'value')]
)
def r_render_visuals(progs, std_min, std_max):
    empty_metrics = go.Figure()
    empty_metrics.update_layout(plotly_layout("Comparaison des indicateurs — générez d'abord les simulations"))
    if not progs:
        empty_fig = go.Figure()
        empty_fig.update_layout(plotly_layout("Frontière Efficace — Espérance vs Écart-type"))
        return empty_fig, empty_metrics, html.Div("Aucun programme.", style={'color': PALETTE['text_muted']}), html.Div()

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
    layout['xaxis']['title'] = "Espérance de la charge nette (€)"
    layout['xaxis']['tickformat'] = ',.0f'
    layout['xaxis']['exponentformat'] = 'none'
    layout['yaxis']['title'] = "Écart-type de la charge nette (€)"
    layout['yaxis']['tickformat'] = ',.0f'
    layout['yaxis']['exponentformat'] = 'none'
    fig.update_layout(layout)

    def creer_table_reas(df):
        if df.empty: return html.Div("Aucun programme.", style={'color': PALETTE['text_muted']})
        rows = df.copy()
        brut_vals = {}
        brut_mask = rows['id'] == 'brut'
        if brut_mask.any():
            for col in ['esp', 'std', 'var95', 'var99', 'tvar99']:
                if col in rows.columns:
                    brut_vals[col] = rows.loc[brut_mask, col].values[0]

        def fmt(val, ref, is_brut):
            if pd.isna(val): return 'N/A'
            base = f"{val:,.0f} €"
            if is_brut or not ref or ref == 0: return base
            pct = (val - ref) / ref * 100
            arrow = "▼" if pct < 0 else "▲"
            return f"{base}  {arrow}{abs(pct):.1f}%"

        for col in ['esp', 'std', 'var95', 'var99', 'tvar99']:
            if col in rows.columns:
                ref = brut_vals.get(col)
                rows[col] = rows.apply(lambda r, c=col, rv=ref: fmt(r[c], rv, r['id'] == 'brut'), axis=1)

        base_cols = [{'name': 'Programme', 'id': 'name'}, {'name': 'Structure', 'id': 'desc'},
                     {'name': 'Espérance', 'id': 'esp'}, {'name': 'Écart-type', 'id': 'std'}]
        extra_cols = [{'name': 'VaR 95%', 'id': 'var95'}, {'name': 'VaR 99%', 'id': 'var99'},
                      {'name': 'TVaR 99%', 'id': 'tvar99'}]
        cols = base_cols + [c for c in extra_cols if c['id'] in rows.columns]
        return make_table(rows.to_dict('records'), cols)

    table_all = creer_table_reas(df_p)
    table_filtered = creer_table_reas(df_cible) if has_target else html.Div(
        "Définissez un écart-type Min/Max pour filtrer les résultats.",
        style={'color': PALETTE['text_muted'], 'fontSize': '13px'})

    # ── Graphique de comparaison des indicateurs ──────────────
    metrics_fig = go.Figure()
    metric_cols   = ['esp',           'var95',             'var99',           'tvar99']
    metric_labels = ['Espérance',     'VaR 95%',           'VaR 99%',         'TVaR 99%']
    metric_colors = [PALETTE['accent2'], PALETTE['warning'], PALETTE['danger'], '#C0392B']
    for col, label, color in zip(metric_cols, metric_labels, metric_colors):
        if col in df_p.columns:
            metrics_fig.add_trace(go.Bar(
                name=label, x=df_p['name'], y=df_p[col],
                marker_color=color, opacity=0.85,
                text=df_p[col].apply(lambda v: f"{v/1000:.0f}k" if pd.notna(v) else ''),
                textposition='outside', textfont=dict(size=10, color=PALETTE['text']),
            ))
    m_layout = plotly_layout("Comparaison ESP / VaR 95% / VaR 99% / TVaR 99% par programme", height=360)
    m_layout['xaxis']['title'] = "Programme"
    m_layout['yaxis']['title'] = "Montant (€)"
    m_layout['barmode'] = 'group'
    m_layout['uniformtext'] = dict(mode='hide', minsize=9)
    metrics_fig.update_layout(m_layout)

    return fig, metrics_fig, table_all, table_filtered
