from dash import html, dash_table
from config import PALETTE


def card(children, style=None, **kwargs):
    base = {
        'backgroundColor': PALETTE['surface'],
        'border': f"1px solid {PALETTE['border']}",
        'borderRadius': '12px',
        'padding': '24px',
    }
    if style: base.update(style)
    return html.Div(children, style=base, **kwargs)


def section_title(text, color=None):
    c = color or PALETTE['accent']
    return html.Div([
        html.Div(style={
            'width': '3px', 'height': '14px', 'backgroundColor': c,
            'borderRadius': '2px', 'marginRight': '10px', 'flexShrink': '0',
        }),
        html.Span(text, style={
            'fontSize': '12px', 'fontWeight': '700', 'letterSpacing': '1.5px',
            'textTransform': 'uppercase', 'color': c,
        }),
    ], style={
        'display': 'flex', 'alignItems': 'center',
        'borderBottom': f"1px solid {PALETTE['border']}",
        'paddingBottom': '12px', 'marginBottom': '18px',
    })


def stat_badge(label, value, color=None):
    c = color or PALETTE['accent']
    return html.Div([
        html.Div(value, style={
            'fontSize': '20px', 'fontWeight': '700', 'color': c,
            'fontFamily': "'JetBrains Mono', monospace", 'letterSpacing': '-0.5px',
        }),
        html.Div(label, style={
            'fontSize': '10px', 'color': PALETTE['text_muted'],
            'letterSpacing': '0.8px', 'textTransform': 'uppercase',
            'marginTop': '4px', 'fontWeight': '500',
        }),
    ], style={
        'backgroundColor': PALETTE['surface2'],
        'border': f"1px solid {PALETTE['border']}",
        'borderLeft': f"3px solid {c}",
        'borderRadius': '6px',
        'padding': '12px 16px',
        'minWidth': '120px',
        'textAlign': 'center',
    })


def btn_primary(text, id, style=None):
    base = {
        'backgroundColor': PALETTE['accent'],
        'color': '#000',
        'border': 'none',
        'borderRadius': '8px',
        'padding': '10px 22px',
        'cursor': 'pointer',
        'fontWeight': '700',
        'fontSize': '13px',
        'letterSpacing': '1px',
        'textTransform': 'uppercase',
        'width': '100%',
    }
    if style: base.update(style)
    return html.Button(text, id=id, n_clicks=0, style=base)


def btn_secondary(text, id, color=None, style=None):
    base = {
        'backgroundColor': 'transparent',
        'color': color or PALETTE['accent2'],
        'border': f"1px solid {color or PALETTE['accent2']}",
        'borderRadius': '8px',
        'padding': '8px 16px',
        'cursor': 'pointer',
        'fontWeight': '600',
        'fontSize': '12px',
        'width': '100%',
    }
    if style: base.update(style)
    return html.Button(text, id=id, n_clicks=0, style=base)


def make_table(data, columns, highlight_first=False):
    cond = [
        {'if': {'row_index': 'odd'}, 'backgroundColor': PALETTE['surface2']},
    ]
    if highlight_first:
        cond.append({'if': {'row_index': 0}, 'backgroundColor': '#1A3A2A', 'color': PALETTE['success'], 'fontWeight': '700'})
    return dash_table.DataTable(
        data=data, columns=columns,
        style_table={'borderRadius': '8px', 'overflow': 'hidden', 'border': f"1px solid {PALETTE['border']}"},
        style_cell={'textAlign': 'center', 'padding': '10px 14px', 'fontSize': '13px',
                    'backgroundColor': PALETTE['surface'], 'color': PALETTE['text'],
                    'border': f"1px solid {PALETTE['border']}", 'fontFamily': "'Courier New', monospace"},
        style_header={'backgroundColor': PALETTE['surface2'], 'color': PALETTE['accent'],
                      'fontWeight': '700', 'fontSize': '12px', 'letterSpacing': '1px',
                      'textTransform': 'uppercase', 'border': f"1px solid {PALETTE['border']}"},
        style_data_conditional=cond,
    )


def plotly_layout(title="", height=450):
    _grid = 'rgba(45,64,96,0.35)'
    return dict(
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(color=PALETTE['text'], size=14, family="'Space Grotesk', sans-serif"),
            x=0.01, xanchor='left', pad=dict(b=6),
        ),
        paper_bgcolor=PALETTE['surface'],
        plot_bgcolor='#0E1826',
        font=dict(color=PALETTE['text_muted'], size=12, family="'Space Grotesk', sans-serif"),
        height=height,
        margin=dict(l=72, r=28, t=56, b=72),
        xaxis=dict(
            gridcolor=_grid, linecolor=PALETTE['border'], zerolinecolor=_grid,
            tickfont=dict(size=11, color=PALETTE['text_muted']),
            title_font=dict(size=12, color=PALETTE['text'], family="'Space Grotesk', sans-serif"),
            title_standoff=14,
        ),
        yaxis=dict(
            gridcolor=_grid, linecolor=PALETTE['border'], zerolinecolor=_grid,
            tickfont=dict(size=11, color=PALETTE['text_muted']),
            title_font=dict(size=12, color=PALETTE['text'], family="'Space Grotesk', sans-serif"),
            title_standoff=14,
        ),
        legend=dict(
            bgcolor='rgba(22,32,50,0.95)', bordercolor=PALETTE['border'], borderwidth=1,
            font=dict(color=PALETTE['text'], size=11, family="'Space Grotesk', sans-serif"),
            itemsizing='constant',
        ),
        hovermode='closest',
        hoverlabel=dict(
            bgcolor=PALETTE['surface2'], bordercolor=PALETTE['border'],
            font=dict(color=PALETTE['text'], size=12, family="'Space Grotesk', sans-serif"),
        ),
    )


_LABEL = {'color': PALETTE['text'], 'fontSize': '13px', 'fontWeight': '500',
          'display': 'block', 'marginBottom': '6px', 'letterSpacing': '0.1px'}
_LABEL_OPT = {'color': PALETTE['text_muted'], 'fontSize': '12px', 'fontWeight': '400',
              'display': 'block', 'marginBottom': '6px'}
_INPUT = {'width': '100%', 'backgroundColor': '#1E2D42', 'border': f"1px solid {PALETTE['border']}",
          'color': PALETTE['text'], 'borderRadius': '6px', 'padding': '9px 12px',
          'fontSize': '13px', 'fontFamily': "'JetBrains Mono', monospace",
          'transition': 'border-color 0.15s ease'}


def _opt_badge():
    return html.Span("optionnel", style={
        'fontSize': '10px', 'fontWeight': '600', 'letterSpacing': '0.5px',
        'color': PALETTE['text_muted'], 'backgroundColor': PALETTE['surface2'],
        'border': f"1px solid {PALETTE['border']}", 'borderRadius': '3px',
        'padding': '1px 5px', 'marginLeft': '6px', 'verticalAlign': 'middle',
    })


def _field_label(text, optional=False):
    return html.Div([
        html.Span(text, style=_LABEL if not optional else _LABEL_OPT),
        _opt_badge() if optional else None,
    ], style={'marginBottom': '6px', 'display': 'flex', 'alignItems': 'center'})


_NAV_BTN_BASE = {
    'border': 'none', 'borderRadius': '6px', 'cursor': 'pointer',
    'padding': '8px 22px', 'fontSize': '13px', 'fontWeight': '600',
    'letterSpacing': '0.4px', 'fontFamily': "'Space Grotesk', sans-serif",
    'transition': 'all 0.15s ease',
}
