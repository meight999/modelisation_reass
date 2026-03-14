from dash import dcc, html
from config import PALETTE, SEV_DIST_NAMES, FREQ_DIST_NAMES
from components.ui import card, section_title, btn_primary, btn_secondary

_tab_style = {
    'color': PALETTE['text_muted'],
    'backgroundColor': PALETTE['surface2'],
    'fontSize': '13px',
    'padding': '10px 18px',
    'fontWeight': '500',
}
_tab_selected_style = {
    'color': PALETTE['accent2'],
    'backgroundColor': PALETTE['surface'],
    'fontSize': '13px',
    'padding': '10px 18px',
    'fontWeight': '700',
    'borderTop': f"2px solid {PALETTE['accent2']}",
}

PAGE_REASSURANCE = html.Div([
    html.Div([
        # COLONNE GAUCHE
        html.Div([
            card([
                section_title("1 — Modèle de simulation", PALETTE['accent2']),

                # Bandeau d'info / lois sélectionnées automatiquement
                html.Div(id='r-model-status-banner'),

                # Overrides manuels (optionnels)
                html.Details([
                    html.Summary("⚙  Overrides distributions (optionnel)", style={
                        'color': PALETTE['text_muted'], 'fontSize': '12px', 'cursor': 'pointer',
                        'marginBottom': '8px', 'letterSpacing': '0.5px',
                    }),
                    html.Div([
                        html.Label("Sév. ↓ sous seuil", style={'color': PALETTE['text_muted'], 'fontSize': '11px'}),
                        dcc.Dropdown(id='r-override-bsev', clearable=True, placeholder="Auto (AIC)",
                                     options=[{'label': v, 'value': k} for k, v in SEV_DIST_NAMES.items()],
                                     style={'marginBottom': '6px'}),
                        html.Label("Fréq. ↓ sous seuil", style={'color': PALETTE['text_muted'], 'fontSize': '11px'}),
                        dcc.Dropdown(id='r-override-bfreq', clearable=True, placeholder="Auto (AIC)",
                                     options=[{'label': v, 'value': k} for k, v in FREQ_DIST_NAMES.items()],
                                     style={'marginBottom': '6px'}),
                        html.Label("Sév. ↑ au-dessus", style={'color': PALETTE['text_muted'], 'fontSize': '11px'}),
                        dcc.Dropdown(id='r-override-asev', clearable=True, placeholder="Auto (AIC)",
                                     options=[{'label': v, 'value': k} for k, v in SEV_DIST_NAMES.items()],
                                     style={'marginBottom': '6px'}),
                        html.Label("Fréq. ↑ au-dessus", style={'color': PALETTE['text_muted'], 'fontSize': '11px'}),
                        dcc.Dropdown(id='r-override-afreq', clearable=True, placeholder="Auto (AIC)",
                                     options=[{'label': v, 'value': k} for k, v in FREQ_DIST_NAMES.items()],
                                     style={'marginBottom': '4px'}),
                    ], style={
                        'backgroundColor': PALETTE['surface2'], 'border': f"1px solid {PALETTE['border']}",
                        'borderRadius': '6px', 'padding': '10px', 'marginBottom': '10px',
                    }),
                ], style={'marginBottom': '12px'}),

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

        # COLONNE DROITE — résultats en onglets
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
                    dcc.Tab(
                        label='Frontière efficace',
                        value='r-tab-frontier',
                        style=_tab_style,
                        selected_style=_tab_selected_style,
                        children=[
                            card([dcc.Graph(id='r-frontiere-graph')]),
                        ],
                    ),
                    dcc.Tab(
                        label='Indicateurs',
                        value='r-tab-metrics',
                        style=_tab_style,
                        selected_style=_tab_selected_style,
                        children=[
                            card([
                                section_title("Comparaison ESP / VaR 95% / VaR 99% / TVaR 99%", PALETTE['accent2']),
                                dcc.Loading(dcc.Graph(id='r-metrics-graph'), color=PALETTE['accent2'], type='dot'),
                            ]),
                        ],
                    ),
                    dcc.Tab(
                        label='Programmes',
                        value='r-tab-all',
                        style=_tab_style,
                        selected_style=_tab_selected_style,
                        children=[
                            card([
                                section_title("Tous les programmes testés"),
                                dcc.Loading(html.Div(id='r-programs-table-container'), color=PALETTE['accent'], type='dot'),
                            ]),
                        ],
                    ),
                    dcc.Tab(
                        label='Zone cible',
                        value='r-tab-filtered',
                        style=_tab_style,
                        selected_style={**_tab_selected_style, 'color': PALETTE['success'], 'borderTop': f"2px solid {PALETTE['success']}"},
                        children=[
                            card(
                                [
                                    section_title("Zone cible", PALETTE['success']),
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

    # (stores au niveau du layout racine)
])
