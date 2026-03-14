from server import app
from dash import Input, Output, State, callback_context, html
import dash
import numpy as np
import pandas as pd
import plotly.graph_objs as go

from config import PALETTE, SEV_DIST_NAMES, FREQ_DIST_NAMES
from backend.reinsurance import (
    simuler_depuis_distributions, stats_programme, formater_description,
    compute_ceded_charges, compute_oep_curve, compute_heatmap,
)
from components.ui import make_table, plotly_layout


# ── Helpers ──────────────────────────────────────────────────────────────────

def _best_dist(fits_dict):
    if not fits_dict:
        return None
    return min(fits_dict.items(), key=lambda x: x[1].get('aic', 9999))[0]


def _make_law_row(label, dist_key, label_map, color):
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


def _fmt_eur(v):
    if pd.isna(v) or v is None:
        return 'N/A'
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.2f}M €"
    if abs(v) >= 1_000:
        return f"{v/1_000:.0f}k €"
    return f"{v:.0f} €"


def _fmt_pct(val, ref):
    if ref is None or ref == 0:
        return ''
    pct = (val - ref) / ref * 100
    arrow = "▼" if pct < 0 else "▲"
    color_hint = "▼" if pct < 0 else "▲"
    return f"  {color_hint}{abs(pct):.1f}%"


# ── Banner ────────────────────────────────────────────────────────────────────

@app.callback(
    Output('r-model-status-banner', 'children'),
    [Input('below-fits', 'data'), Input('above-fits', 'data'),
     Input('below-freq-store', 'data'), Input('above-freq-store', 'data')]
)
def r_update_banner(below_fits, above_fits, below_freq_store, above_freq_store):
    below_freq_fits = below_freq_store.get('fits') if below_freq_store else None
    above_freq_fits = above_freq_store.get('fits') if above_freq_store else None
    has_model = bool(below_fits or above_fits)

    if not has_model:
        return html.Div([
            html.Span("⚠ ", style={'fontSize': '16px'}),
            html.Span("Aucune modélisation disponible. Allez sur la page "),
            html.Strong("Modélisation", style={'color': PALETTE['accent']}),
            html.Span(" et cliquez sur Analyser."),
        ], style={
            'backgroundColor': '#2a1f00', 'border': f"1px solid {PALETTE['warning']}",
            'borderRadius': '6px', 'padding': '10px 14px', 'marginBottom': '14px',
            'color': PALETTE['warning'], 'fontSize': '12px',
        })

    bsd = _best_dist(below_fits)
    bfd = _best_dist(below_freq_fits)
    asd = _best_dist(above_fits)
    afd = _best_dist(above_freq_fits)

    return html.Div([
        html.Div([
            html.Span("✓ Lois sélectionnées par ", style={'fontSize': '12px', 'color': PALETTE['success']}),
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


# ── Simulations ───────────────────────────────────────────────────────────────

@app.callback(
    [Output('r-simulations-store', 'data'),
     Output('r-saved-programs-store', 'data'),
     Output('r-sim-status', 'children')],
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

    n_sims = int(n_sims or 5000)
    sims = simuler_depuis_distributions(
        n_sims, bsd, bsev_params, bfd, bfreq_params, asd, asev_params, afd, afreq_params,
    )

    e, s, v95, v99, tv99 = stats_programme(sims, [])
    bc = 0.0  # Brut = aucune cession

    desc_parts = []
    if bsd and bsev_params:  desc_parts.append(f"Sév.↓ {SEV_DIST_NAMES.get(bsd, bsd)}")
    if bfd and bfreq_params: desc_parts.append(f"Fréq.↓ {FREQ_DIST_NAMES.get(bfd, bfd)}")
    if asd and asev_params:  desc_parts.append(f"Sév.↑ {SEV_DIST_NAMES.get(asd, asd)}")
    if afd and afreq_params: desc_parts.append(f"Fréq.↑ {FREQ_DIST_NAMES.get(afd, afd)}")

    ov_flag = " [override]" if any([ov_bsev, ov_bfreq, ov_asev, ov_afreq]) else ""
    status = f"✓ {n_sims:,} simulations générées{ov_flag}"

    brut_entry = [{
        'id': 'brut', 'name': 'BRUT (sans réassurance)',
        'esp': e, 'std': s, 'var95': v95, 'var99': v99, 'tvar99': tv99,
        'burning_cost': bc,
        'desc': f"Brut — {' | '.join(desc_parts)}",
        'stack': [],
    }]
    return sims, brut_entry, status


# ── Toggle QP / XS ───────────────────────────────────────────────────────────

@app.callback(
    [Output('r-container-qp', 'style'), Output('r-container-xs', 'style')],
    Input('r-type-traite', 'value')
)
def r_toggle_inputs(t):
    if t == 'QP':
        return {'display': 'block'}, {'display': 'none'}
    return {'display': 'none'}, {'display': 'block'}


# ── Stack de couches ──────────────────────────────────────────────────────────

@app.callback(
    [Output('r-current-stack-store', 'data'), Output('r-current-stack-display', 'children')],
    [Input('r-btn-add-layer', 'n_clicks'), Input('r-btn-remove-layer', 'n_clicks')],
    [State('r-type-traite', 'value'), State('r-in-qp-taux', 'value'),
     State('r-in-xs-prio', 'value'), State('r-in-xs-portee', 'value'),
     State('r-current-stack-store', 'data')],
    prevent_initial_call=True
)
def r_manage_stack(n_add, n_remove, t, val_qp, val_prio, val_portee, stack):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    new_stack = (stack or []).copy()
    if trigger == 'r-btn-add-layer':
        if t == 'QP':
            new_stack.append({'type': 'QP', 'taux_retention': val_qp})
        elif t == 'XS':
            new_stack.append({'type': 'XS', 'priorite': val_prio, 'portee': val_portee})
    elif trigger == 'r-btn-remove-layer' and new_stack:
        new_stack.pop()
    desc = formater_description(new_stack) if new_stack else "Aucune couche — programme brut"
    return new_stack, desc


# ── Gestion des programmes ────────────────────────────────────────────────────

@app.callback(
    [Output('r-saved-programs-store', 'data', allow_duplicate=True),
     Output('r-current-stack-store', 'data', allow_duplicate=True),
     Output('r-prog-to-delete', 'options')],
    [Input('r-btn-save-prog', 'n_clicks'),
     Input('r-btn-delete-prog', 'n_clicks'),
     Input('r-btn-reset', 'n_clicks')],
    [State('r-current-stack-store', 'data'), State('r-prog-name', 'value'),
     State('r-saved-programs-store', 'data'), State('r-simulations-store', 'data'),
     State('r-prog-to-delete', 'value')],
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
        traites = stack or []
        e, s, v95, v99, tv99 = stats_programme(sims, traites)
        # Burning cost = cession moyenne / charge brute moyenne
        gross_arr, net_arr = compute_ceded_charges(sims, traites)
        mean_gross = float(np.mean(gross_arr))
        ceded_arr = gross_arr - net_arr
        bc = float(np.mean(ceded_arr) / mean_gross) if mean_gross > 0 else 0.0

        new_id = f"prog_{len(current)}_{np.random.randint(9999)}"
        p_name = name.strip() if name and name.strip() else f"Programme {len(current)}"
        current.append({
            'id': new_id, 'name': p_name,
            'esp': e, 'std': s, 'var95': v95, 'var99': v99, 'tvar99': tv99,
            'burning_cost': bc,
            'desc': formater_description(traites),
            'stack': traites,
        })
        return current, [], [{'label': p['name'], 'value': p['id']} for p in current if p['id'] != 'brut']

    return dash.no_update, dash.no_update, dash.no_update


# ── Dropdown sélecteur de programme (Retenu/Cédé) ───────────────────────────

@app.callback(
    [Output('r-detail-prog-dropdown', 'options'),
     Output('r-detail-prog-dropdown', 'value')],
    Input('r-saved-programs-store', 'data')
)
def r_update_detail_dropdown(progs):
    if not progs:
        return [], None
    opts = [{'label': p['name'], 'value': p['id']} for p in progs]
    return opts, progs[0]['id']


# ── Rendu principal (frontière + indicateurs + tableaux) ─────────────────────

@app.callback(
    [Output('r-frontiere-graph', 'figure'),
     Output('r-metrics-graph', 'figure'),
     Output('r-programs-table-container', 'children'),
     Output('r-filtered-programs-table-container', 'children')],
    [Input('r-saved-programs-store', 'data'),
     Input('r-std-min', 'value'),
     Input('r-std-max', 'value')]
)
def r_render_visuals(progs, std_min, std_max):
    empty_metrics = go.Figure()
    empty_metrics.update_layout(plotly_layout("Générez les simulations et ajoutez des programmes"))
    if not progs:
        empty_fig = go.Figure()
        empty_fig.update_layout(plotly_layout("Frontière Efficace — Espérance vs Écart-type"))
        return empty_fig, empty_metrics, html.Div("Aucun programme.", style={'color': PALETTE['text_muted']}), html.Div()

    df_p = pd.DataFrame(progs)
    brut = df_p[df_p['id'] == 'brut']
    others = df_p[df_p['id'] != 'brut']
    has_target = std_min is not None or std_max is not None
    s_min = std_min or 0
    s_max = std_max or float('inf')

    df_cible = pd.DataFrame()
    df_hors = pd.DataFrame()
    if has_target and not others.empty:
        mask = (others['std'] >= s_min) & (others['std'] <= s_max)
        df_cible = others[mask]
        df_hors = others[~mask]
    else:
        df_cible = others

    # ── Frontière efficace ──
    fig = go.Figure()
    if has_target and std_min is not None and std_max is not None:
        fig.add_hrect(y0=s_min, y1=s_max, line_width=0, fillcolor=PALETTE['success'], opacity=0.07, layer="below")
        fig.add_hline(y=s_min, line_dash='dot', line_color=PALETTE['success'], opacity=0.5)
        fig.add_hline(y=s_max, line_dash='dot', line_color=PALETTE['success'], opacity=0.5)

    if not brut.empty:
        fig.add_trace(go.Scatter(
            x=brut['esp'], y=brut['std'], mode='markers+text',
            name="Brut", text=["BRUT"], textposition="top center",
            marker=dict(size=18, color=PALETTE['danger'], symbol='x', line=dict(width=3, color=PALETTE['danger'])),
            textfont=dict(color=PALETTE['danger'], size=12, family="'JetBrains Mono', monospace"),
        ))
    if not df_cible.empty:
        pt_color = PALETTE['success'] if has_target else PALETTE['accent2']
        fig.add_trace(go.Scatter(
            x=df_cible['esp'], y=df_cible['std'], mode='markers+text',
            name="Dans la cible" if has_target else "Programmes",
            text=df_cible['name'], textposition="top center",
            marker=dict(size=12, color=pt_color, line=dict(width=1.5, color=PALETTE['text'])),
            textfont=dict(color=pt_color, size=11, family="'JetBrains Mono', monospace"),
        ))
    if not df_hors.empty:
        fig.add_trace(go.Scatter(
            x=df_hors['esp'], y=df_hors['std'], mode='markers+text',
            name="Hors cible", text=df_hors['name'], textposition="top center",
            marker=dict(size=10, color=PALETTE['text_muted'], line=dict(width=1, color=PALETTE['border'])),
            textfont=dict(color=PALETTE['text_muted'], size=10),
        ))

    layout_f = plotly_layout("Frontière Efficace — Espérance vs Écart-type", height=480)
    layout_f['xaxis'].update(title="Espérance de la charge nette (€)", tickformat=',.0f', exponentformat='none')
    layout_f['yaxis'].update(title="Écart-type de la charge nette (€)", tickformat=',.0f', exponentformat='none')
    fig.update_layout(layout_f)

    # ── Tableau commun ──
    def creer_table(df):
        if df.empty:
            return html.Div("Aucun programme.", style={'color': PALETTE['text_muted']})
        rows = df.copy()
        brut_vals = {}
        if 'id' in rows.columns and (rows['id'] == 'brut').any():
            for col in ['esp', 'std', 'var95', 'var99', 'tvar99']:
                if col in rows.columns:
                    brut_vals[col] = rows.loc[rows['id'] == 'brut', col].values[0]

        def fmt_cell(val, ref, is_brut):
            if pd.isna(val):
                return 'N/A'
            base = _fmt_eur(val)
            if is_brut or not ref or ref == 0:
                return base
            pct = (val - ref) / ref * 100
            arrow = "▼" if pct < 0 else "▲"
            return f"{base}  {arrow}{abs(pct):.1f}%"

        display = rows.copy()
        for col in ['esp', 'std', 'var95', 'var99', 'tvar99']:
            if col in display.columns:
                ref = brut_vals.get(col)
                display[col] = display.apply(
                    lambda r, c=col, rv=ref: fmt_cell(r[c], rv, r['id'] == 'brut'), axis=1
                )
        if 'burning_cost' in display.columns:
            display['burning_cost'] = display.apply(
                lambda r: '—' if r['id'] == 'brut' else f"{r['burning_cost']*100:.1f}%",
                axis=1,
            )

        cols = [
            {'name': 'Programme',    'id': 'name'},
            {'name': 'Structure',    'id': 'desc'},
            {'name': 'Espérance',    'id': 'esp'},
            {'name': 'Écart-type',  'id': 'std'},
            {'name': 'VaR 95% (1/20 ans)', 'id': 'var95'},
            {'name': 'VaR 99% (1/100 ans)', 'id': 'var99'},
            {'name': 'TVaR 99%',    'id': 'tvar99'},
            {'name': 'Burning Cost', 'id': 'burning_cost'},
        ]
        cols = [c for c in cols if c['id'] in display.columns]
        return make_table(display.to_dict('records'), cols, highlight_first=True)

    table_all = creer_table(df_p)
    table_filtered = creer_table(df_cible) if has_target and not df_cible.empty else (
        html.Div("Définissez un écart-type Min/Max (colonne gauche) pour filtrer.",
                 style={'color': PALETTE['text_muted'], 'fontSize': '13px'})
        if not has_target else
        html.Div("Aucun programme dans la zone cible.", style={'color': PALETTE['text_muted']})
    )

    # ── Graphique indicateurs (grouped bar) ──
    metrics_fig = go.Figure()
    metric_cols   = ['esp',             'var95',              'var99',            'tvar99']
    metric_labels = ['Espérance (ESP)', 'VaR 95% (1/20 ans)', 'VaR 99% (1/100 ans)', 'TVaR 99%']
    metric_colors = [PALETTE['accent2'], PALETTE['warning'],   PALETTE['danger'],    '#C0392B']

    for col, label, color in zip(metric_cols, metric_labels, metric_colors):
        if col in df_p.columns:
            metrics_fig.add_trace(go.Bar(
                name=label, x=df_p['name'], y=df_p[col],
                marker_color=color, opacity=0.85,
                text=df_p[col].apply(lambda v: _fmt_eur(v) if pd.notna(v) else ''),
                textposition='outside',
                textfont=dict(size=10, color=PALETTE['text']),
            ))

    m_layout = plotly_layout("Comparaison des indicateurs de risque par programme", height=400)
    m_layout['xaxis']['title'] = "Programme"
    m_layout['yaxis'].update(title="Montant (€)", tickformat=',.0f', exponentformat='none')
    m_layout['barmode'] = 'group'
    m_layout['uniformtext'] = dict(mode='hide', minsize=9)
    metrics_fig.update_layout(m_layout)

    return fig, metrics_fig, table_all, table_filtered


# ── OEP ──────────────────────────────────────────────────────────────────────

@app.callback(
    Output('r-oep-graph', 'figure'),
    [Input('r-saved-programs-store', 'data'),
     Input('r-simulations-store', 'data')]
)
def r_render_oep(progs, sims):
    fig = go.Figure()
    layout = plotly_layout("Courbe d'Excédance de Pertes (OEP)", height=480)
    layout['xaxis'].update(title="Période de retour (années)", type='log',
                           tickvals=[1, 2, 5, 10, 20, 50, 100, 200, 500, 1000],
                           ticktext=['1', '2', '5', '10', '20', '50', '100', '200', '500', '1000'])
    layout['yaxis'].update(title="Perte annuelle dépassée (€)", tickformat=',.0f', exponentformat='none')

    if not progs or not sims:
        fig.update_layout(layout)
        return fig

    colors = [PALETTE['danger'], PALETTE['accent2'], PALETTE['success'], PALETTE['warning'],
              PALETTE['accent'], '#9B59B6', '#E67E22', '#1ABC9C', '#3498DB']

    for i, prog in enumerate(progs):
        stack = prog.get('stack', [])
        try:
            from backend.reinsurance import compute_charges
            ch = compute_charges(sims, stack)
        except Exception:
            continue
        rp, sorted_ch = compute_oep_curve(ch)
        color = PALETTE['danger'] if prog['id'] == 'brut' else colors[i % len(colors)]
        dash_style = 'dash' if prog['id'] == 'brut' else 'solid'
        width = 2.5 if prog['id'] == 'brut' else 1.8

        fig.add_trace(go.Scatter(
            x=rp, y=sorted_ch,
            name=prog['name'],
            mode='lines',
            line=dict(color=color, width=width, dash=dash_style),
            hovertemplate=(
                f"<b>{prog['name']}</b><br>"
                "Période de retour: %{x:.0f} ans<br>"
                "Perte: %{y:,.0f} €<extra></extra>"
            ),
        ))

    # Lignes de référence pour les périodes classiques
    for rp_val, label, color in [(20, '1/20 ans (VaR 95%)', PALETTE['warning']),
                                  (100, '1/100 ans (VaR 99%)', PALETTE['danger'])]:
        fig.add_vline(x=rp_val, line_dash='dot', line_color=color, opacity=0.5,
                      annotation_text=label, annotation_font=dict(color=color, size=10),
                      annotation_position='top right')

    fig.update_layout(layout)
    return fig


# ── Retenu / Cédé ────────────────────────────────────────────────────────────

@app.callback(
    Output('r-retained-ceded-graph', 'figure'),
    [Input('r-detail-prog-dropdown', 'value'),
     Input('r-saved-programs-store', 'data')],
    State('r-simulations-store', 'data')
)
def r_render_retained_ceded(prog_id, progs, sims):
    fig = go.Figure()
    layout = plotly_layout("Distribution Retenu / Cédé", height=420)
    layout['xaxis'].update(title="Charge annuelle (€)", tickformat=',.0f', exponentformat='none')
    layout['yaxis'].update(title="Nombre de simulations")
    layout['barmode'] = 'overlay'

    if not prog_id or not progs or not sims:
        fig.update_layout(layout)
        return fig

    prog = next((p for p in progs if p['id'] == prog_id), None)
    if not prog:
        fig.update_layout(layout)
        return fig

    stack = prog.get('stack', [])
    try:
        gross_arr, net_arr = compute_ceded_charges(sims, stack)
    except Exception:
        fig.update_layout(layout)
        return fig

    ceded_arr = gross_arr - net_arr

    fig.add_trace(go.Histogram(
        x=gross_arr, name="Brut total",
        marker_color=PALETTE['text_muted'], opacity=0.35,
        nbinsx=60,
        hovertemplate="Brut: %{x:,.0f} €<br>Simulations: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Histogram(
        x=net_arr, name="Retenu (cédante)",
        marker_color=PALETTE['success'], opacity=0.75,
        nbinsx=60,
        hovertemplate="Retenu: %{x:,.0f} €<br>Simulations: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Histogram(
        x=ceded_arr, name="Cédé (réassureur)",
        marker_color=PALETTE['warning'], opacity=0.75,
        nbinsx=60,
        hovertemplate="Cédé: %{x:,.0f} €<br>Simulations: %{y}<extra></extra>",
    ))

    # Médianes
    for arr, name, color in [
        (net_arr,   "Médiane retenu",  PALETTE['success']),
        (ceded_arr, "Médiane cédé",    PALETTE['warning']),
    ]:
        median_val = float(np.median(arr))
        fig.add_vline(x=median_val, line_dash='dot', line_color=color, opacity=0.8,
                      annotation_text=f"{name}: {_fmt_eur(median_val)}",
                      annotation_font=dict(color=color, size=10),
                      annotation_position='top left')

    title = f"Retenu vs Cédé — {prog['name']}"
    layout['title']['text'] = f"<b>{title}</b>"
    fig.update_layout(layout)
    return fig


# ── Heatmap sensibilité XS ────────────────────────────────────────────────────

@app.callback(
    [Output('r-heatmap-graph', 'figure'),
     Output('r-heatmap-status', 'children')],
    Input('r-btn-heatmap', 'n_clicks'),
    [State('r-heatmap-prio-min', 'value'),
     State('r-heatmap-prio-max', 'value'),
     State('r-heatmap-portee-min', 'value'),
     State('r-heatmap-portee-max', 'value'),
     State('r-heatmap-steps', 'value'),
     State('r-simulations-store', 'data')],
    prevent_initial_call=True
)
def r_render_heatmap(n_clicks, prio_min, prio_max, portee_min, portee_max, steps, sims):
    fig = go.Figure()
    layout = plotly_layout("Heatmap ESP net — Priorité × Portée", height=480)

    if not sims:
        layout['title']['text'] = "<b>Générez d'abord les simulations</b>"
        fig.update_layout(layout)
        return fig, "⚠ Aucune simulation disponible."

    try:
        prio_min = float(prio_min or 50_000)
        prio_max = float(prio_max or 500_000)
        portee_min = float(portee_min or 100_000)
        portee_max = float(portee_max or 1_000_000)
        steps = max(4, min(20, int(steps or 8)))
    except (TypeError, ValueError):
        fig.update_layout(layout)
        return fig, "⚠ Paramètres invalides."

    prio_list   = np.linspace(prio_min, prio_max, steps)
    portee_list = np.linspace(portee_min, portee_max, steps)

    matrix = compute_heatmap(sims, prio_list, portee_list)

    # Labels formatés
    x_labels = [_fmt_eur(v) for v in prio_list]
    y_labels = [_fmt_eur(v) for v in portee_list]

    # Texte dans chaque cellule
    text_matrix = [[_fmt_eur(matrix[i, j]) for j in range(len(prio_list))]
                   for i in range(len(portee_list))]

    fig.add_trace(go.Heatmap(
        z=matrix,
        x=x_labels,
        y=y_labels,
        text=text_matrix,
        texttemplate="%{text}",
        textfont=dict(size=9, color='white'),
        colorscale=[
            [0.0, '#0D4F3C'],
            [0.3, PALETTE['success']],
            [0.6, PALETTE['warning']],
            [1.0, PALETTE['danger']],
        ],
        reversescale=False,
        colorbar=dict(
            title="ESP net (€)",
            tickformat=',.0f',
            title_font=dict(color=PALETTE['text'], size=11),
            tickfont=dict(color=PALETTE['text_muted'], size=10),
        ),
        hovertemplate=(
            "Priorité: %{x}<br>"
            "Portée: %{y}<br>"
            "ESP net: %{text}<extra></extra>"
        ),
    ))

    layout['xaxis'].update(title="Priorité XS", tickangle=-30)
    layout['yaxis'].update(title="Portée XS")
    layout['margin'].update(l=90, b=100)
    fig.update_layout(layout)

    status = f"✓ Grille {steps}×{steps} calculée — {steps*steps} combinaisons testées"
    return fig, status
