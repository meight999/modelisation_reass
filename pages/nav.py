from dash import html
from config import PALETTE
from components.ui import _NAV_BTN_BASE

NAV_TABS = html.Div([
    html.Div([
        # Brand
        html.Div([
            html.Div([
                html.Span("◈ ", style={'color': PALETTE['accent'], 'fontSize': '18px'}),
                html.Span("Modélisation Réassurance", style={
                    'color': PALETTE['text'], 'fontSize': '15px', 'fontWeight': '700',
                    'letterSpacing': '0.5px', 'fontFamily': "'JetBrains Mono', monospace",
                }),
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '2px'}),
            html.Div("Modélisation & Réassurance", style={
                'fontSize': '11px', 'color': PALETTE['text_muted'],
                'letterSpacing': '0.5px', 'marginLeft': '2px',
            }),
        ]),
        # Navigation
        html.Div([
            html.Button("Modélisation", id='nav-modelisation', n_clicks=0, style={
                **_NAV_BTN_BASE,
                'backgroundColor': PALETTE['accent'], 'color': '#000',
                'marginRight': '6px',
            }),
            html.Button("Réassurance", id='nav-reassurance', n_clicks=0, style={
                **_NAV_BTN_BASE,
                'backgroundColor': 'transparent', 'color': PALETTE['text_muted'],
                'border': f"1px solid {PALETTE['border']}",
            }),
        ], style={'display': 'flex', 'alignItems': 'center'}),
    ], style={
        'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
        'maxWidth': '1600px', 'margin': '0 auto', 'padding': '0 32px',
    }),
], style={
    'backgroundColor': PALETTE['surface'],
    'padding': '14px 0',
    'borderBottom': f"1px solid {PALETTE['border']}",
    'position': 'sticky', 'top': '0', 'zIndex': '1000',
    'boxShadow': '0 2px 12px rgba(0,0,0,0.3)',
})
