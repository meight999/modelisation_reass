from dash import dcc, html
from config import PALETTE, SEV_DIST_NAMES, FREQ_DIST_NAMES
from components.ui import card, section_title, btn_primary, btn_secondary

_tab_style = {
    'color': PALETTE['text_muted'],
    'backgroundColor': PALETTE['surface2'],
    'fontSize': '12px',
    'padding': '9px 14px',
    'fontWeight': '500',
}
_tab_selected_style = {
    'color': PALETTE['accent2'],
    'backgroundColor': PALETTE['surface'],
    'fontSize': '12px',
    'padding': '9px 14px',
    'fontWeight': '700',
    'borderTop': f"2px solid {PALETTE['accent2']}",
}

_inp = {
    'width': '100%',
    'backgroundColor': PALETTE['surface2'],
    'border': f"1px solid {PALETTE['border']}",
    'color': PALETTE['text'],
    'borderRadius': '6px',
    'padding': '8px 12px',
    'fontFamily': "'JetBrains Mono', monospace",
    'fontSize': '13px',
}
_lbl = {'color': PALETTE['text_muted'], 'fontSize': '12px', 'display': 'block', 'marginBottom': '4px'}

PAGE_REASSURANCE = html.Div([
    html.Div([

        # ── COLONNE GAUCHE ───────────────────────────────────────────────
        html.Div([

            # 1 — Modèle de simulation
            card([
                section_title("1 — Simulation", PALETTE['accent2']),

                html.Div(id='r-model-status-banner'),

                html.Details([
                    html.Summary("⚙  Overrides distributions (optionnel)", style={
                        'color': PALETTE['text_muted'], 'fontSize': '12px',
                        'cursor': 'pointer', 'marginBottom': '8px', 'letterSpacing': '0.5px',
                    }),
                    html.Div([
                        html.Label("Sév. ↓ sous seuil", style=_lbl),
                        dcc.Dropdown(id='r-override-bsev', clearable=True, placeholder="Auto (AIC)",
                                     options=[{'label': v, 'value': k} for k, v in SEV_DIST_NAMES.items()],
                                     style={'marginBottom': '6px'}),
                        html.Label("Fréq. ↓ sous seuil", style=_lbl),
                        dcc.Dropdown(id='r-override-bfreq', clearable=True, placeholder="Auto (AIC)",
                                     options=[{'label': v, 'value': k} for k, v in FREQ_DIST_NAMES.items()],
                                     style={'marginBottom': '6px'}),
                        html.Label("Sév. ↑ au-dessus", style=_lbl),
                        dcc.Dropdown(id='r-override-asev', clearable=True, placeholder="Auto (AIC)",
                                     options=[{'label': v, 'value': k} for k, v in SEV_DIST_NAMES.items()],
                                     style={'marginBottom': '6px'}),
                        html.Label("Fréq. ↑ au-dessus", style=_lbl),
                        dcc.Dropdown(id='r-override-afreq', clearable=True, placeholder="Auto (AIC)",
                                     options=[{'label': v, 'value': k} for k, v in FREQ_DIST_NAMES.items()],
                                     style={'marginBottom': '4px'}),
                    ], style={
                        'backgroundColor': PALETTE['surface2'],
                        'border': f"1px solid {PALETTE['border']}",
                        'borderRadius': '6px', 'padding': '10px', 'marginBottom': '10px',
                    }),
                ], style={'marginBottom': '12px'}),

                html.Label("Nb. de simulations", style=_lbl),
                dcc.Input(id='r-nb-sims', type='number', value=5000, min=100, max=100000, step=500,
                          style={**_inp, 'marginBottom': '12px'}),

                btn_primary("⚙  Générer Simulations", id='r-btn-simuler'),
                html.Div(id='r-sim-status', style={
                    'color': PALETTE['success'], 'fontSize': '11px',
                    'marginTop': '8px', 'textAlign': 'center', 'lineHeight': '1.5',
                }),
            ], style={'marginBottom': '16px'}),

            # 2 — Configurer Traité
            card([
                section_title("2 — Configurer Traité", PALETTE['warning']),
                dcc.Dropdown(id='r-type-traite',
                             options=[
                                 {'label': 'Excess of Loss (XS)', 'value': 'XS'},
                                 {'label': 'Quote-Part (QP)', 'value': 'QP'},
                             ],
                             value='XS', style={'marginBottom': '10px'}),

                html.Div(id='r-container-qp', children=[
                    html.Label("Rétention %", style=_lbl),
                    dcc.Input(id='r-in-qp-taux', type='number', value=0.8, step=0.05,
                              style={**_inp, 'marginBottom': '8px'}),
                ], style={'display': 'none'}),

                html.Div(id='r-container-xs', children=[
                    html.Label("Priorité (€)", style=_lbl),
                    dcc.Input(id='r-in-xs-prio', type='number', value=100000,
                              style={**_inp, 'marginBottom': '8px'}),
                    html.Label("Portée (€)", style=_lbl),
                    dcc.Input(id='r-in-xs-portee', type='number', value=500000,
                              style={**_inp, 'marginBottom': '8px'}),
                ], style={'display': 'block'}),

                html.Div([
                    btn_secondary("+ Ajouter couche", id='r-btn-add-layer',
                                  style={'width': '48%', 'display': 'inline-block',
                                         'color': PALETTE['warning'],
                                         'border': f"1px solid {PALETTE['warning']}",
                                         'borderRadius': '6px', 'padding': '8px',
                                         'fontSize': '12px', 'fontWeight': '600'}),
                    btn_secondary("– Retirer", id='r-btn-remove-layer',
                                  style={'width': '48%', 'display': 'inline-block', 'float': 'right',
                                         'color': PALETTE['text_muted'],
                                         'border': f"1px solid {PALETTE['border']}",
                                         'borderRadius': '6px', 'padding': '8px',
                                         'fontSize': '12px', 'fontWeight': '600'}),
                ], style={'overflow': 'hidden', 'marginTop': '8px', 'marginBottom': '10px'}),

                html.Div(id='r-current-stack-display', style={
                    'backgroundColor': PALETTE['surface2'],
                    'border': f"1px solid {PALETTE['border']}",
                    'borderRadius': '6px', 'padding': '10px', 'fontSize': '12px',
                    'color': PALETTE['warning'], 'fontFamily': "'JetBrains Mono', monospace",
                    'minHeight': '36px', 'marginBottom': '12px',
                }),

                dcc.Input(id='r-prog-name', type='text', placeholder="Nom du programme (ex: A — 100k xs 500k)",
                          style={**_inp, 'marginBottom': '10px'}),
                btn_primary("✓  Valider & Tracer", id='r-btn-save-prog'),
            ], style={'marginBottom': '16px'}),

            # 3 — Filtres & Gestion
            card([
                section_title("3 — Zone cible & Gestion", PALETTE['danger']),
                html.Label("Filtrer par Écart-type (€)", style=_lbl),
                html.Div([
                    dcc.Input(id='r-std-min', type='number', placeholder="Min",
                              style={**_inp, 'width': '48%'}),
                    dcc.Input(id='r-std-max', type='number', placeholder="Max",
                              style={**_inp, 'width': '48%', 'float': 'right'}),
                ], style={'overflow': 'hidden', 'marginBottom': '14px'}),

                html.Label("Supprimer un programme", style=_lbl),
                html.Div([
                    html.Div(dcc.Dropdown(id='r-prog-to-delete', placeholder="Choisir…"),
                             style={'width': '63%', 'display': 'inline-block'}),
                    html.Button('Suppr.', id='r-btn-delete-prog', n_clicks=0, style={
                        'width': '33%', 'float': 'right', 'backgroundColor': 'transparent',
                        'color': PALETTE['danger'], 'border': f"1px solid {PALETTE['danger']}",
                        'borderRadius': '6px', 'padding': '8px', 'cursor': 'pointer',
                        'fontWeight': '700', 'fontSize': '12px',
                    }),
                ], style={'overflow': 'hidden', 'marginBottom': '10px'}),

                html.Button('✕  Tout vider (sauf Brut)', id='r-btn-reset', n_clicks=0, style={
                    'width': '100%', 'backgroundColor': 'transparent',
                    'color': PALETTE['text_muted'],
                    'border': f"1px solid {PALETTE['border']}",
                    'borderRadius': '6px', 'padding': '8px', 'cursor': 'pointer',
                    'fontWeight': '600', 'fontSize': '12px',
                }),
            ]),

        ], style={'width': '280px', 'flexShrink': '0'}),

        # ── COLONNE DROITE — onglets ────────────────────────────────────
        html.Div([
            dcc.Tabs(
                id='r-results-tabs',
                value='r-tab-frontier',
                colors={
                    "border": PALETTE['border'],
                    "primary": PALETTE['accent2'],
                    "background": PALETTE['surface'],
                },
                children=[

                    # TAB 1 — Frontière efficace
                    dcc.Tab(
                        label='Frontière efficace',
                        value='r-tab-frontier',
                        style=_tab_style,
                        selected_style=_tab_selected_style,
                        children=[
                            card([
                                dcc.Loading(
                                    dcc.Graph(id='r-frontiere-graph'),
                                    color=PALETTE['accent2'], type='dot',
                                ),
                                html.Div([
                                    html.Span("💡 Chaque point = un programme. Optimum = bas-gauche (faible ESP, faible σ).",
                                              style={'color': PALETTE['text_muted'], 'fontSize': '11px'}),
                                ], style={'marginTop': '8px'}),
                            ]),
                        ],
                    ),

                    # TAB 2 — Indicateurs
                    dcc.Tab(
                        label='Indicateurs',
                        value='r-tab-metrics',
                        style=_tab_style,
                        selected_style=_tab_selected_style,
                        children=[
                            card([
                                section_title("ESP · VaR 95% · VaR 99% · TVaR 99%", PALETTE['accent2']),
                                dcc.Loading(
                                    dcc.Graph(id='r-metrics-graph'),
                                    color=PALETTE['accent2'], type='dot',
                                ),
                                html.Div([
                                    html.Span("VaR 95% ≈ 1 an sur 20 · VaR 99% ≈ 1 an sur 100 · TVaR = moyenne des scénarios au-delà de la VaR 99%",
                                              style={'color': PALETTE['text_muted'], 'fontSize': '11px'}),
                                ], style={'marginTop': '8px'}),
                            ]),
                        ],
                    ),

                    # TAB 3 — OEP
                    dcc.Tab(
                        label='Courbe OEP',
                        value='r-tab-oep',
                        style=_tab_style,
                        selected_style={**_tab_selected_style, 'color': PALETTE['accent'], 'borderTop': f"2px solid {PALETTE['accent']}"},
                        children=[
                            card([
                                section_title("Courbe d'excédance de pertes (OEP)", PALETTE['accent']),
                                html.Div([
                                    html.Span(
                                        "Probabilité que la perte annuelle dépasse X€. "
                                        "Plus la courbe est basse, meilleure est la protection.",
                                        style={'color': PALETTE['text_muted'], 'fontSize': '11px'},
                                    ),
                                ], style={'marginBottom': '12px'}),
                                dcc.Loading(
                                    dcc.Graph(id='r-oep-graph'),
                                    color=PALETTE['accent'], type='dot',
                                ),
                            ]),
                        ],
                    ),

                    # TAB 4 — Retenu / Cédé
                    dcc.Tab(
                        label='Retenu / Cédé',
                        value='r-tab-retained',
                        style=_tab_style,
                        selected_style={**_tab_selected_style, 'color': PALETTE['warning'], 'borderTop': f"2px solid {PALETTE['warning']}"},
                        children=[
                            card([
                                section_title("Distribution Retenu vs Cédé", PALETTE['warning']),
                                html.Div([
                                    html.Label("Programme à analyser", style=_lbl),
                                    dcc.Dropdown(
                                        id='r-detail-prog-dropdown',
                                        placeholder="Sélectionner un programme…",
                                        style={'marginBottom': '14px'},
                                    ),
                                ]),
                                dcc.Loading(
                                    dcc.Graph(id='r-retained-ceded-graph'),
                                    color=PALETTE['warning'], type='dot',
                                ),
                                html.Div([
                                    html.Span("Histogramme des charges annuelles simulées. "
                                              "Vert = part retenue par la cédante · Orange = part cédée au réassureur.",
                                              style={'color': PALETTE['text_muted'], 'fontSize': '11px'}),
                                ], style={'marginTop': '8px'}),
                            ]),
                        ],
                    ),

                    # TAB 5 — Sensibilité heatmap
                    dcc.Tab(
                        label='Sensibilité XS',
                        value='r-tab-heatmap',
                        style=_tab_style,
                        selected_style={**_tab_selected_style, 'color': PALETTE['success'], 'borderTop': f"2px solid {PALETTE['success']}"},
                        children=[
                            card([
                                section_title("Heatmap Priorité × Portée", PALETTE['success']),
                                html.Div([
                                    html.Span(
                                        "Visualise l'ESP net retenu pour toutes les combinaisons "
                                        "(priorité, portée) XS. Vert foncé = charge minimale.",
                                        style={'color': PALETTE['text_muted'], 'fontSize': '11px'},
                                    ),
                                ], style={'marginBottom': '16px'}),

                                # Controls inline
                                html.Div([
                                    html.Div([
                                        html.Label("Priorité min (€)", style=_lbl),
                                        dcc.Input(id='r-heatmap-prio-min', type='number', value=50000,
                                                  style={**_inp}),
                                    ], style={'flex': '1', 'marginRight': '10px'}),
                                    html.Div([
                                        html.Label("Priorité max (€)", style=_lbl),
                                        dcc.Input(id='r-heatmap-prio-max', type='number', value=500000,
                                                  style={**_inp}),
                                    ], style={'flex': '1', 'marginRight': '10px'}),
                                    html.Div([
                                        html.Label("Portée min (€)", style=_lbl),
                                        dcc.Input(id='r-heatmap-portee-min', type='number', value=100000,
                                                  style={**_inp}),
                                    ], style={'flex': '1', 'marginRight': '10px'}),
                                    html.Div([
                                        html.Label("Portée max (€)", style=_lbl),
                                        dcc.Input(id='r-heatmap-portee-max', type='number', value=1000000,
                                                  style={**_inp}),
                                    ], style={'flex': '1', 'marginRight': '10px'}),
                                    html.Div([
                                        html.Label("Résolution", style=_lbl),
                                        dcc.Input(id='r-heatmap-steps', type='number', value=8,
                                                  min=4, max=20,
                                                  style={**_inp}),
                                    ], style={'flex': '0 0 90px'}),
                                ], style={'display': 'flex', 'marginBottom': '14px', 'gap': '4px'}),

                                btn_primary("Calculer Heatmap", id='r-btn-heatmap'),
                                html.Div(id='r-heatmap-status', style={
                                    'color': PALETTE['text_muted'], 'fontSize': '11px',
                                    'marginTop': '6px', 'textAlign': 'center',
                                }),
                                dcc.Loading(
                                    dcc.Graph(id='r-heatmap-graph'),
                                    color=PALETTE['success'], type='dot',
                                ),
                            ]),
                        ],
                    ),

                    # TAB 6 — Tous les programmes
                    dcc.Tab(
                        label='Programmes',
                        value='r-tab-all',
                        style=_tab_style,
                        selected_style=_tab_selected_style,
                        children=[
                            card([
                                section_title("Tous les programmes testés"),
                                dcc.Loading(
                                    html.Div(id='r-programs-table-container'),
                                    color=PALETTE['accent'], type='dot',
                                ),
                            ]),
                        ],
                    ),

                    # TAB 7 — Zone cible
                    dcc.Tab(
                        label='Zone cible',
                        value='r-tab-filtered',
                        style=_tab_style,
                        selected_style={**_tab_selected_style, 'color': PALETTE['success'],
                                        'borderTop': f"2px solid {PALETTE['success']}"},
                        children=[
                            card(
                                [
                                    section_title("Programmes dans la zone cible", PALETTE['success']),
                                    html.Div(id='r-filtered-programs-table-container'),
                                ],
                                style={'borderLeft': f"3px solid {PALETTE['success']}"},
                            ),
                        ],
                    ),

                ],
            ),
        ], style={'flex': '1', 'minWidth': '0'}),

    ], style={'display': 'flex', 'gap': '20px', 'padding': '24px', 'maxWidth': '1600px', 'margin': '0 auto'}),
])
