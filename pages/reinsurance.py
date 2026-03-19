from dash import dcc, html
from config import PALETTE, SEV_DIST_NAMES, FREQ_DIST_NAMES
from components.ui import card, section_title, btn_primary, btn_secondary

_tab_style = {
    'color': PALETTE['text_muted'],
    'backgroundColor': PALETTE['surface2'],
    'fontSize': '12px',
    'padding': '9px 16px',
    'fontWeight': '500',
    'letterSpacing': '0.3px',
}
_tab_selected_style = {
    'color': PALETTE['text'],
    'backgroundColor': PALETTE['surface'],
    'fontSize': '12px',
    'padding': '9px 16px',
    'fontWeight': '700',
    'borderTop': f"2px solid {PALETTE['accent2']}",
    'letterSpacing': '0.3px',
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
_lbl = {
    'color': PALETTE['text_muted'],
    'fontSize': '11px',
    'display': 'block',
    'marginBottom': '4px',
    'fontWeight': '500',
    'letterSpacing': '0.3px',
    'textTransform': 'uppercase',
}


PAGE_REASSURANCE = html.Div([

    # ══════════════════════════════════════════════════════════════
    # BANDE KPI — toujours visible, pleine largeur
    # ══════════════════════════════════════════════════════════════
    html.Div(
        id='r-summary-kpis',
        style={
            'padding': '20px 24px 4px',
            'maxWidth': '1600px',
            'margin': '0 auto',
        },
    ),

    # ══════════════════════════════════════════════════════════════
    # LAYOUT DEUX COLONNES
    # ══════════════════════════════════════════════════════════════
    html.Div([

        # ── COLONNE GAUCHE ───────────────────────────────────────
        html.Div([

            # 1 — Simulation
            card([
                section_title("1 — Simulation", PALETTE['accent2']),
                html.Div(id='r-model-status-banner'),

                html.Details([
                    html.Summary("⚙  Overrides distributions", style={
                        'color': PALETTE['text_muted'], 'fontSize': '11px',
                        'cursor': 'pointer', 'marginBottom': '8px',
                        'letterSpacing': '0.5px', 'textTransform': 'uppercase',
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
                                     options=[{'label': v, 'value': k} for k, v in FREQ_DIST_NAMES.items()]),
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
                    'marginTop': '8px', 'textAlign': 'center', 'lineHeight': '1.6',
                }),
            ], style={'marginBottom': '14px'}),

            # 2 — Configurer Traité
            card([
                section_title("2 — Configurer Traité", PALETTE['warning']),
                dcc.Dropdown(
                    id='r-type-traite',
                    options=[
                        {'label': 'Excess of Loss (XS)', 'value': 'XS'},
                        {'label': 'Quote-Part (QP)', 'value': 'QP'},
                    ],
                    value='XS',
                    style={'marginBottom': '10px'},
                ),

                html.Div(id='r-container-qp', children=[
                    html.Label("Rétention cédante (%)", style=_lbl),
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
                    html.Button("+ Couche", id='r-btn-add-layer', n_clicks=0, style={
                        'width': '48%', 'backgroundColor': 'transparent',
                        'color': PALETTE['warning'], 'border': f"1px solid {PALETTE['warning']}",
                        'borderRadius': '6px', 'padding': '8px', 'cursor': 'pointer',
                        'fontWeight': '700', 'fontSize': '12px',
                    }),
                    html.Button("– Retirer", id='r-btn-remove-layer', n_clicks=0, style={
                        'width': '48%', 'float': 'right', 'backgroundColor': 'transparent',
                        'color': PALETTE['text_muted'], 'border': f"1px solid {PALETTE['border']}",
                        'borderRadius': '6px', 'padding': '8px', 'cursor': 'pointer',
                        'fontWeight': '600', 'fontSize': '12px',
                    }),
                ], style={'overflow': 'hidden', 'marginBottom': '10px'}),

                # Aperçu du stack courant
                html.Div(id='r-current-stack-display', style={
                    'backgroundColor': PALETTE['surface2'],
                    'border': f"1px solid {PALETTE['warning']}44",
                    'borderLeft': f"3px solid {PALETTE['warning']}",
                    'borderRadius': '6px', 'padding': '10px', 'fontSize': '12px',
                    'color': PALETTE['warning'], 'fontFamily': "'JetBrains Mono', monospace",
                    'minHeight': '36px', 'marginBottom': '12px', 'lineHeight': '1.6',
                }),

                html.Label("Nom du programme", style=_lbl),
                dcc.Input(id='r-prog-name', type='text', placeholder="ex: A — 100k xs 500k",
                          style={**_inp, 'marginBottom': '10px'}),
                btn_primary("✓  Valider & Tracer", id='r-btn-save-prog'),
            ], style={'marginBottom': '14px'}),

            # 3 — Zone cible & Gestion
            card([
                section_title("3 — Zone cible & Gestion", PALETTE['danger']),

                html.Label("Filtrer par Écart-type (σ)", style=_lbl),
                html.Div([
                    dcc.Input(id='r-std-min', type='number', placeholder="Min σ",
                              style={**_inp, 'width': '48%'}),
                    dcc.Input(id='r-std-max', type='number', placeholder="Max σ",
                              style={**_inp, 'width': '48%', 'float': 'right'}),
                ], style={'overflow': 'hidden', 'marginBottom': '16px'}),

                html.Label("Supprimer un programme", style=_lbl),
                html.Div([
                    html.Div(
                        dcc.Dropdown(id='r-prog-to-delete', placeholder="Choisir…"),
                        style={'width': '63%', 'display': 'inline-block'},
                    ),
                    html.Button('Suppr.', id='r-btn-delete-prog', n_clicks=0, style={
                        'width': '33%', 'float': 'right', 'backgroundColor': 'transparent',
                        'color': PALETTE['danger'], 'border': f"1px solid {PALETTE['danger']}",
                        'borderRadius': '6px', 'padding': '8px', 'cursor': 'pointer',
                        'fontWeight': '700', 'fontSize': '12px',
                    }),
                ], style={'overflow': 'hidden', 'marginBottom': '10px'}),

                html.Button('✕  Tout vider (sauf Brut)', id='r-btn-reset', n_clicks=0, style={
                    'width': '100%', 'backgroundColor': 'transparent',
                    'color': PALETTE['text_muted'], 'border': f"1px solid {PALETTE['border']}",
                    'borderRadius': '6px', 'padding': '8px', 'cursor': 'pointer',
                    'fontWeight': '600', 'fontSize': '12px',
                }),
            ]),

        ], style={'width': '272px', 'flexShrink': '0'}),

        # ── COLONNE DROITE — onglets ─────────────────────────────
        html.Div([
            dcc.Tabs(
                id='r-results-tabs',
                value='r-tab-metrics',
                colors={
                    "border": PALETTE['border'],
                    "primary": PALETTE['accent2'],
                    "background": PALETTE['surface2'],
                },
                children=[

                    # TAB 1 — Indicateurs
                    dcc.Tab(
                        label='Indicateurs',
                        value='r-tab-metrics',
                        style=_tab_style,
                        selected_style={**_tab_selected_style,
                                        'borderTop': f"2px solid {PALETTE['accent2']}"},
                        children=[
                            card([
                                # Légende métrique
                                html.Div([
                                    html.Span("% de réduction par rapport à la position BRUT (sans réassurance).",
                                              style={'color': PALETTE['text_muted'], 'fontSize': '12px'}),
                                    html.Span("  ▼ Plus la barre est longue, meilleure est la protection.",
                                              style={'color': PALETTE['success'], 'fontSize': '12px', 'fontWeight': '600'}),
                                ], style={'marginBottom': '16px',
                                          'backgroundColor': f"{PALETTE['surface2']}",
                                          'border': f"1px solid {PALETTE['border']}",
                                          'borderRadius': '6px', 'padding': '10px 14px'}),
                                dcc.Loading(
                                    dcc.Graph(id='r-metrics-graph', config={'displayModeBar': False}),
                                    color=PALETTE['accent2'], type='dot',
                                ),
                            ]),
                        ],
                    ),

                    # TAB 2 — Frontière efficace
                    dcc.Tab(
                        label='Frontière efficace',
                        value='r-tab-frontier',
                        style=_tab_style,
                        selected_style={**_tab_selected_style,
                                        'borderTop': f"2px solid {PALETTE['accent']}"},
                        children=[
                            card([
                                html.Div([
                                    html.Span(
                                        "Chaque point = un programme. L'optimum se trouve en bas à gauche "
                                        "(charge faible ET variabilité faible). Survolez un point pour voir ses indicateurs.",
                                        style={'color': PALETTE['text_muted'], 'fontSize': '12px'},
                                    ),
                                ], style={'marginBottom': '12px',
                                          'backgroundColor': PALETTE['surface2'],
                                          'border': f"1px solid {PALETTE['border']}",
                                          'borderRadius': '6px', 'padding': '10px 14px'}),
                                dcc.Loading(
                                    dcc.Graph(id='r-frontiere-graph'),
                                    color=PALETTE['accent'], type='dot',
                                ),
                            ]),
                        ],
                    ),

                    # TAB 3 — OEP
                    dcc.Tab(
                        label='Courbe OEP',
                        value='r-tab-oep',
                        style=_tab_style,
                        selected_style={**_tab_selected_style,
                                        'color': '#A78BFA',
                                        'borderTop': "2px solid #A78BFA"},
                        children=[
                            card([
                                html.Div([
                                    html.Span(
                                        "Probabilité de dépasser X€ de perte dans l'année. "
                                        "Les lignes pointillées marquent les seuils 1/20 ans et 1/100 ans.",
                                        style={'color': PALETTE['text_muted'], 'fontSize': '12px'},
                                    ),
                                ], style={'marginBottom': '12px',
                                          'backgroundColor': PALETTE['surface2'],
                                          'border': f"1px solid {PALETTE['border']}",
                                          'borderRadius': '6px', 'padding': '10px 14px'}),
                                dcc.Loading(
                                    dcc.Graph(id='r-oep-graph'),
                                    color='#A78BFA', type='dot',
                                ),
                                # Tableau des valeurs aux points de référence
                                html.Div(id='r-oep-ref-table', style={'marginTop': '16px'}),
                            ]),
                        ],
                    ),

                    # TAB 4 — Retenu / Cédé
                    dcc.Tab(
                        label='Retenu / Cédé',
                        value='r-tab-retained',
                        style=_tab_style,
                        selected_style={**_tab_selected_style,
                                        'color': PALETTE['warning'],
                                        'borderTop': f"2px solid {PALETTE['warning']}"},
                        children=[
                            card([
                                html.Div([
                                    html.Label("Sélectionner un programme", style={**_lbl, 'marginBottom': '6px'}),
                                    dcc.Dropdown(
                                        id='r-detail-prog-dropdown',
                                        placeholder="Sélectionner un programme…",
                                    ),
                                ], style={'marginBottom': '16px'}),
                                # KPI strip du programme sélectionné
                                html.Div(id='r-retained-kpis', style={'marginBottom': '16px'}),
                                dcc.Loading(
                                    dcc.Graph(id='r-retained-ceded-graph'),
                                    color=PALETTE['warning'], type='dot',
                                ),
                            ]),
                        ],
                    ),

                    # TAB 5 — Sensibilité XS
                    dcc.Tab(
                        label='Sensibilité XS',
                        value='r-tab-heatmap',
                        style=_tab_style,
                        selected_style={**_tab_selected_style,
                                        'color': PALETTE['success'],
                                        'borderTop': f"2px solid {PALETTE['success']}"},
                        children=[
                            card([
                                html.Div([
                                    html.Span(
                                        "ESP net retenu pour chaque combinaison (Priorité, Portée) XS. "
                                        "Vert foncé = charge minimale = meilleure protection.",
                                        style={'color': PALETTE['text_muted'], 'fontSize': '12px'},
                                    ),
                                ], style={'marginBottom': '16px',
                                          'backgroundColor': PALETTE['surface2'],
                                          'border': f"1px solid {PALETTE['border']}",
                                          'borderRadius': '6px', 'padding': '10px 14px'}),

                                html.Div([
                                    html.Div([
                                        html.Label("Priorité min (€)", style=_lbl),
                                        dcc.Input(id='r-heatmap-prio-min', type='number', value=50000,
                                                  style=_inp),
                                    ], style={'flex': '1'}),
                                    html.Div([
                                        html.Label("Priorité max (€)", style=_lbl),
                                        dcc.Input(id='r-heatmap-prio-max', type='number', value=500000,
                                                  style=_inp),
                                    ], style={'flex': '1'}),
                                    html.Div([
                                        html.Label("Portée min (€)", style=_lbl),
                                        dcc.Input(id='r-heatmap-portee-min', type='number', value=100000,
                                                  style=_inp),
                                    ], style={'flex': '1'}),
                                    html.Div([
                                        html.Label("Portée max (€)", style=_lbl),
                                        dcc.Input(id='r-heatmap-portee-max', type='number', value=1000000,
                                                  style=_inp),
                                    ], style={'flex': '1'}),
                                    html.Div([
                                        html.Label("Résolution", style=_lbl),
                                        dcc.Input(id='r-heatmap-steps', type='number', value=8, min=4, max=20,
                                                  style=_inp),
                                    ], style={'flex': '0 0 100px'}),
                                ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '14px'}),

                                btn_primary("Calculer la Heatmap", id='r-btn-heatmap'),
                                html.Div(id='r-heatmap-status', style={
                                    'color': PALETTE['success'], 'fontSize': '11px',
                                    'marginTop': '8px', 'textAlign': 'center',
                                }),
                                dcc.Loading(
                                    dcc.Graph(id='r-heatmap-graph'),
                                    color=PALETTE['success'], type='dot',
                                ),
                            ]),
                        ],
                    ),

                    # TAB 6 — Tous les programmes (tableau)
                    dcc.Tab(
                        label='Programmes',
                        value='r-tab-all',
                        style=_tab_style,
                        selected_style=_tab_selected_style,
                        children=[
                            card([
                                section_title("Comparatif de tous les programmes"),
                                html.Div([
                                    html.Span("▼ vert = réduction vs Brut · ▲ rouge = dégradation",
                                              style={'color': PALETTE['text_muted'], 'fontSize': '11px'}),
                                ], style={'marginBottom': '14px'}),
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
                        selected_style={**_tab_selected_style,
                                        'color': PALETTE['success'],
                                        'borderTop': f"2px solid {PALETTE['success']}"},
                        children=[
                            card([
                                section_title("Programmes dans la zone cible (σ filtré)", PALETTE['success']),
                                html.Div(id='r-filtered-programs-table-container'),
                            ], style={'borderLeft': f"3px solid {PALETTE['success']}"}),
                        ],
                    ),

                ],
            ),
        ], style={'flex': '1', 'minWidth': '0'}),

    ], style={
        'display': 'flex',
        'gap': '20px',
        'padding': '8px 24px 24px',
        'maxWidth': '1600px',
        'margin': '0 auto',
    }),
])
