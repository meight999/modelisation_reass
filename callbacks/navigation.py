from server import app
from dash import Input, Output, State, callback_context
from config import PALETTE


@app.callback(
    [Output('page-modelisation', 'style'),
     Output('page-reassurance', 'style'),
     Output('nav-modelisation', 'style'),
     Output('nav-reassurance', 'style'),
     Output('current-page', 'data')],
    [Input('nav-modelisation', 'n_clicks'), Input('nav-reassurance', 'n_clicks')],
    State('current-page', 'data'),
    prevent_initial_call=False
)
def navigate(n_mod, n_rea, current):
    ctx = callback_context
    style_active = {'backgroundColor': PALETTE['accent'], 'color': '#000', 'border': 'none',
                    'padding': '8px 20px', 'borderRadius': '6px', 'cursor': 'pointer',
                    'fontWeight': '700', 'fontSize': '13px', 'letterSpacing': '1px', 'marginRight': '8px'}
    style_inactive = {'backgroundColor': 'transparent', 'color': PALETTE['text_muted'],
                      'border': f"1px solid {PALETTE['border']}", 'padding': '8px 20px',
                      'borderRadius': '6px', 'cursor': 'pointer', 'fontWeight': '600', 'fontSize': '13px', 'letterSpacing': '1px'}

    show = {'display': 'block'}
    hide = {'display': 'none'}

    if not ctx.triggered or ctx.triggered[0]['prop_id'] == '.':
        return show, hide, style_active, style_inactive, 'modelisation'

    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'nav-reassurance':
        return hide, show, style_inactive, {**style_active, 'marginRight': '0'}, 'reassurance'
    return show, hide, style_active, style_inactive, 'modelisation'
