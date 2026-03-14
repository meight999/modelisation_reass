from dash import dcc, html
from config import PALETTE
from components.ui import card, section_title, btn_primary, _LABEL, _INPUT, _field_label

PAGE_MODELISATION = html.Div([
    html.Div([
        # COLONNE GAUCHE - Configuration
        html.Div([
            card([
                section_title("Configuration"),

                # Upload zone
                html.Div("Fichier de données", style=_LABEL),
                dcc.Upload(id='upload-data', children=html.Div([
                    html.Div("↑", style={'fontSize': '24px', 'color': PALETTE['accent'], 'lineHeight': '1'}),
                    html.Div("Glisser-déposer ou cliquer", style={'fontSize': '12px', 'color': PALETTE['text_muted'], 'marginTop': '4px'}),
                    html.Div("Excel (.xlsx) ou CSV", style={'fontSize': '11px', 'color': PALETTE['border'], 'marginTop': '2px'}),
                ], style={'textAlign': 'center', 'padding': '4px 0'}), style={
                    'border': f"2px dashed {PALETTE['border']}", 'borderRadius': '8px',
                    'padding': '18px 12px', 'cursor': 'pointer', 'marginBottom': '6px',
                    'backgroundColor': PALETTE['surface2'],
                    'transition': 'border-color 0.2s ease',
                }),
                html.Div(id='upload-status', style={
                    'color': PALETTE['success'], 'fontSize': '12px',
                    'marginBottom': '20px', 'minHeight': '16px',
                }),

                # Séparateur
                html.Hr(style={'border': 'none', 'borderTop': f"1px solid {PALETTE['border']}", 'margin': '0 0 16px 0'}),

                _field_label("Colonne des montants"),
                dcc.Dropdown(id='column-name', options=[], placeholder='Sélectionner une colonne…',
                             style={'marginBottom': '16px'}, className='dark-dropdown'),

                # Champs optionnels groupés
                html.Div([
                    html.Div("Analyse de fréquence", style={
                        'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '1.5px',
                        'color': PALETTE['text_muted'], 'textTransform': 'uppercase',
                        'marginBottom': '10px',
                    }),
                    _field_label("Colonne de date", optional=True),
                    dcc.Dropdown(id='date-column', options=[], placeholder='Aucune',
                                 style={'marginBottom': '12px'}),
                    _field_label("Année de départ", optional=True),
                    dcc.Input(id='start-date-input', type='number', placeholder='ex : 2015',
                              min=1900, max=2100, style={**_INPUT, 'marginBottom': '4px'}),
                ], style={
                    'backgroundColor': PALETTE['surface2'], 'borderRadius': '8px',
                    'border': f"1px solid {PALETTE['border']}", 'padding': '14px',
                    'marginBottom': '16px',
                }),

                _field_label("Seuil de séparation (€)"),
                html.Div("Sinistres en-dessous = attritionnels, au-dessus = graves",
                         style={'fontSize': '11px', 'color': PALETTE['text_muted'], 'marginBottom': '6px'}),
                dcc.Input(id='threshold', type='number', value=30000,
                          style={**_INPUT, 'marginBottom': '20px'}),

                btn_primary("▶  Lancer l'analyse", id='analyze-button'),
            ], style={'marginBottom': '16px'}),

            html.Div(id='data-info-card'),
        ], style={'width': '290px', 'flexShrink': '0'}),

        # COLONNE DROITE - Résultats
        html.Div([
            # Aperçu distribution + seuil (visible après Analyser)
            html.Div(id='threshold-preview-container'),

            # Navigation principale : SOUS LE SEUIL / AU-DESSUS DU SEUIL
            card([
                dcc.Tabs(id='segment-tabs', value='segment-below', children=[

                    # ── SOUS LE SEUIL ────────────────────────────────────────
                    dcc.Tab(label='▼  SOUS LE SEUIL', value='segment-below',
                            style={'color': PALETTE['text_muted'], 'backgroundColor': PALETTE['surface'],
                                   'padding': '12px 28px', 'borderColor': PALETTE['border']},
                            selected_style={'color': PALETTE['success'], 'fontWeight': '700',
                                           'backgroundColor': PALETTE['surface2'],
                                           'borderTop': f"3px solid {PALETTE['success']}",
                                           'padding': '12px 28px', 'borderColor': PALETTE['border']},
                            children=[
                                dcc.Tabs(id='below-type-tabs', value='below-sev',
                                         style={'marginTop': '18px'},
                                         colors={"border": PALETTE['border'], "primary": PALETTE['success'],
                                                 "background": PALETTE['surface2']},
                                         children=[
                                    dcc.Tab(label='📊  Sévérité', value='below-sev',
                                            style={'color': PALETTE['text_muted'], 'fontSize': '13px',
                                                   'backgroundColor': PALETTE['surface2'], 'padding': '8px 18px'},
                                            selected_style={'color': PALETTE['success'], 'fontWeight': '700',
                                                           'fontSize': '13px', 'backgroundColor': PALETTE['surface'],
                                                           'borderTop': f"2px solid {PALETTE['success']}",
                                                           'padding': '8px 18px'},
                                            children=[html.Div(style={'paddingTop': '14px'}, children=[
                                                dcc.Tabs(id='below-tabs', value='below-details', children=[
                                                    dcc.Tab(label='Paramètres',      value='below-details'),
                                                    dcc.Tab(label='ECDF & Critères', value='below-ecdf-criteria'),
                                                    dcc.Tab(label='QQ & Quantiles',  value='below-qq-quantiles'),
                                                    dcc.Tab(label='Histogramme',     value='below-histogram'),
                                                ], colors={"border": PALETTE['border'], "primary": PALETTE['accent'],
                                                           "background": PALETTE['surface2']}),
                                                dcc.Loading(
                                                    html.Div(id='below-content', style={'minHeight': '320px', 'paddingTop': '20px'}),
                                                    color=PALETTE['accent'], type='dot'),
                                            ])]),
                                    dcc.Tab(label='📈  Fréquence', value='below-freq',
                                            style={'color': PALETTE['text_muted'], 'fontSize': '13px',
                                                   'backgroundColor': PALETTE['surface2'], 'padding': '8px 18px'},
                                            selected_style={'color': PALETTE['below_freq'], 'fontWeight': '700',
                                                           'fontSize': '13px', 'backgroundColor': PALETTE['surface'],
                                                           'borderTop': f"2px solid {PALETTE['below_freq']}",
                                                           'padding': '8px 18px'},
                                            children=[html.Div(style={'paddingTop': '14px'}, children=[
                                                dcc.Tabs(id='below-freq-tabs', value='below-freq-details', children=[
                                                    dcc.Tab(label='Paramètres',       value='below-freq-details'),
                                                    dcc.Tab(label='CDF & Critères',   value='below-freq-cmf'),
                                                    dcc.Tab(label='Série temporelle', value='below-freq-ts'),
                                                ], colors={"border": PALETTE['border'], "primary": PALETTE['below_freq'],
                                                           "background": PALETTE['surface2']}),
                                                dcc.Loading(
                                                    html.Div(id='below-freq-content', style={'minHeight': '320px', 'paddingTop': '20px'}),
                                                    color=PALETTE['below_freq'], type='dot'),
                                            ])]),
                                ]),
                            ]),

                    # ── AU-DESSUS DU SEUIL ────────────────────────────────────
                    dcc.Tab(label='▲  AU-DESSUS DU SEUIL', value='segment-above',
                            style={'color': PALETTE['text_muted'], 'backgroundColor': PALETTE['surface'],
                                   'padding': '12px 28px', 'borderColor': PALETTE['border']},
                            selected_style={'color': PALETTE['danger'], 'fontWeight': '700',
                                           'backgroundColor': PALETTE['surface2'],
                                           'borderTop': f"3px solid {PALETTE['danger']}",
                                           'padding': '12px 28px', 'borderColor': PALETTE['border']},
                            children=[
                                dcc.Tabs(id='above-type-tabs', value='above-sev',
                                         style={'marginTop': '18px'},
                                         colors={"border": PALETTE['border'], "primary": PALETTE['danger'],
                                                 "background": PALETTE['surface2']},
                                         children=[
                                    dcc.Tab(label='📊  Sévérité', value='above-sev',
                                            style={'color': PALETTE['text_muted'], 'fontSize': '13px',
                                                   'backgroundColor': PALETTE['surface2'], 'padding': '8px 18px'},
                                            selected_style={'color': PALETTE['danger'], 'fontWeight': '700',
                                                           'fontSize': '13px', 'backgroundColor': PALETTE['surface'],
                                                           'borderTop': f"2px solid {PALETTE['danger']}",
                                                           'padding': '8px 18px'},
                                            children=[html.Div(style={'paddingTop': '14px'}, children=[
                                                dcc.Tabs(id='above-tabs', value='above-details', children=[
                                                    dcc.Tab(label='Paramètres',      value='above-details'),
                                                    dcc.Tab(label='ECDF & Critères', value='above-ecdf-criteria'),
                                                    dcc.Tab(label='QQ & Quantiles',  value='above-qq-quantiles'),
                                                    dcc.Tab(label='Histogramme',     value='above-histogram'),
                                                ], colors={"border": PALETTE['border'], "primary": PALETTE['danger'],
                                                           "background": PALETTE['surface2']}),
                                                dcc.Loading(
                                                    html.Div(id='above-content', style={'minHeight': '320px', 'paddingTop': '20px'}),
                                                    color=PALETTE['danger'], type='dot'),
                                            ])]),
                                    dcc.Tab(label='📈  Fréquence', value='above-freq',
                                            style={'color': PALETTE['text_muted'], 'fontSize': '13px',
                                                   'backgroundColor': PALETTE['surface2'], 'padding': '8px 18px'},
                                            selected_style={'color': PALETTE['above_freq'], 'fontWeight': '700',
                                                           'fontSize': '13px', 'backgroundColor': PALETTE['surface'],
                                                           'borderTop': f"2px solid {PALETTE['above_freq']}",
                                                           'padding': '8px 18px'},
                                            children=[html.Div(style={'paddingTop': '14px'}, children=[
                                                dcc.Tabs(id='above-freq-tabs', value='above-freq-details', children=[
                                                    dcc.Tab(label='Paramètres',       value='above-freq-details'),
                                                    dcc.Tab(label='CDF & Critères',   value='above-freq-cmf'),
                                                    dcc.Tab(label='Série temporelle', value='above-freq-ts'),
                                                ], colors={"border": PALETTE['border'], "primary": PALETTE['above_freq'],
                                                           "background": PALETTE['surface2']}),
                                                dcc.Loading(
                                                    html.Div(id='above-freq-content', style={'minHeight': '320px', 'paddingTop': '20px'}),
                                                    color=PALETTE['above_freq'], type='dot'),
                                            ])]),
                                ]),
                            ]),

                ], colors={"border": PALETTE['border'], "primary": PALETTE['accent'],
                           "background": PALETTE['surface']}),
            ]),
        ], style={'flex': '1', 'minWidth': '0'}),

    ], style={'display': 'flex', 'gap': '20px', 'padding': '24px', 'maxWidth': '1600px', 'margin': '0 auto'}),

    # (stores au niveau du layout racine)
])
