from server import app
from dash import Input, Output, State, dcc, html
import dash
import base64
import io
import numpy as np
import pandas as pd
import plotly.graph_objs as go

from config import PALETTE
from backend.severity import analyze_segment_data
from backend.frequency import compute_counts_from_dates, analyze_frequency
from components.ui import card, section_title, stat_badge, plotly_layout
from views.severity import view_severite_details, view_severite_ecdf, view_severite_qq, view_severite_histogram
from views.frequency import view_freq_details, view_freq_cmf, view_freq_ts


@app.callback(
    [Output('stored-data', 'data'), Output('column-name', 'options'),
     Output('date-column', 'options'), Output('upload-status', 'children')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def load_data(contents, filename):
    if contents is None: return None, [], [], ""
    try:
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded)) if filename.endswith(('.xlsx', '.xls')) else pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        opts = [{'label': c, 'value': c} for c in df.columns]
        date_opts = [{'label': '(aucune)', 'value': ''}] + opts
        return df.to_json(date_format='iso', orient='split'), opts, date_opts, f"✓ {filename} ({len(df):,} lignes)"
    except Exception as e:
        return None, [], [], f"Erreur : {str(e)}"


@app.callback(
    [Output('data-info-card', 'children'),
     Output('below-fits', 'data'), Output('below-data-store', 'data'),
     Output('above-fits', 'data'), Output('above-data-store', 'data'),
     Output('below-freq-store', 'data'), Output('above-freq-store', 'data')],
    Input('analyze-button', 'n_clicks'),
    [State('stored-data', 'data'), State('column-name', 'value'),
     State('date-column', 'value'), State('start-date-input', 'value'), State('threshold', 'value')]
)
def analyze_data(n_clicks, json_data, col, date_col, start_date, threshold):
    empty = (html.Div(), None, None, None, None, None, None)
    if not n_clicks or not json_data or not col: return empty
    try:
        df = pd.read_json(io.StringIO(json_data), orient='split')
        data = df[col].dropna()
        data = data[data > 0]
        if start_date and date_col and date_col in df.columns:
            ds = pd.to_datetime(df.loc[data.index, date_col], errors='coerce')
            data = data[ds.dt.year >= int(start_date)]
        below = data[data < threshold].values
        above = data[data >= threshold].values
        below_fits = analyze_segment_data(below)
        above_fits = analyze_segment_data(above)

        below_freq = above_freq = None
        if date_col and date_col in df.columns:
            di = df[col].dropna(); di = di[di > 0]
            if start_date:
                try:
                    ds_tmp = pd.to_datetime(df.loc[di.index, date_col], errors='coerce')
                    di = di[ds_tmp.dt.year >= int(start_date)]
                except: pass
            ds = df.loc[di.index, date_col]
            bc, bl = compute_counts_from_dates(ds, di < threshold)
            ac, al = compute_counts_from_dates(ds, di >= threshold)
            if bc is not None:
                below_freq = {'counts': bc.tolist(), 'labels': bl, 'fits': analyze_frequency(bc)}
            if ac is not None:
                above_freq = {'counts': ac.tolist(), 'labels': al, 'fits': analyze_frequency(ac)}

        total = len(below) + len(above)
        info = card([
            section_title("Résumé des données"),
            html.Div([
                stat_badge("Total sinistres", f"{total:,}"),
                stat_badge("Sous le seuil", f"{len(below):,}", PALETTE['success']),
                stat_badge("Au-dessus", f"{len(above):,}", PALETTE['danger']),
                stat_badge("Seuil", f"{threshold:,} €", PALETTE['warning']),
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '8px'}),
        ])
        return info, below_fits, below.tolist(), above_fits, above.tolist(), below_freq, above_freq
    except Exception as e:
        return card([html.P(f"Erreur : {str(e)}", style={'color': PALETTE['danger']})]), None, None, None, None, None, None


@app.callback(Output('below-content', 'children'),
              [Input('below-tabs', 'value'), Input('below-fits', 'data'), Input('below-data-store', 'data'), Input('threshold', 'value')])
def render_below(tab, fits, data, threshold):
    if tab == 'below-details':       return view_severite_details(data, fits, threshold, "sous")
    elif tab == 'below-ecdf-criteria': return view_severite_ecdf(data, fits, threshold)
    elif tab == 'below-qq-quantiles':  return view_severite_qq(data, fits, threshold)
    elif tab == 'below-histogram':     return view_severite_histogram(data, fits, threshold)


@app.callback(Output('above-content', 'children'),
              [Input('above-tabs', 'value'), Input('above-fits', 'data'), Input('above-data-store', 'data'), Input('threshold', 'value')])
def render_above(tab, fits, data, threshold):
    if tab == 'above-details':        return view_severite_details(data, fits, threshold, "au-dessus")
    elif tab == 'above-ecdf-criteria': return view_severite_ecdf(data, fits, threshold)
    elif tab == 'above-qq-quantiles':  return view_severite_qq(data, fits, threshold)
    elif tab == 'above-histogram':     return view_severite_histogram(data, fits, threshold)


@app.callback(Output('below-freq-content', 'children'),
              [Input('below-freq-tabs', 'value'), Input('below-freq-store', 'data')])
def render_below_freq(tab, store):
    if not store:
        return html.Div("Sélectionnez une colonne de date pour l'analyse de fréquence.", style={'color': PALETTE['text_muted'], 'padding': '40px', 'textAlign': 'center'})
    c, l, f = np.array(store['counts']), store.get('labels'), store.get('fits')
    if tab == 'below-freq-details': return view_freq_details(c, f)
    elif tab == 'below-freq-cmf': return view_freq_cmf(c, f, l)
    elif tab == 'below-freq-ts': return view_freq_ts(c, f, l)


@app.callback(Output('above-freq-content', 'children'),
              [Input('above-freq-tabs', 'value'), Input('above-freq-store', 'data')])
def render_above_freq(tab, store):
    if not store:
        return html.Div("Sélectionnez une colonne de date pour l'analyse de fréquence.", style={'color': PALETTE['text_muted'], 'padding': '40px', 'textAlign': 'center'})
    c, l, f = np.array(store['counts']), store.get('labels'), store.get('fits')
    if tab == 'above-freq-details': return view_freq_details(c, f)
    elif tab == 'above-freq-cmf': return view_freq_cmf(c, f, l)
    elif tab == 'above-freq-ts': return view_freq_ts(c, f, l)


@app.callback(
    Output('threshold-preview-container', 'children'),
    [Input('below-data-store', 'data'), Input('above-data-store', 'data'), Input('threshold', 'value')]
)
def render_threshold_preview(below_data, above_data, threshold):
    """Histogramme bicolore montrant la répartition des sinistres autour du seuil."""
    if below_data is None and above_data is None:
        return html.Div()
    below = np.array(below_data or [])
    above = np.array(above_data or [])
    total = len(below) + len(above)
    if total == 0:
        return html.Div()

    all_data = np.concatenate([below, above])
    all_positive = all_data[all_data > 0]
    use_log = (
        len(all_positive) > 0
        and threshold is not None
        and threshold > 0
        and np.max(all_positive) / max(np.min(all_positive), 1) > 50
    )

    # Bins en espace log ou linéaire
    if use_log and len(all_positive) > 0:
        log_min = np.log10(max(np.min(all_positive), 1))
        log_max = np.log10(np.percentile(all_positive, 99.5))
        bin_edges = np.logspace(log_min, log_max, 60)
        # clamp data to avoid log(0)
        below_plot = below[below > 0]
        above_plot = above[above > 0]
    else:
        p_low = np.percentile(all_data, 0.5) if len(all_data) > 0 else 0
        p_high = np.percentile(all_data, 99.5) if len(all_data) > 0 else 1
        bin_edges = np.linspace(p_low, p_high, 60)
        below_plot = below
        above_plot = above

    fig = go.Figure()
    if len(below_plot) > 0:
        fig.add_trace(go.Histogram(
            x=below_plot, xbins=dict(start=bin_edges[0], end=bin_edges[-1], size=(bin_edges[-1]-bin_edges[0])/58),
            autobinx=False, histnorm='',
            name=f"Attritionnels — {len(below):,} sin. ({len(below)/total*100:.0f}%)",
            marker_color='rgba(16,185,129,0.40)',
            marker_line_color='rgba(16,185,129,0.85)', marker_line_width=0.8,
        ))
    if len(above_plot) > 0:
        fig.add_trace(go.Histogram(
            x=above_plot, xbins=dict(start=bin_edges[0], end=bin_edges[-1], size=(bin_edges[-1]-bin_edges[0])/58),
            autobinx=False, histnorm='',
            name=f"Graves — {len(above):,} sin. ({len(above)/total*100:.0f}%)",
            marker_color='rgba(239,68,68,0.40)',
            marker_line_color='rgba(239,68,68,0.85)', marker_line_width=0.8,
        ))
    if threshold and threshold > 0:
        fig.add_vline(
            x=threshold, line_dash='dash', line_color=PALETTE['warning'], line_width=2,
            annotation=dict(
                text=f"<b>Seuil : {threshold:,.0f} €</b>",
                font=dict(color=PALETTE['warning'], size=12),
                bgcolor=PALETTE['surface2'],
                bordercolor=PALETTE['warning'],
                borderwidth=1, borderpad=4,
            ),
            annotation_position="top right",
        )

    layout = plotly_layout(f"Répartition des {total:,} sinistres — aperçu du seuil", height=360)
    layout['barmode'] = 'overlay'
    layout['margin'] = dict(l=72, r=28, t=52, b=90)
    layout['legend'] = dict(
        bgcolor='rgba(22,32,50,0.95)', bordercolor=PALETTE['border'], borderwidth=1,
        font=dict(color=PALETTE['text'], size=11), orientation='h',
        yanchor='top', y=-0.24, x=0,
    )

    if use_log:
        # Ticks manuels lisibles en mode log
        tick_vals = []
        for exp in range(int(np.floor(np.log10(max(all_positive.min(), 1)))),
                         int(np.ceil(np.log10(all_positive.max()))) + 1):
            for m in [1, 2, 5]:
                v = m * 10**exp
                if all_positive.min() * 0.5 <= v <= all_positive.max() * 1.5:
                    tick_vals.append(v)
        tick_text = [
            f"{v/1e6:.0f}M €" if v >= 1e6 else
            f"{v/1e3:.0f}k €" if v >= 1e3 else
            f"{v:.0f} €"
            for v in tick_vals
        ]
        layout['xaxis'].update({
            'type': 'log',
            'tickvals': tick_vals,
            'ticktext': tick_text,
            'title': 'Montant du sinistre (échelle log)',
            'exponentformat': 'none',
        })
    else:
        layout['xaxis'].update({
            'title': 'Montant du sinistre (€)',
            'tickformat': ',.0f',
            'ticksuffix': ' €',
            'exponentformat': 'none',
        })
    layout['yaxis']['title'] = "Nombre de sinistres"

    fig.update_layout(layout)
    return card(
        [dcc.Graph(figure=fig, config={'displayModeBar': True, 'modeBarButtonsToRemove': ['select2d','lasso2d','autoScale2d']})],
        style={'marginBottom': '16px', 'padding': '16px 20px 8px 20px'}
    )
