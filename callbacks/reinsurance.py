from server import app
from dash import Input, Output, State, callback_context, html, dash_table
import dash
import numpy as np
import pandas as pd
import plotly.graph_objs as go

from config import PALETTE, SEV_DIST_NAMES, FREQ_DIST_NAMES
from backend.reinsurance import (
    simuler_depuis_distributions, stats_programme, formater_description,
    compute_ceded_charges, compute_oep_curve, compute_heatmap, compute_charges,
    compute_full_stats, compute_premium, PREMIUM_PRINCIPLES,
    serialize_simulations, deserialize_simulations,
)
from components.ui import plotly_layout


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _hex_rgba(hex_color, alpha=0.13):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _best_dist(fits_dict):
    if not fits_dict:
        return None
    return min(fits_dict.items(), key=lambda x: x[1].get('aic', 9999))[0]


def _fmt_eur(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return 'N/A'
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.2f}M €"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.0f}k €"
    return f"{v:.0f} €"


def _pct_reduction(val, ref):
    if ref is None or ref == 0:
        return 0.0
    return (ref - val) / ref * 100


def _make_law_row(label, dist_key, label_map, color):
    if not dist_key:
        return html.Div([
            html.Span(f"{label} : ", style={'color': PALETTE['text_muted'], 'fontSize': '12px'}),
            html.Span("Non disponible", style={'color': PALETTE['text_muted'], 'fontSize': '12px',
                                               'fontStyle': 'italic'}),
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


def _kpi_card(label, value, sub=None, color=None, border=None):
    c = color or PALETTE['text']
    b = border or PALETTE['border']
    return html.Div([
        html.Div(value, style={
            'fontSize': '20px', 'fontWeight': '700', 'color': c,
            'fontFamily': "'JetBrains Mono', monospace",
            'letterSpacing': '-0.5px', 'lineHeight': '1.2',
        }),
        html.Div(label, style={
            'fontSize': '10px', 'color': PALETTE['text_muted'],
            'letterSpacing': '0.8px', 'textTransform': 'uppercase',
            'marginTop': '5px', 'fontWeight': '600',
        }),
        html.Div(sub or '', style={
            'fontSize': '11px', 'color': PALETTE['text_muted'],
            'marginTop': '3px', 'lineHeight': '1.3',
        }),
    ], style={
        'backgroundColor': PALETTE['surface'],
        'border': f"1px solid {b}44",
        'borderLeft': f"3px solid {b}",
        'borderRadius': '8px',
        'padding': '14px 18px',
        'flex': '1',
    })


def _get_premium_param(principle, loading, alpha_std, alpha_var):
    if principle == 'expected_value':
        return float(loading) if loading is not None else 0.20
    elif principle == 'std_deviation':
        return float(alpha_std) if alpha_std is not None else 0.20
    else:
        return float(alpha_var) if alpha_var is not None else 0.01


def _ds(sims):
    """Désérialise les simulations depuis le dcc.Store avant calcul."""
    return deserialize_simulations(sims)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BANNER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
            html.Span("⚠  Aucune modélisation. Allez sur "),
            html.Strong("Modélisation", style={'color': PALETTE['accent']}),
            html.Span(" → Analyser."),
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
            html.Span("✓  Lois sélectionnées par AIC",
                      style={'color': PALETTE['success'], 'fontSize': '11px', 'fontWeight': '600'}),
        ], style={'marginBottom': '8px'}),
        html.Div("↓ SOUS SEUIL", style={'color': PALETTE['success'], 'fontSize': '10px',
                                         'fontWeight': '700', 'letterSpacing': '1px',
                                         'marginBottom': '4px'}),
        _make_law_row("Sév.", bsd, SEV_DIST_NAMES, PALETTE['success']),
        _make_law_row("Fréq.", bfd, FREQ_DIST_NAMES, PALETTE['below_freq']),
        html.Div("↑ AU-DESSUS", style={'color': PALETTE['danger'], 'fontSize': '10px',
                                        'fontWeight': '700', 'letterSpacing': '1px',
                                        'marginBottom': '4px', 'marginTop': '8px'}),
        _make_law_row("Sév.", asd, SEV_DIST_NAMES, PALETTE['danger']),
        _make_law_row("Fréq.", afd, FREQ_DIST_NAMES, PALETTE['above_freq']),
    ], style={
        'backgroundColor': '#0a1f15', 'border': f"1px solid {PALETTE['success']}44",
        'borderRadius': '6px', 'padding': '10px 12px', 'marginBottom': '14px',
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOGGLE CHAMPS PRINCIPE DE PRIME
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    [Output('r-premium-param-ev',  'style'),
     Output('r-premium-param-std', 'style'),
     Output('r-premium-param-var', 'style')],
    Input('r-premium-principle', 'value'),
)
def r_toggle_premium_inputs(principle):
    show = {}
    hide = {'display': 'none'}
    return (
        show if principle == 'expected_value' else hide,
        show if principle == 'std_deviation'  else hide,
        show if principle == 'variance'        else hide,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SIMULATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

    bsev_params  = below_fits[bsd]['params']      if below_fits      and bsd and bsd in below_fits      else None
    asev_params  = above_fits[asd]['params']       if above_fits      and asd and asd in above_fits      else None
    bfreq_params = below_freq_fits[bfd]['params']  if below_freq_fits and bfd and bfd in below_freq_fits else None
    afreq_params = above_freq_fits[afd]['params']  if above_freq_fits and afd and afd in above_freq_fits else None

    if not bsev_params and not asev_params:
        return dash.no_update, dash.no_update, "⚠ Aucune distribution — lancez la modélisation d'abord."

    n_sims = int(n_sims) if n_sims is not None else 1000
    n_sims = max(100, min(50000, n_sims))  # borne de sécurité
    sims = simuler_depuis_distributions(
        n_sims, bsd, bsev_params, bfd, bfreq_params, asd, asev_params, afd, afreq_params,
    )

    # 6 valeurs — corrigé
    e, s, v95, v99, v995, tv99 = stats_programme(sims, [])

    desc_parts = []
    if bsd and bsev_params:  desc_parts.append(f"Sév.↓ {SEV_DIST_NAMES.get(bsd, bsd)}")
    if bfd and bfreq_params: desc_parts.append(f"Fréq.↓ {FREQ_DIST_NAMES.get(bfd, bfd)}")
    if asd and asev_params:  desc_parts.append(f"Sév.↑ {SEV_DIST_NAMES.get(asd, asd)}")
    if afd and afreq_params: desc_parts.append(f"Fréq.↑ {FREQ_DIST_NAMES.get(afd, afd)}")

    ov_flag = "  [override actif]" if any([ov_bsev, ov_bfreq, ov_asev, ov_afreq]) else ""
    status = f"✓  {n_sims:,} simulations générées{ov_flag}"

    brut_entry = [{
        'id': 'brut', 'name': 'BRUT',
        'esp': e, 'std': s, 'var95': v95, 'var99': v99, 'var995': v995, 'tvar99': tv99,
        'net_esp': e, 'net_std': s, 'net_var95': v95, 'net_var99': v99, 'net_tvar99': tv99,
        'premium': 0.0,
        'burning_cost': 0.0,
        'desc': 'Sans réassurance',
        'stack': [],
    }]
    return serialize_simulations(sims), brut_entry, status


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOGGLE QP / XS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    [Output('r-container-qp', 'style'), Output('r-container-xs', 'style')],
    Input('r-type-traite', 'value')
)
def r_toggle_inputs(t):
    if t == 'QP':
        return {'display': 'block'}, {'display': 'none'}
    return {'display': 'none'}, {'display': 'block'}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STACK DE COUCHES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    [Output('r-current-stack-store', 'data'),
     Output('r-current-stack-display', 'children')],
    [Input('r-btn-add-layer', 'n_clicks'),
     Input('r-btn-remove-layer', 'n_clicks')],
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

    if not new_stack:
        display = html.Span("Aucune couche configurée",
                            style={'color': PALETTE['text_muted'], 'fontStyle': 'italic'})
    else:
        parts = []
        for i, t_ in enumerate(new_stack, 1):
            if t_['type'] == 'QP':
                parts.append(html.Div(
                    f"Couche {i} · QP {float(t_['taux_retention'])*100:.0f}% rétention",
                    style={'marginBottom': '2px'}))
            else:
                prio_k   = float(t_['priorite']) / 1000
                portee_k = float(t_['portee']) / 1000
                parts.append(html.Div(
                    f"Couche {i} · XS {portee_k:.0f}k xs {prio_k:.0f}k",
                    style={'marginBottom': '2px'}))
        display = html.Div(parts)

    return new_stack, display


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GESTION DES PROGRAMMES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    [Output('r-saved-programs-store', 'data', allow_duplicate=True),
     Output('r-current-stack-store', 'data', allow_duplicate=True),
     Output('r-prog-to-delete', 'options')],
    [Input('r-btn-save-prog', 'n_clicks'),
     Input('r-btn-delete-prog', 'n_clicks'),
     Input('r-btn-reset', 'n_clicks')],
    [State('r-current-stack-store', 'data'),
     State('r-prog-name', 'value'),
     State('r-saved-programs-store', 'data'),
     State('r-simulations-store', 'data'),
     State('r-prog-to-delete', 'value'),
     State('r-premium-principle', 'value'),
     State('r-premium-loading', 'value'),
     State('r-premium-alpha-std', 'value'),
     State('r-premium-alpha-var', 'value')],
    prevent_initial_call=True
)
def r_manage_programs(n_save, n_del, n_reset, stack, name, saved, sims, prog_to_del,
                      principle, loading, alpha_std, alpha_var):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    current = (saved or []).copy()
    opts = [{'label': p['name'], 'value': p['id']} for p in current if p['id'] != 'brut']

    if trigger == 'r-btn-reset':
        current = [p for p in current if p['id'] == 'brut']
        return current, [], []

    if trigger == 'r-btn-delete-prog' and prog_to_del:
        current = [p for p in current if p['id'] != prog_to_del]
        return current, dash.no_update, [
            {'label': p['name'], 'value': p['id']} for p in current if p['id'] != 'brut'
        ]

    if trigger == 'r-btn-save-prog' and sims:
        traites = stack or []
        principle = principle or 'expected_value'
        param = _get_premium_param(principle, loading, alpha_std, alpha_var)

        # Stats brutes S (6 valeurs)
        e, s, v95, v99, v995, tv99 = stats_programme(_ds(sims), traites)

        # Stats nettes D = S-R+P_R
        full = compute_full_stats(_ds(sims), traites, principle=principle, param=param)
        net_m = full['net']
        prem  = full['premium']

        gross_arr, net_arr = compute_ceded_charges(_ds(sims), traites)
        mean_gross = float(np.mean(gross_arr))
        bc = float(np.mean(gross_arr - net_arr) / mean_gross) if mean_gross > 0 else 0.0

        new_id = f"prog_{len(current)}_{np.random.randint(9999)}"
        p_name = (name.strip() if name and name.strip()
                  else f"Programme {len([p for p in current if p['id'] != 'brut']) + 1}")

        current.append({
            'id': new_id, 'name': p_name,
            # Brut S
            'esp': e, 'std': s, 'var95': v95, 'var99': v99, 'var995': v995, 'tvar99': tv99,
            # Net D = S-R+P_R
            'net_esp':    net_m['mean'],
            'net_std':    net_m['std'],
            'net_var95':  net_m['var95'],
            'net_var99':  net_m['var99'],
            'net_tvar99': net_m['tvar99'],
            # Prime
            'premium':   prem['P_R'],
            'principle': prem['principle'],
            'param':     prem['param'],
            'burning_cost': bc,
            'desc': formater_description(traites),
            'stack': traites,
        })
        return current, [], [
            {'label': p['name'], 'value': p['id']} for p in current if p['id'] != 'brut'
        ]

    return dash.no_update, dash.no_update, opts


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INDICATEURS — PRIME BOX + 5 ONGLETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    [# Prime box
     Output('r-pr-value',           'children'),
     Output('r-pr-principle-label', 'children'),
     Output('r-pr-param-label',     'children'),
     Output('r-pr-er',              'children'),
     Output('r-pr-stdr',            'children'),
     # Tab 1 — Espérances
     Output('r-es-gross',  'children'),
     Output('r-es-net',    'children'),
     Output('r-ed-gross',  'children'),
     Output('r-ed-net',    'children'),
     Output('r-er-gross',  'children'),
     Output('r-er-net',    'children'),
     Output('r-pr-tab1',   'children'),
     # Tab 2 — Dispersion
     Output('r-vars-gross', 'children'),
     Output('r-vars-net',   'children'),
     Output('r-stds-gross', 'children'),
     Output('r-stds-net',   'children'),
     # Tab 3 — Risque extrême
     Output('r-var95-gross',  'children'),
     Output('r-var95-net',    'children'),
     Output('r-var99-gross',  'children'),
     Output('r-var99-net',    'children'),
     Output('r-tvar95-gross', 'children'),
     Output('r-tvar95-net',   'children'),
     Output('r-tvar99-gross', 'children'),
     Output('r-tvar99-net',   'children'),
     # Tab 4 — Solvabilité
     Output('r-ruin-gross', 'children'),
     Output('r-ruin-net',   'children'),
     # Tab 5 — Rentabilité
     Output('r-profit-result',    'children'),
     Output('r-profit-cost',      'children'),
     Output('r-profit-reduction', 'children')],
    [Input('r-simulations-store',    'data'),
     Input('r-detail-prog-dropdown', 'value'),
     Input('r-saved-programs-store', 'data'),
     Input('r-premium-principle',    'value'),
     Input('r-premium-loading',      'value'),
     Input('r-premium-alpha-std',    'value'),
     Input('r-premium-alpha-var',    'value'),
     Input('r-capital-input',        'value')],
)
def r_update_indicators(sims, prog_id, progs, principle, loading, alpha_std, alpha_var, capital):
    na = '—'
    empty = tuple([na] * 29)

    if not sims:
        return empty

    # Lire le stack depuis le programme sélectionné
    # Si prog_id est None, prendre le premier programme non-brut disponible
    traites = []
    if progs:
        if prog_id:
            prog = next((p for p in progs if p['id'] == prog_id), None)
        else:
            prog = next((p for p in progs if p['id'] != 'brut'), None)
        if prog:
            traites = prog.get('stack', [])

    principle = principle or 'expected_value'
    param     = _get_premium_param(principle, loading, alpha_std, alpha_var)
    cap       = float(capital) if capital else None

    try:
        full = compute_full_stats(_ds(sims), traites, principle=principle, param=param, capital=cap)
    except Exception:
        return empty

    p  = full['premium']
    g  = full['gross']
    n  = full['net']
    r  = full['ceded']
    pr = full['profitability']

    def fmt(v):
        return _fmt_eur(v) if v is not None else na

    def fmt_pct(v):
        return f"{v*100:.3f} %" if v is not None else na

    principle_short = {
        'expected_value': "Valeur espérée",
        'std_deviation':  "Écart-type",
        'variance':       "Variance",
    }.get(p['principle'], p['principle'])

    param_label = {
        'expected_value': f"θ = {p['param']:.3f}",
        'std_deviation':  f"α = {p['param']:.3f}",
        'variance':       f"α = {p['param']:.4f}",
    }.get(p['principle'], str(p['param']))

    ruin_gross = fmt_pct(g['ruin']) if g['ruin'] is not None else "Entrez un capital"
    ruin_net   = fmt_pct(n['ruin']) if n['ruin'] is not None else "Entrez un capital"

    return (
        # Prime box
        fmt(p['P_R']),
        principle_short,
        param_label,
        fmt(p['E_R']),
        fmt(p['Std_R']),
        # Tab 1 — Espérances
        fmt(g['mean']), fmt(n['mean']),   # E[S], E[D]
        fmt(g['mean']), fmt(n['mean']),   # répété pour E[D] brut/net
        fmt(r['mean']), fmt(r['mean']),   # E[R]
        fmt(p['P_R']),                    # P_R
        # Tab 2 — Dispersion
        fmt(g['var']),  fmt(n['var']),
        fmt(g['std']),  fmt(n['std']),
        # Tab 3 — Risque extrême
        fmt(g['var95']),  fmt(n['var95']),
        fmt(g['var99']),  fmt(n['var99']),
        fmt(g['tvar95']), fmt(n['tvar95']),
        fmt(g['tvar99']), fmt(n['tvar99']),
        # Tab 4 — Solvabilité
        ruin_gross, ruin_net,
        # Tab 5 — Rentabilité
        fmt(pr['expected_result_net']),
        fmt(pr['cost_of_reins']),
        fmt(pr['risk_reduction']),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BANDE KPI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    Output('r-summary-kpis', 'children'),
    Input('r-saved-programs-store', 'data')
)
def r_render_summary_kpis(progs):
    if not progs:
        return html.Div()

    df = pd.DataFrame(progs)
    brut_row = df[df['id'] == 'brut']
    others   = df[df['id'] != 'brut']

    if brut_row.empty:
        return html.Div()

    brut_esp   = float(brut_row['esp'].values[0])
    brut_var99 = float(brut_row['var99'].values[0])
    brut_std   = float(brut_row['std'].values[0])
    n_progs    = len(others)

    cards = [
        _kpi_card("Charge brute — ESP",     _fmt_eur(brut_esp),
                  "Coût moyen annuel sans réassurance", PALETTE['danger'], PALETTE['danger']),
        _kpi_card("Charge brute — VaR 99%", _fmt_eur(brut_var99),
                  "Scénario 1 an sur 100",              PALETTE['danger'], PALETTE['danger']),
        _kpi_card("Volatilité brute (σ)",   _fmt_eur(brut_std),
                  "Écart-type des charges annuelles",   PALETTE['warning'], PALETTE['warning']),
    ]

    if not others.empty:
        cmp_col = 'net_var99' if 'net_var99' in others.columns else 'var99'
        best = others.loc[others[cmp_col].idxmin()]
        best_var99  = float(best[cmp_col])
        esp_col     = 'net_esp' if 'net_esp' in best.index else 'esp'
        best_esp    = float(best[esp_col])
        red_var99   = _pct_reduction(best_var99, brut_var99)
        red_esp     = _pct_reduction(best_esp, brut_esp)
        bc_pct      = float(best.get('burning_cost', 0) or 0) * 100
        prem_val    = best.get('premium', None)
        prem_str    = f"  ·  P_R = {_fmt_eur(prem_val)}" if prem_val else ''

        cards += [
            _kpi_card(
                "Meilleur programme (net D)",
                best['name'],
                best.get('desc', ''),
                PALETTE['success'], PALETTE['success'],
            ),
            _kpi_card(
                "Réduction VaR 99% net",
                f"−{red_var99:.1f}%",
                f"{_fmt_eur(best_var99)}  ·  ESP −{red_esp:.1f}%{prem_str}",
                PALETTE['success'], PALETTE['success'],
            ),
            _kpi_card(
                "Burning Cost (meilleur)",
                f"{bc_pct:.1f}%",
                f"Part du brut cédée  ·  {n_progs} programme{'s' if n_progs > 1 else ''} testé{'s' if n_progs > 1 else ''}",
                PALETTE['accent2'], PALETTE['accent2'],
            ),
        ]
    else:
        cards.append(_kpi_card(
            "Programmes testés", "0",
            "Configurez un programme dans la colonne de gauche",
            PALETTE['text_muted'], PALETTE['border'],
        ))

    return html.Div([html.Div(cards, style={'display': 'flex', 'gap': '12px'})])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DROPDOWN RETENU / CÉDÉ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    [Output('r-detail-prog-dropdown', 'options'),
     Output('r-detail-prog-dropdown', 'value')],
    Input('r-saved-programs-store', 'data')
)
def r_update_detail_dropdown(progs):
    if not progs:
        return [], None
    opts     = [{'label': p['name'], 'value': p['id']} for p in progs]
    non_brut = [p for p in progs if p['id'] != 'brut']
    default  = non_brut[0]['id'] if non_brut else progs[0]['id']
    return opts, default


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDU PRINCIPAL — frontière + indicateurs + tables
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
    _empty = go.Figure()
    _empty.update_layout(plotly_layout("Générez les simulations et ajoutez des programmes"))
    no_prog_msg = html.Div("Aucun programme.",
                           style={'color': PALETTE['text_muted'], 'padding': '16px'})

    if not progs:
        return _empty, _empty, no_prog_msg, html.Div()

    df_p   = pd.DataFrame(progs)
    brut   = df_p[df_p['id'] == 'brut']
    others = df_p[df_p['id'] != 'brut']

    # Colonnes net (D) si disponibles, sinon fallback sur brut
    esp_col   = 'net_esp'    if 'net_esp'    in df_p.columns else 'esp'
    std_col   = 'net_std'    if 'net_std'    in df_p.columns else 'std'
    var99_col = 'net_var99'  if 'net_var99'  in df_p.columns else 'var99'
    var95_col = 'net_var95'  if 'net_var95'  in df_p.columns else 'var95'
    tvar_col  = 'net_tvar99' if 'net_tvar99' in df_p.columns else 'tvar99'

    has_target = std_min is not None or std_max is not None
    s_min = std_min or 0
    s_max = std_max or float('inf')

    if has_target and not others.empty:
        mask     = (others[std_col] >= s_min) & (others[std_col] <= s_max)
        df_cible = others[mask]
        df_hors  = others[~mask]
    else:
        df_cible = others
        df_hors  = pd.DataFrame()

    brut_esp   = float(brut['esp'].values[0])    if not brut.empty else None
    brut_var99 = float(brut['var99'].values[0])   if not brut.empty else None
    brut_var95 = float(brut['var95'].values[0])   if not brut.empty else None
    brut_tvar  = float(brut['tvar99'].values[0])  if not brut.empty else None
    brut_std   = float(brut['std'].values[0])     if not brut.empty else None

    # ── Frontière efficace ──────────────────────────────────────
    fig_f = go.Figure()

    if has_target and std_min is not None and std_max is not None:
        fig_f.add_hrect(y0=s_min, y1=s_max, line_width=0,
                        fillcolor=PALETTE['success'], opacity=0.06, layer="below")
        fig_f.add_hline(y=s_min, line_dash='dot', line_color=PALETTE['success'], opacity=0.5)
        fig_f.add_hline(y=s_max, line_dash='dot', line_color=PALETTE['success'], opacity=0.5)

    def _hover_txt(row):
        bc      = row.get('burning_cost', None)
        bc_str  = f"{bc*100:.1f}%" if bc is not None and bc > 0 else "—"
        prem    = row.get('premium', None)
        p_str   = _fmt_eur(prem) if prem else "—"
        r99     = _pct_reduction(row.get(var99_col, row['var99']), brut_var99)
        return (
            f"<b>{row['name']}</b><br>"
            f"Structure : {row.get('desc','—')}<br>"
            f"ESP net D : {_fmt_eur(row.get(esp_col, row['esp']))}<br>"
            f"σ net : {_fmt_eur(row.get(std_col, row['std']))}<br>"
            f"VaR 99% net : {_fmt_eur(row.get(var99_col, row['var99']))}  (−{r99:.1f}% vs brut)<br>"
            f"TVaR 99% net : {_fmt_eur(row.get(tvar_col, row['tvar99']))}<br>"
            f"Prime P_R : {p_str}<br>"
            f"Burning cost : {bc_str}"
            "<extra></extra>"
        )

    if not brut.empty:
        br = brut.iloc[0]
        fig_f.add_trace(go.Scatter(
            x=[br['esp']], y=[br['std']],
            mode='markers+text', name="BRUT", text=["BRUT"],
            textposition="top center",
            hovertemplate=_hover_txt(br),
            marker=dict(size=20, color=PALETTE['danger'], symbol='x',
                        line=dict(width=3, color=PALETTE['danger'])),
            textfont=dict(color=PALETTE['danger'], size=12,
                          family="'JetBrains Mono', monospace"),
        ))

    def _add_scatter(df_sub, name, color, size=12):
        if df_sub.empty:
            return
        x_vals     = df_sub[esp_col] if esp_col in df_sub.columns else df_sub['esp']
        y_vals     = df_sub[std_col] if std_col in df_sub.columns else df_sub['std']
        customdata = [_hover_txt(row) for _, row in df_sub.iterrows()]
        fig_f.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode='markers+text', name=name,
            text=df_sub['name'], textposition="top center",
            hovertemplate="%{customdata}", customdata=customdata,
            marker=dict(size=size, color=color,
                        line=dict(width=1.5, color=PALETTE['surface'])),
            textfont=dict(color=color, size=10, family="'JetBrains Mono', monospace"),
        ))

    _add_scatter(df_cible, "Dans la cible" if has_target else "Programmes",
                 PALETTE['success'] if has_target else PALETTE['accent2'])
    _add_scatter(df_hors, "Hors cible", PALETTE['text_muted'], size=9)

    lf = plotly_layout("Frontière Efficace — ESP net vs σ net (D = S−R+P_R)", height=500)
    lf['xaxis'].update(title="Espérance D (€)", tickformat=',.0f', exponentformat='none')
    lf['yaxis'].update(title="Écart-type σ net (€)", tickformat=',.0f', exponentformat='none')
    fig_f.update_layout(lf)

    # ── Indicateurs % réduction ──────────────────────────────────
    fig_m = go.Figure()

    if brut.empty or others.empty:
        fig_m.update_layout(plotly_layout("Ajoutez des programmes pour comparer"))
    else:
        oth = others.copy()
        oth['red_var99'] = oth[var99_col].apply(lambda v: _pct_reduction(v, brut_var99))
        oth = oth.sort_values('red_var99', ascending=True)

        refs = {
            esp_col:   brut_esp,
            var95_col: brut_var95,
            var99_col: brut_var99,
            tvar_col:  brut_tvar,
        }
        metrics_def = [
            (esp_col,   'Réduction ESP net (D)',      PALETTE['accent2']),
            (var95_col, 'Réduction VaR 95% net',      PALETTE['warning']),
            (var99_col, 'Réduction VaR 99% net',      PALETTE['danger']),
            (tvar_col,  'Réduction TVaR 99% net',     '#E8544A'),
        ]
        for col, label, color in metrics_def:
            ref = refs.get(col)
            if ref is None or ref == 0 or col not in oth.columns:
                continue
            pcts  = [_pct_reduction(v, ref) for v in oth[col]]
            texts = [f"{p:+.1f}%" for p in pcts]
            fig_m.add_trace(go.Bar(
                name=label, x=pcts, y=oth['name'],
                orientation='h', marker_color=color, opacity=0.82,
                text=texts, textposition='outside',
                textfont=dict(size=11, color=PALETTE['text']),
                hovertemplate=(
                    f"<b>%{{y}}</b> — {label}<br>"
                    "Réduction vs Brut : %{x:+.1f}%<br><extra></extra>"
                ),
                width=0.6,
            ))

        fig_m.add_vline(x=0, line_width=2, line_color=PALETTE['danger'], opacity=0.6,
                        annotation_text="BRUT",
                        annotation_font=dict(color=PALETTE['danger'], size=10),
                        annotation_position="bottom right")

        n_prog     = len(oth)
        chart_h    = max(300, 120 + n_prog * 60)
        lm = plotly_layout("Réduction des indicateurs net (D = S−R+P_R) vs BRUT",
                           height=chart_h)
        lm['xaxis'].update(title="Réduction (%) — positif = meilleure protection",
                           ticksuffix="%", zeroline=True,
                           zerolinecolor=PALETTE['danger'], zerolinewidth=1.5)
        lm['yaxis'].update(title="", tickfont=dict(size=12, color=PALETTE['text']))
        lm['barmode'] = 'group'
        lm['legend'].update(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
        lm['margin'].update(l=140, r=80, t=80, b=60)
        fig_m.update_layout(lm)

    # ── Tableau comparatif ───────────────────────────────────────
    def _make_table(df):
        if df.empty:
            return html.Div("Aucun programme.",
                            style={'color': PALETTE['text_muted'], 'padding': '12px'})
        rows = []
        for _, row in df.iterrows():
            is_brut = row['id'] == 'brut'

            def _cell(col, ref_val):
                v = row.get(col, None)
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    return 'N/A'
                base = _fmt_eur(v)
                if is_brut or ref_val is None or ref_val == 0:
                    return base
                pct   = _pct_reduction(v, ref_val)
                arrow = "▼" if pct > 0 else "▲"
                return f"{base}  {arrow}{abs(pct):.1f}%"

            bc   = row.get('burning_cost', None)
            prem = row.get('premium', None)
            rows.append({
                'name':  row['name'],
                'desc':  row.get('desc', '—'),
                'esp':   _cell(esp_col   if esp_col   in row.index else 'esp',   brut_esp),
                'std':   _cell(std_col   if std_col   in row.index else 'std',   brut_std),
                'var95': _cell(var95_col if var95_col in row.index else 'var95', brut_var95),
                'var99': _cell(var99_col if var99_col in row.index else 'var99', brut_var99),
                'tvar':  _cell(tvar_col  if tvar_col  in row.index else 'tvar99', brut_tvar),
                'prem':  '—' if is_brut else (_fmt_eur(prem) if prem is not None else '—'),
                'bc':    '—' if is_brut else (f"{bc*100:.1f}%" if bc is not None else '—'),
            })

        cond = [
            {'if': {'row_index': 'odd'}, 'backgroundColor': PALETTE['surface2']},
            {'if': {'row_index': 0},
             'backgroundColor': '#1A0A0A', 'color': PALETTE['danger'], 'fontWeight': '700'},
        ]
        for col_id in ['esp', 'std', 'var95', 'var99', 'tvar']:
            cond += [
                {'if': {'filter_query': f'{{{col_id}}} contains "▼"', 'column_id': col_id},
                 'color': PALETTE['success']},
                {'if': {'filter_query': f'{{{col_id}}} contains "▲"', 'column_id': col_id},
                 'color': PALETTE['danger']},
            ]

        return dash_table.DataTable(
            data=rows,
            columns=[
                {'name': 'Programme',      'id': 'name'},
                {'name': 'Structure',       'id': 'desc'},
                {'name': 'ESP net D',       'id': 'esp'},
                {'name': 'σ net',           'id': 'std'},
                {'name': 'VaR 95% net',     'id': 'var95'},
                {'name': 'VaR 99% net',     'id': 'var99'},
                {'name': 'TVaR 99% net',    'id': 'tvar'},
                {'name': 'Prime P_R',       'id': 'prem'},
                {'name': 'Burning Cost',    'id': 'bc'},
            ],
            style_table={'overflowX': 'auto', 'borderRadius': '8px',
                         'border': f"1px solid {PALETTE['border']}"},
            style_cell={
                'textAlign': 'center', 'padding': '10px 14px', 'fontSize': '12px',
                'backgroundColor': PALETTE['surface'], 'color': PALETTE['text'],
                'border': f"1px solid {PALETTE['border']}",
                'fontFamily': "'JetBrains Mono', monospace",
                'whiteSpace': 'normal', 'minWidth': '90px',
            },
            style_cell_conditional=[
                {'if': {'column_id': 'name'}, 'textAlign': 'left', 'fontWeight': '600',
                 'color': PALETTE['text'], 'minWidth': '110px'},
                {'if': {'column_id': 'desc'}, 'textAlign': 'left', 'fontSize': '11px',
                 'color': PALETTE['text_muted'], 'minWidth': '150px'},
                {'if': {'column_id': 'prem'}, 'color': PALETTE['warning']},
            ],
            style_header={
                'backgroundColor': PALETTE['surface2'], 'color': PALETTE['accent'],
                'fontWeight': '700', 'fontSize': '11px', 'letterSpacing': '0.8px',
                'textTransform': 'uppercase', 'border': f"1px solid {PALETTE['border']}",
            },
            style_data_conditional=cond,
        )

    table_all = _make_table(df_p)
    if has_target:
        table_filtered = (_make_table(df_cible) if not df_cible.empty
                         else html.Div("Aucun programme dans la zone cible.",
                                       style={'color': PALETTE['text_muted'], 'padding': '12px'}))
    else:
        table_filtered = html.Div(
            "Définissez un Écart-type Min/Max dans la colonne gauche pour filtrer.",
            style={'color': PALETTE['text_muted'], 'fontSize': '13px', 'padding': '12px'},
        )

    return fig_f, fig_m, table_all, table_filtered


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OEP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    [Output('r-oep-graph', 'figure'),
     Output('r-oep-ref-table', 'children')],
    [Input('r-saved-programs-store', 'data'),
     Input('r-simulations-store',   'data'),
     Input('r-premium-principle',   'value'),
     Input('r-premium-loading',     'value'),
     Input('r-premium-alpha-std',   'value'),
     Input('r-premium-alpha-var',   'value')]
)
def r_render_oep(progs, sims, principle, loading, alpha_std, alpha_var):
    _empty = go.Figure()
    _empty.update_layout(plotly_layout("Générez les simulations et ajoutez des programmes"))

    if not progs or not sims:
        return _empty, html.Div()

    principle = principle or 'expected_value'
    param     = _get_premium_param(principle, loading, alpha_std, alpha_var)
    n_sims    = len(sims)
    fig       = go.Figure()

    prog_colors = [PALETTE['danger'], PALETTE['success'], PALETTE['accent2'],
                   PALETTE['warning'], '#A78BFA', '#F472B6', '#34D399', '#60A5FA']
    ref_rows = []

    for i, prog in enumerate(progs):
        stack = prog.get('stack', [])
        try:
            if stack:
                full = compute_full_stats(_ds(sims), stack, principle=principle, param=param)
                ch   = full['_D']
            else:
                ch = compute_charges(_ds(sims), stack)
        except Exception:
            continue

        n           = len(ch)
        sorted_ch   = np.sort(ch)[::-1]
        ranks       = np.arange(1, n + 1)
        rp          = n / ranks
        color       = prog_colors[0] if prog['id'] == 'brut' else prog_colors[min(i, len(prog_colors)-1)]
        dash_style  = 'dash' if prog['id'] == 'brut' else 'solid'
        width       = 2.8 if prog['id'] == 'brut' else 2.0
        label_sfx   = '' if prog['id'] == 'brut' else ' (D net)'
        val_20  = float(sorted_ch[max(0, min(n-1, int(n/20)-1))])
        val_100 = float(sorted_ch[max(0, min(n-1, int(n/100)-1))])

        ref_rows.append({'name': prog['name']+label_sfx, 'v20': _fmt_eur(val_20),
                         'v100': _fmt_eur(val_100), 'color': color})

        fig.add_trace(go.Scatter(
            x=rp, y=sorted_ch, name=prog['name']+label_sfx, mode='lines',
            line=dict(color=color, width=width, dash=dash_style),
            hovertemplate=(
                f"<b>{prog['name']}</b><br>"
                "Période de retour : %{x:.0f} ans<br>"
                "Perte : %{y:,.0f} €<extra></extra>"
            ),
        ))
        for rp_val, val in [(20, val_20), (100, val_100)]:
            if rp_val <= n:
                fig.add_trace(go.Scatter(
                    x=[rp_val], y=[val], mode='markers',
                    marker=dict(size=7, color=color, symbol='circle',
                                line=dict(width=1.5, color=PALETTE['surface'])),
                    showlegend=False,
                    hovertemplate=(f"<b>{prog['name']}</b><br>1/{rp_val} ans : "
                                   f"{_fmt_eur(val)}<extra></extra>"),
                ))

    for rp_val, label, c in [
        (20,  "← 1/20 ans (VaR 95%)",  PALETTE['warning']),
        (100, "← 1/100 ans (VaR 99%)", PALETTE['danger']),
    ]:
        if rp_val <= n_sims:
            fig.add_vline(x=rp_val, line_dash='dot', line_color=c, opacity=0.7,
                          line_width=1.5, annotation_text=label,
                          annotation_font=dict(color=c, size=10),
                          annotation_position="top left")

    lo = plotly_layout("Courbe OEP — Brut (S) et Net (D = S−R+P_R)", height=480)
    lo['xaxis'].update(
        title="Période de retour (années)",
        type='log',
        autorange=True,
        tickformat='.0f',
        dtick=None,
    )
    lo['yaxis'].update(title="Perte annuelle (€)", tickformat=',.0f', exponentformat='none')
    lo['legend'].update(orientation='v', x=1.01, y=1, xanchor='left')
    lo['margin'].update(r=160)
    fig.update_layout(lo)

    if not ref_rows:
        ref_table = html.Div()
    else:
        ref_table = html.Div([
            html.Div("Valeurs aux points de référence", style={
                'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '1px',
                'textTransform': 'uppercase', 'color': PALETTE['text_muted'],
                'marginBottom': '10px',
            }),
            html.Div([
                html.Div([
                    html.Div(style={'width': '10px', 'height': '10px', 'borderRadius': '50%',
                                    'backgroundColor': r['color'], 'marginRight': '8px',
                                    'flexShrink': '0'}),
                    html.Span(r['name'], style={'flex': '1', 'fontSize': '12px',
                                                'fontWeight': '600'}),
                    html.Span(f"1/20 ans : {r['v20']}", style={
                        'fontSize': '12px', 'color': PALETTE['warning'],
                        'fontFamily': "'JetBrains Mono', monospace", 'marginRight': '20px'}),
                    html.Span(f"1/100 ans : {r['v100']}", style={
                        'fontSize': '12px', 'color': PALETTE['danger'],
                        'fontFamily': "'JetBrains Mono', monospace"}),
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '8px'})
                for r in ref_rows
            ]),
        ], style={'backgroundColor': PALETTE['surface2'],
                  'border': f"1px solid {PALETTE['border']}",
                  'borderRadius': '8px', 'padding': '14px 18px'})

    return fig, ref_table


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RETENU / CÉDÉ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    [Output('r-retained-ceded-graph', 'figure'),
     Output('r-retained-kpis', 'children')],
    [Input('r-detail-prog-dropdown', 'value'),
     Input('r-saved-programs-store', 'data'),
     Input('r-premium-principle',    'value'),
     Input('r-premium-loading',      'value'),
     Input('r-premium-alpha-std',    'value'),
     Input('r-premium-alpha-var',    'value')],
    State('r-simulations-store', 'data')
)
def r_render_retained_ceded(prog_id, progs, principle, loading, alpha_std, alpha_var, sims):
    empty_fig = go.Figure()
    empty_fig.update_layout(plotly_layout("Sélectionnez un programme", height=380))

    if not prog_id or not progs or not sims:
        return empty_fig, html.Div()

    prog = next((p for p in progs if p['id'] == prog_id), None)
    if not prog:
        return empty_fig, html.Div()

    stack = prog.get('stack', [])
    try:
        gross_arr, net_no_prem = compute_ceded_charges(_ds(sims), stack)
    except Exception:
        return empty_fig, html.Div()

    ceded_arr = gross_arr - net_no_prem
    principle = principle or 'expected_value'
    param     = _get_premium_param(principle, loading, alpha_std, alpha_var)
    P_R       = 0.0
    if stack:
        try:
            P_R, _ = compute_premium(ceded_arr, principle, param)
        except Exception:
            pass

    net_arr     = net_no_prem + P_R
    n           = len(net_arr)
    mean_gross  = float(np.mean(gross_arr))
    mean_net    = float(np.mean(net_arr))
    mean_ceded  = float(np.mean(ceded_arr))
    p99_net     = float(np.percentile(net_arr, 99))
    bc_pct      = mean_ceded / mean_gross * 100 if mean_gross > 0 else 0.0

    kpis = html.Div([
        _kpi_card("ESP Retenu D",     _fmt_eur(mean_net),   "Charge nette avec prime P_R",
                  PALETTE['success'], PALETTE['success']),
        _kpi_card("ESP Cédé",         _fmt_eur(mean_ceded), "Charge moyenne réassureur",
                  PALETTE['warning'], PALETTE['warning']),
        _kpi_card("Burning Cost",     f"{bc_pct:.1f}%",     "Part du brut cédée",
                  PALETTE['accent2'], PALETTE['accent2']),
        _kpi_card("VaR 99% net D",    _fmt_eur(p99_net),    "Scénario 1/100 ans — cédante",
                  PALETTE['danger'],  PALETTE['danger']),
        _kpi_card("Prime P_R",        _fmt_eur(P_R),        "Prime de réassurance annuelle",
                  PALETTE['warning'], PALETTE['warning']),
    ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '16px'})

    fig = go.Figure()
    fig.add_trace(go.Box(
        y=gross_arr, name="Brut (S)",
        marker_color=PALETTE['text_muted'],
        line=dict(color=PALETTE['text_muted'], width=1.5),
        fillcolor=_hex_rgba(PALETTE['text_muted'], 0.12),
        boxpoints='outliers', jitter=0.3, marker=dict(size=3, opacity=0.4),
        hovertemplate="Brut<br>%{y:,.0f} €<extra></extra>",
    ))
    fig.add_trace(go.Box(
        y=net_arr, name="Retenu D = S−R+P_R",
        marker_color=PALETTE['success'],
        line=dict(color=PALETTE['success'], width=2),
        fillcolor=_hex_rgba(PALETTE['success'], 0.15),
        boxpoints='outliers', jitter=0.3, marker=dict(size=3, opacity=0.5),
        hovertemplate="Retenu net<br>%{y:,.0f} €<extra></extra>",
    ))
    fig.add_trace(go.Box(
        y=ceded_arr, name="Cédé (R)",
        marker_color=PALETTE['warning'],
        line=dict(color=PALETTE['warning'], width=2),
        fillcolor=_hex_rgba(PALETTE['warning'], 0.15),
        boxpoints='outliers', jitter=0.3, marker=dict(size=3, opacity=0.5),
        hovertemplate="Cédé<br>%{y:,.0f} €<extra></extra>",
    ))

    lo = plotly_layout(f"Distribution Brut / Retenu net D / Cédé — {prog['name']}", height=420)
    lo['yaxis'].update(title="Charge annuelle (€)", tickformat=',.0f', exponentformat='none')
    lo['xaxis'].update(title="")
    lo['boxmode'] = 'group'
    lo['showlegend'] = True
    lo['annotations'] = [dict(
        x=0.5, y=1.05, xref='paper', yref='paper',
        text=f"D = S−R+P_R  ·  P_R = {_fmt_eur(P_R)}  ·  {n:,} simulations",
        showarrow=False,
        font=dict(size=10, color=PALETTE['text_muted']),
        align='center',
    )]
    fig.update_layout(lo)
    return fig, kpis


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEATMAP SENSIBILITÉ XS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.callback(
    [Output('r-heatmap-graph', 'figure'),
     Output('r-heatmap-status', 'children')],
    Input('r-btn-heatmap', 'n_clicks'),
    [State('r-heatmap-prio-min',   'value'),
     State('r-heatmap-prio-max',   'value'),
     State('r-heatmap-portee-min', 'value'),
     State('r-heatmap-portee-max', 'value'),
     State('r-heatmap-steps',      'value'),
     State('r-simulations-store',  'data'),
     State('r-premium-principle',  'value'),
     State('r-premium-loading',    'value'),
     State('r-premium-alpha-std',  'value'),
     State('r-premium-alpha-var',  'value')],
    prevent_initial_call=True
)
def r_render_heatmap(n_clicks, prio_min, prio_max, portee_min, portee_max, steps, sims,
                     principle, loading, alpha_std, alpha_var):
    empty_fig = go.Figure()
    empty_fig.update_layout(plotly_layout("Configurez les paramètres et cliquez Calculer"))

    if not sims:
        return empty_fig, "⚠  Générez d'abord les simulations."

    try:
        prio_min   = float(prio_min   or 50_000)
        prio_max   = float(prio_max   or 500_000)
        portee_min = float(portee_min or 100_000)
        portee_max = float(portee_max or 1_000_000)
        steps      = max(4, min(20, int(steps or 8)))
    except (TypeError, ValueError):
        return empty_fig, "⚠  Paramètres invalides."

    principle   = principle or 'expected_value'
    param       = _get_premium_param(principle, loading, alpha_std, alpha_var)
    prio_list   = np.linspace(prio_min,   prio_max,   steps)
    portee_list = np.linspace(portee_min, portee_max, steps)

    # Heatmap sur D = S-R+P_R
    matrix = np.zeros((len(portee_list), len(prio_list)))
    for j, prio in enumerate(prio_list):
        for i, portee in enumerate(portee_list):
            traite = [{'type': 'XS', 'priorite': float(prio), 'portee': float(portee)}]
            full   = compute_full_stats(_ds(sims), traite, principle=principle, param=param)
            matrix[i, j] = full['net']['mean']

    x_labels = [_fmt_eur(v) for v in prio_list]
    y_labels = [_fmt_eur(v) for v in portee_list]
    min_idx  = np.unravel_index(np.argmin(matrix), matrix.shape)
    text_mat = [[_fmt_eur(matrix[i, j]) for j in range(len(prio_list))]
                for i in range(len(portee_list))]

    fig = go.Figure(go.Heatmap(
        z=matrix, x=x_labels, y=y_labels,
        text=text_mat, texttemplate="%{text}",
        textfont=dict(size=9, color='white', family="'JetBrains Mono', monospace"),
        colorscale=[[0.0, '#0D4A38'], [0.25, PALETTE['success']],
                    [0.55, PALETTE['warning']], [1.0, PALETTE['danger']]],
        colorbar=dict(
            title=dict(text="ESP net D (€)", font=dict(color=PALETTE['text'], size=11)),
            tickformat=',.0f', tickfont=dict(color=PALETTE['text_muted'], size=10),
            outlinewidth=0,
        ),
        hovertemplate="Priorité : %{x}<br>Portée : %{y}<br>ESP net D : %{text}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[x_labels[min_idx[1]]], y=[y_labels[min_idx[0]]],
        mode='markers+text', text=["OPTIMUM"], textposition="top center",
        marker=dict(size=14, color='white', symbol='star',
                    line=dict(width=1.5, color=PALETTE['success'])),
        textfont=dict(color='white', size=9, family="'JetBrains Mono', monospace"),
        showlegend=False,
        hovertemplate=f"<b>Optimum</b><br>ESP net D : {_fmt_eur(matrix[min_idx])}<extra></extra>",
    ))

    lo = plotly_layout(
        f"Heatmap Sensibilité XS — ESP net D = S−R+P_R ({steps}×{steps} combinaisons)",
        height=500)
    lo['xaxis'].update(title="Priorité XS", tickangle=-30, tickfont=dict(size=10))
    lo['yaxis'].update(title="Portée XS", tickfont=dict(size=10))
    lo['margin'].update(l=110, r=100, b=110, t=70)
    fig.update_layout(lo)

    best_prio   = prio_list[min_idx[1]]
    best_portee = portee_list[min_idx[0]]
    status = (
        f"✓  Grille {steps}×{steps} calculée  ·  "
        f"Optimum : {_fmt_eur(best_portee)} xs {_fmt_eur(best_prio)}"
        f"  →  ESP net D {_fmt_eur(matrix[min_idx])}"
    )
    return fig, status
