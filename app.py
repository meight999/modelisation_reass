print("Démarrage RiskLens...")

from server import app
from config import GLOBAL_CSS
from pages.nav import NAV_TABS
from pages.modelling import PAGE_MODELISATION
from pages.reinsurance import PAGE_REASSURANCE
from dash import html, dcc

app.title = "RiskLens — Modélisation & Réassurance"

app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>RiskLens</title>
        {%favicon%}
        {%css%}
        <style>
''' + GLOBAL_CSS + '''
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

from config import PALETTE

app.layout = html.Div([
    NAV_TABS,
    # Stores partagés entre modélisation et réassurance — niveau racine = persistent
    dcc.Store(id='current-page', data='modelisation'),
    dcc.Store(id='stored-data'),
    dcc.Store(id='below-fits'),
    dcc.Store(id='above-fits'),
    dcc.Store(id='below-data-store'),
    dcc.Store(id='above-data-store'),
    dcc.Store(id='below-freq-store'),
    dcc.Store(id='above-freq-store'),
    # Stores réassurance
    dcc.Store(id='r-simulations-store'),
    dcc.Store(id='r-current-stack-store', data=[]),
    dcc.Store(id='r-saved-programs-store', data=[]),
    # Pages rendues une seule fois, visibilité gérée par display
    html.Div(PAGE_MODELISATION, id='page-modelisation', style={'display': 'block'}),
    html.Div(PAGE_REASSURANCE, id='page-reassurance', style={'display': 'none'}),
], style={'backgroundColor': PALETTE['bg'], 'minHeight': '100vh', 'fontFamily': "'Space Grotesk', sans-serif", 'color': PALETTE['text']})

# Register callbacks
import callbacks.navigation
import callbacks.modelling
import callbacks.reinsurance

if __name__ == '__main__':
    print("Lancement sur http://127.0.0.1:8050")
    app.run(debug=True, port=8050)
