print("Démarrage Modélisation Réassurance...")

from server import app
from config import GLOBAL_CSS
from pages.nav import NAV_TABS
from pages.modelling import PAGE_MODELISATION
from pages.reinsurance import PAGE_REASSURANCE
from dash import html, dcc

app.title = "Modélisation Réassurance"

app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Modélisation Réassurance</title>
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
    # Stores partagés entre modélisation et réassurance
    # storage_type='local'    → persist après fermeture du navigateur
    # storage_type='session'  → persist sur refresh, effacé à la fermeture de l'onglet
    dcc.Store(id='current-page',           data='modelisation', storage_type='local'),
    dcc.Store(id='stored-data',            storage_type='memory'),    # données brutes uploadées (memory = pas de limite de taille)
    dcc.Store(id='below-fits',             storage_type='local'),     # résultats modélisation
    dcc.Store(id='above-fits',             storage_type='local'),
    dcc.Store(id='below-data-store',       storage_type='memory'),    # vecteurs de sinistres
    dcc.Store(id='above-data-store',       storage_type='memory'),
    dcc.Store(id='below-freq-store',       storage_type='local'),
    dcc.Store(id='above-freq-store',       storage_type='local'),
    # Stores réassurance
    dcc.Store(id='r-simulations-store',    storage_type='session'),   # simulations (larges)
    dcc.Store(id='r-current-stack-store',  data=[], storage_type='local'),
    dcc.Store(id='r-saved-programs-store', data=[], storage_type='local'),
    # Pages rendues une seule fois, visibilité gérée par display
    html.Div(PAGE_MODELISATION, id='page-modelisation', style={'display': 'block'}),
    html.Div(PAGE_REASSURANCE, id='page-reassurance', style={'display': 'none'}),
], style={'backgroundColor': PALETTE['bg'], 'minHeight': '100vh', 'fontFamily': "'Space Grotesk', sans-serif", 'color': PALETTE['text']})

# Register callbacks
import callbacks.navigation
import callbacks.modelling
import callbacks.reinsurance

if __name__ == '__main__':
    print("Lancement sur http://127.0.0.1:8050")  # noqa
    app.run(debug=True, port=8050)
