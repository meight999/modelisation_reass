from dash import dcc, html
from config import PALETTE
from components.ui import card, section_title

_lbl = {
    'color': PALETTE['text_muted'],
    'fontSize': '11px',
    'display': 'block',
    'marginBottom': '4px',
    'fontWeight': '600',
    'letterSpacing': '0.5px',
    'textTransform': 'uppercase',
}
_inp = {
    'width': '100%',
    'backgroundColor': '#1A2535',
    'border': f"1px solid {PALETTE['border']}",
    'color': PALETTE['text'],
    'borderRadius': '6px',
    'padding': '8px 12px',
    'fontFamily': "'JetBrains Mono', monospace",
    'fontSize': '13px',
    'marginBottom': '10px',
}
_tab_style = {
    'color': PALETTE['text_muted'],
    'backgroundColor': PALETTE['surface2'],
    'fontSize': '13px',
    'padding': '12px 24px',
    'fontWeight': '500',
    'letterSpacing': '0.3px',
}
_tab_sel_s1 = {
    'color': PALETTE['accent2'],
    'backgroundColor': PALETTE['surface'],
    'fontSize': '13px',
    'padding': '12px 24px',
    'fontWeight': '700',
    'borderTop': f"2px solid {PALETTE['accent2']}",
}
_tab_sel_s2 = {
    'color': PALETTE['success'],
    'backgroundColor': PALETTE['surface'],
    'fontSize': '13px',
    'padding': '12px 24px',
    'fontWeight': '700',
    'borderTop': f"2px solid {PALETTE['success']}",
}

_info_box = {
    'backgroundColor': '#101E30',
    'border': f"1px solid {PALETTE['border']}",
    'borderRadius': '8px',
    'padding': '12px 16px',
    'fontSize': '12px',
    'color': PALETTE['text_muted'],
    'lineHeight': '1.7',
    'marginBottom': '16px',
}

_why_box_s1 = {
    'backgroundColor': '#0D1E33',
    'border': f"1px solid {PALETTE['accent2']}44",
    'borderLeft': f"3px solid {PALETTE['accent2']}",
    'borderRadius': '8px',
    'padding': '14px 18px',
    'fontSize': '13px',
    'color': PALETTE['text'],
    'lineHeight': '1.7',
    'marginTop': '16px',
}

_why_box_s2 = {
    'backgroundColor': '#0D2218',
    'border': f"1px solid {PALETTE['success']}44",
    'borderLeft': f"3px solid {PALETTE['success']}",
    'borderRadius': '8px',
    'padding': '14px 18px',
    'fontSize': '13px',
    'color': PALETTE['text'],
    'lineHeight': '1.7',
    'marginTop': '16px',
}

_slider_marks_theta = {0: '0%', 0.1: '10%', 0.2: '20%', 0.3: '30%', 0.5: '50%'}
_slider_marks_er = {0.05: '5%', 0.1: '10%', 0.2: '20%', 0.35: '35%', 0.5: '50%'}
_slider_marks_q = {0.05: '5%', 0.1: '10%', 0.2: '20%', 0.4: '40%', 0.6: '60%'}
_slider_marks_av = {0: '0', 0.05: '0.05', 0.1: '0.1', 0.2: '0.2', 0.5: '0.5'}


def _dist_params_block(prefix, accent):
    """Distribution selection + conditional parameter inputs."""
    return html.Div([
        html.Label("Distribution de S", style=_lbl),
        dcc.Dropdown(
            id=f'{prefix}-dist',
            options=[
                {'label': 'Exponentielle', 'value': 'exponential'},
                {'label': 'Lognormale', 'value': 'lognormal'},
                {'label': 'Gamma', 'value': 'gamma'},
            ],
            value='lognormal',
            clearable=False,
            style={'marginBottom': '12px'},
        ),

        # Exponential params
        html.Div(id=f'{prefix}-params-exp', style={'display': 'none'}, children=[
            html.Label("Moyenne E[S]", style=_lbl),
            dcc.Input(id=f'{prefix}-exp-mean', type='number', value=100000,
                      min=1000, step=5000, style=_inp),
        ]),

        # Lognormal params
        html.Div(id=f'{prefix}-params-ln', style={'display': 'block'}, children=[
            html.Label("μ (log-moyenne)", style=_lbl),
            dcc.Input(id=f'{prefix}-ln-mu', type='number', value=11.0,
                      step=0.1, style=_inp),
            html.Label("σ (log-écart-type)", style=_lbl),
            dcc.Input(id=f'{prefix}-ln-sigma', type='number', value=0.8,
                      min=0.01, max=3.0, step=0.05, style=_inp),
        ]),

        # Gamma params
        html.Div(id=f'{prefix}-params-gam', style={'display': 'none'}, children=[
            html.Label("Shape α", style=_lbl),
            dcc.Input(id=f'{prefix}-gam-alpha', type='number', value=3.0,
                      min=0.1, step=0.1, style=_inp),
            html.Label("Scale β", style=_lbl),
            dcc.Input(id=f'{prefix}-gam-beta', type='number', value=33000,
                      min=100, step=1000, style=_inp),
        ]),

        # Implied moments display
        html.Div(id=f'{prefix}-dist-info', style={
            'backgroundColor': '#101E30',
            'border': f"1px solid {PALETTE['border']}",
            'borderRadius': '6px',
            'padding': '8px 12px',
            'fontSize': '11px',
            'color': accent,
            'fontFamily': "'JetBrains Mono', monospace",
            'marginBottom': '16px',
            'lineHeight': '1.6',
        }),
    ])


def _params_panel_s1():
    return html.Div([
        # Context
        html.Div([
            html.Div("Scénario 1 — Prime valeur espérée", style={
                'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '1px',
                'textTransform': 'uppercase', 'color': PALETTE['accent2'],
                'marginBottom': '6px',
            }),
            html.P(
                "P_R = (1+θ)·E[R]. À E[R] fixé, le Stop-Loss minimise Var(D). "
                "Objectif : choisir b tel que E[(S−b)₊] = E[R].",
                style={'fontSize': '12px', 'color': PALETTE['text_muted'],
                       'lineHeight': '1.6', 'margin': 0},
            ),
        ], style=_info_box),

        section_title("Distribution de S", PALETTE['accent2']),
        _dist_params_block('s1', PALETTE['accent2']),

        html.Div(style={'height': '1px', 'backgroundColor': PALETTE['border'],
                        'marginBottom': '16px'}),
        section_title("Paramètres de prime", PALETTE['accent2']),

        html.Label("Chargement θ", style=_lbl),
        html.Div([
            dcc.Slider(id='s1-theta', min=0, max=0.5, step=0.01, value=0.2,
                       marks=_slider_marks_theta,
                       tooltip={'placement': 'bottom', 'always_visible': False}),
        ], style={'marginBottom': '24px', 'paddingBottom': '8px'}),

        html.Label("Budget E[R] / E[S]", style=_lbl),
        html.P("Part de la perte espérée cédée au réassureur.", style={
            'fontSize': '11px', 'color': PALETTE['text_muted'],
            'marginBottom': '8px', 'lineHeight': '1.4',
        }),
        html.Div([
            dcc.Slider(id='s1-er-frac', min=0.02, max=0.5, step=0.01, value=0.2,
                       marks=_slider_marks_er,
                       tooltip={'placement': 'bottom', 'always_visible': False}),
        ], style={'marginBottom': '20px', 'paddingBottom': '8px'}),

    ], style={'width': '260px', 'flexShrink': '0'})


def _params_panel_s2():
    return html.Div([
        # Context
        html.Div([
            html.Div("Scénario 2 — Prime de variance", style={
                'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '1px',
                'textTransform': 'uppercase', 'color': PALETTE['success'],
                'marginBottom': '6px',
            }),
            html.P(
                "P_R = E[R] + α_V·Var(R). À Var(R) fixé, le Quote-Part minimise Var(D). "
                "Proportion optimale : a* = √(Var(R)/Var(S)).",
                style={'fontSize': '12px', 'color': PALETTE['text_muted'],
                       'lineHeight': '1.6', 'margin': 0},
            ),
        ], style=_info_box),

        section_title("Distribution de S", PALETTE['success']),
        _dist_params_block('s2', PALETTE['success']),

        html.Div(style={'height': '1px', 'backgroundColor': PALETTE['border'],
                        'marginBottom': '16px'}),
        section_title("Paramètres de prime", PALETTE['success']),

        html.Label("Chargement de variance α_V", style=_lbl),
        html.Div([
            dcc.Slider(id='s2-alpha-v', min=0, max=0.5, step=0.01, value=0.05,
                       marks=_slider_marks_av,
                       tooltip={'placement': 'bottom', 'always_visible': False}),
        ], style={'marginBottom': '24px', 'paddingBottom': '8px'}),

        html.Label("Var(R) / Var(S)", style=_lbl),
        html.P("Fraction de la variance de S transférée au réassureur.", style={
            'fontSize': '11px', 'color': PALETTE['text_muted'],
            'marginBottom': '8px', 'lineHeight': '1.4',
        }),
        html.Div([
            dcc.Slider(id='s2-q-frac', min=0.02, max=0.7, step=0.01, value=0.25,
                       marks=_slider_marks_q,
                       tooltip={'placement': 'bottom', 'always_visible': False}),
        ], style={'marginBottom': '20px', 'paddingBottom': '8px'}),

    ], style={'width': '260px', 'flexShrink': '0'})


def _charts_area_s1():
    return html.Div([
        # Row 1: PDF + CDF
        html.Div([
            html.Div([
                dcc.Loading(dcc.Graph(id='s1-chart-pdf', config={'displayModeBar': False}),
                            color=PALETTE['accent2'], type='dot'),
            ], style={'flex': '1', 'minWidth': '0'}),
            html.Div([
                dcc.Loading(dcc.Graph(id='s1-chart-cdf', config={'displayModeBar': False}),
                            color=PALETTE['accent2'], type='dot'),
            ], style={'flex': '1', 'minWidth': '0'}),
        ], style={'display': 'flex', 'gap': '16px', 'marginBottom': '16px'}),

        # Row 2: Var(D) vs b
        dcc.Loading(dcc.Graph(id='s1-chart-var', config={'displayModeBar': False}),
                    color=PALETTE['accent2'], type='dot'),

        # Metrics
        html.Div(id='s1-metrics', style={
            'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap',
            'marginTop': '16px',
        }),

        # Why box
        html.Div([
            html.Div("Pourquoi le Stop-Loss gagne ici ?", style={
                'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '1px',
                'textTransform': 'uppercase', 'color': PALETTE['accent2'],
                'marginBottom': '8px',
            }),
            html.P(
                "Sous le principe de la valeur espérée, la contrainte fixe E[R] — donc E[D]. "
                "La CDF de D_SL = min(S, b*) croise celle de tout autre D en un seul point (en b*) : "
                "c'est la condition nécessaire et suffisante pour dominer au sens de la variance. "
                "Le QS, à même coût, élimine la queue droite moins efficacement.",
                style={'margin': 0, 'fontSize': '13px'},
            ),
        ], style=_why_box_s1),
    ], style={'flex': '1', 'minWidth': '0'})


def _charts_area_s2():
    return html.Div([
        # Row 1: Var(D) vs a + Distributions
        html.Div([
            html.Div([
                dcc.Loading(dcc.Graph(id='s2-chart-var', config={'displayModeBar': False}),
                            color=PALETTE['success'], type='dot'),
            ], style={'flex': '1', 'minWidth': '0'}),
            html.Div([
                dcc.Loading(dcc.Graph(id='s2-chart-dist', config={'displayModeBar': False}),
                            color=PALETTE['success'], type='dot'),
            ], style={'flex': '1', 'minWidth': '0'}),
        ], style={'display': 'flex', 'gap': '16px', 'marginBottom': '16px'}),

        # Row 2: Correlation
        dcc.Loading(dcc.Graph(id='s2-chart-cor', config={'displayModeBar': False}),
                    color=PALETTE['success'], type='dot'),

        # Metrics
        html.Div(id='s2-metrics', style={
            'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap',
            'marginTop': '16px',
        }),

        # Why box
        html.Div([
            html.Div("Pourquoi le Quote-Part gagne ici ?", style={
                'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '1px',
                'textTransform': 'uppercase', 'color': PALETTE['success'],
                'marginBottom': '8px',
            }),
            html.P(
                "Sous le principe de la variance, la contrainte fixe Var(R) — donc le chargement de sécurité. "
                "L'inégalité de Cauchy-Schwarz donne Var(D) ≥ (1−a)²·Var(S), "
                "et la borne inférieure est atteinte uniquement si R = a·S (proportionnalité stricte, Cor = 1). "
                "Le Stop-Loss, avec Cor < 1, ne peut pas atteindre cette borne.",
                style={'margin': 0, 'fontSize': '13px'},
            ),
        ], style=_why_box_s2),
    ], style={'flex': '1', 'minWidth': '0'})


PAGE_REASSURANCE = html.Div([

    # ── Page header ──────────────────────────────────────────────────────────
    html.Div([
        html.H2("Optimisation du Programme de Réassurance", style={
            'fontSize': '22px', 'fontWeight': '700', 'color': PALETTE['text'],
            'margin': '0 0 6px 0', 'letterSpacing': '-0.3px',
        }),
        html.P(
            "Critère : minimiser Var(D) — la variance de la perte retenue. "
            "Le principe de prime du réassureur détermine entièrement le contrat optimal.",
            style={'fontSize': '13px', 'color': PALETTE['text_muted'],
                   'margin': 0, 'lineHeight': '1.6'},
        ),
    ], style={
        'padding': '24px 28px 20px',
        'borderBottom': f"1px solid {PALETTE['border']}",
        'maxWidth': '1600px', 'margin': '0 auto',
    }),

    # ── Two scenarios as tabs ─────────────────────────────────────────────────
    html.Div([
        dcc.Tabs(
            id='reass-tabs',
            value='s1',
            colors={
                'border': PALETTE['border'],
                'primary': PALETTE['accent2'],
                'background': PALETTE['surface2'],
            },
            children=[

                # ── SCÉNARIO 1 ──────────────────────────────────────────────
                dcc.Tab(
                    label='Scénario 1 — Prime valeur espérée → Stop-Loss optimal',
                    value='s1',
                    style=_tab_style,
                    selected_style=_tab_sel_s1,
                    children=[
                        html.Div([
                            card(_params_panel_s1(), style={
                                'width': '260px', 'flexShrink': '0',
                                'alignSelf': 'flex-start',
                                'position': 'sticky', 'top': '16px',
                            }),
                            card(_charts_area_s1(), style={'flex': '1', 'minWidth': '0'}),
                        ], style={
                            'display': 'flex', 'gap': '20px',
                            'padding': '20px 0 0 0',
                        }),
                    ],
                ),

                # ── SCÉNARIO 2 ──────────────────────────────────────────────
                dcc.Tab(
                    label='Scénario 2 — Prime de variance → Quote-Part optimal',
                    value='s2',
                    style=_tab_style,
                    selected_style=_tab_sel_s2,
                    children=[
                        html.Div([
                            card(_params_panel_s2(), style={
                                'width': '260px', 'flexShrink': '0',
                                'alignSelf': 'flex-start',
                                'position': 'sticky', 'top': '16px',
                            }),
                            card(_charts_area_s2(), style={'flex': '1', 'minWidth': '0'}),
                        ], style={
                            'display': 'flex', 'gap': '20px',
                            'padding': '20px 0 0 0',
                        }),
                    ],
                ),
            ],
        ),
    ], style={
        'padding': '0 28px 32px',
        'maxWidth': '1600px',
        'margin': '0 auto',
    }),
])
