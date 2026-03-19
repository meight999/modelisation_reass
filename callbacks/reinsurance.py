from server import app
from dash import Input, Output, html
import numpy as np
from scipy.stats import gaussian_kde
import plotly.graph_objs as go

from config import PALETTE
from components.ui import plotly_layout, stat_badge
from backend.reinsurance_theory import (
    moments, scenario1, scenario2,
    var_retained_sl, e_sl,
    _ppf, _pdf, _cdf,
)

# ─── Palette shortcuts ────────────────────────────────────────────────────────
_A2 = PALETTE['accent2']    # blue — Scénario 1 / Stop-Loss
_GR = PALETTE['success']    # green — Scénario 2 / Quote-Part
_OR = PALETTE['warning']    # orange — competitor
_RED = PALETTE['danger']
_MUT = PALETTE['text_muted']
_TXT = PALETTE['text']


def _rgba(hex_c, a=0.18):
    h = hex_c.lstrip('#')
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
    return f"rgba({r},{g},{b},{a})"


def _fmt(v, unit='€'):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return 'N/A'
    if abs(v) >= 1e9:
        return f"{v/1e9:.2f}G {unit}"
    if abs(v) >= 1e6:
        return f"{v/1e6:.2f}M {unit}"
    if abs(v) >= 1e3:
        return f"{v/1e3:.0f}k {unit}"
    return f"{v:.0f} {unit}"


def _pct(v):
    return f"{v:.1f}%" if v is not None else 'N/A'


# ─── Distribution visibility callbacks ───────────────────────────────────────

def _toggle_params(dist):
    show = {'display': 'block', 'marginBottom': '4px'}
    hide = {'display': 'none'}
    return (
        show if dist == 'exponential' else hide,
        show if dist == 'lognormal'   else hide,
        show if dist == 'gamma'       else hide,
    )


@app.callback(
    Output('s1-params-exp', 'style'),
    Output('s1-params-ln',  'style'),
    Output('s1-params-gam', 'style'),
    Input('s1-dist', 'value'),
)
def _toggle_s1(dist):
    return _toggle_params(dist)


@app.callback(
    Output('s2-params-exp', 'style'),
    Output('s2-params-ln',  'style'),
    Output('s2-params-gam', 'style'),
    Input('s2-dist', 'value'),
)
def _toggle_s2(dist):
    return _toggle_params(dist)


# ─── Helper: build params dict from inputs ───────────────────────────────────

def _build_params(dist, exp_mean, ln_mu, ln_sigma, gam_alpha, gam_beta):
    if dist == 'exponential':
        return {'mean': float(exp_mean or 100000)}
    elif dist == 'lognormal':
        return {'mu': float(ln_mu or 11.0), 'sigma': float(ln_sigma or 0.8)}
    else:
        return {'alpha': float(gam_alpha or 3.0), 'beta': float(gam_beta or 33000)}


def _dist_info(name, p):
    m, v = moments(name, p)
    std = np.sqrt(v)
    cv = std / m if m > 0 else 0
    return f"E[S] = {_fmt(m)}  ·  σ(S) = {_fmt(std)}  ·  CV = {cv:.2f}"


# ─── Chart builders — Scenario 1 ─────────────────────────────────────────────

def _fig_s1_pdf(name, p, res):
    b = res['b_opt']
    x_max = _ppf(name, p, 0.995)
    x_max = max(x_max, b * 1.5)
    xs = np.linspace(1e-6, x_max, 600)
    ys = _pdf(name, p, xs)

    fig = go.Figure()
    # Retained area [0, b]
    mask_r = xs <= b
    fig.add_trace(go.Scatter(
        x=xs[mask_r], y=ys[mask_r],
        fill='tozeroy', fillcolor=_rgba(_A2, 0.22),
        line=dict(color=_A2, width=1.5),
        name='Retenu D = min(S, b*)',
        hovertemplate='S = %{x:,.0f}<br>f(S) = %{y:.2e}<extra>Retenu</extra>',
    ))
    # Ceded area [b, ∞]
    mask_c = xs >= b
    fig.add_trace(go.Scatter(
        x=xs[mask_c], y=ys[mask_c],
        fill='tozeroy', fillcolor=_rgba(_OR, 0.20),
        line=dict(color=_OR, width=1.5),
        name='Cédé R = (S − b*)₊',
        hovertemplate='S = %{x:,.0f}<br>f(S) = %{y:.2e}<extra>Cédé</extra>',
    ))
    # Vertical line at b*
    fig.add_vline(x=b, line=dict(color=_A2, width=2, dash='dash'),
                  annotation_text=f"b* = {_fmt(b)}",
                  annotation_font=dict(color=_A2, size=11))

    layout = plotly_layout("Distribution de S — Partage Retenu / Cédé", height=300)
    layout['xaxis']['title'] = 'Perte S'
    layout['yaxis']['title'] = 'Densité'
    layout['margin'] = dict(l=60, r=20, t=50, b=56)
    fig.update_layout(**layout)
    return fig


def _fig_s1_cdf(name, p, res):
    b = res['b_opt']
    a_qs = res['a_qs']
    # Show x up to 1.8*b to see the crossing clearly
    x_max = min(b * 1.8, _ppf(name, p, 0.999))
    xs = np.linspace(0, x_max, 600)

    # CDF of D_SL = min(S, b):  F_S(x) for x < b, 1 for x >= b
    cdf_sl = np.where(xs < b, _cdf(name, p, xs), 1.0)

    # CDF of D_QS = (1-a)*S:  F_S(x/(1-a))
    denom = (1 - a_qs)
    if denom > 1e-6:
        cdf_qs = _cdf(name, p, xs / denom)
    else:
        cdf_qs = np.ones_like(xs)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=cdf_sl,
        name=f'Stop-Loss (b*={_fmt(b)})',
        line=dict(color=_A2, width=2.5),
        hovertemplate='D = %{x:,.0f}<br>F(D) = %{y:.3f}<extra>Stop-Loss</extra>',
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=cdf_qs,
        name=f'Quote-Part (a={a_qs:.2f})',
        line=dict(color=_OR, width=2, dash='dot'),
        hovertemplate='D = %{x:,.0f}<br>F(D) = %{y:.3f}<extra>Quote-Part</extra>',
    ))
    fig.add_vline(x=b, line=dict(color=_MUT, width=1, dash='dash'),
                  annotation_text="b* (croisement unique)",
                  annotation_font=dict(color=_MUT, size=10))

    layout = plotly_layout("CDF de D — Croisement unique en b*", height=300)
    layout['xaxis']['title'] = 'Perte retenue D'
    layout['yaxis']['title'] = 'F(d)'
    layout['margin'] = dict(l=60, r=20, t=50, b=56)
    fig.update_layout(**layout)
    return fig


def _fig_s1_var(name, p, res):
    b_opt = res['b_opt']
    var_qs = res['var_qs']
    x_max = _ppf(name, p, 0.99)
    n_pts = 60 if name == 'gamma' else 150
    b_vals = np.linspace(0.01 * x_max, x_max, n_pts)
    var_vals = [var_retained_sl(name, p, float(b)) for b in b_vals]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=b_vals, y=var_vals,
        name='Var(D_SL)',
        line=dict(color=_A2, width=2.5),
        fill='tozeroy', fillcolor=_rgba(_A2, 0.08),
        hovertemplate='b = %{x:,.0f}<br>Var(D) = %{y:,.0f}<extra>Stop-Loss</extra>',
    ))
    # Optimal b*
    if np.isfinite(b_opt) and 0 < b_opt < x_max:
        var_at_opt = var_retained_sl(name, p, b_opt)
        fig.add_trace(go.Scatter(
            x=[b_opt], y=[var_at_opt],
            mode='markers',
            marker=dict(color=_A2, size=12, symbol='star',
                        line=dict(color='white', width=1.5)),
            name=f'Optimum b* = {_fmt(b_opt)}',
            hovertemplate=f'b* = {_fmt(b_opt)}<br>Var(D*) = {var_at_opt:,.0f}<extra></extra>',
        ))
        fig.add_vline(x=b_opt, line=dict(color=_A2, width=1.5, dash='dash'))
    # Horizontal line for QS variance
    fig.add_hline(y=var_qs,
                  line=dict(color=_OR, width=2, dash='dot'),
                  annotation_text=f"Var(D_QS) = {_fmt(var_qs, '')}",
                  annotation_font=dict(color=_OR, size=11),
                  annotation_position='top right')

    layout = plotly_layout("Var(D) en fonction de la rétention b", height=300)
    layout['xaxis']['title'] = 'Rétention b'
    layout['yaxis']['title'] = 'Var(D)'
    layout['margin'] = dict(l=72, r=20, t=50, b=56)
    fig.update_layout(**layout)
    return fig


def _metrics_s1(res):
    var_sl, var_qs = res['var_sl'], res['var_qs']
    std_sl = np.sqrt(var_sl) if var_sl >= 0 else 0
    std_qs = np.sqrt(var_qs) if var_qs >= 0 else 0

    winner_color = _A2 if var_sl <= var_qs else _OR
    loser_color = _OR if var_sl <= var_qs else _A2

    items = [
        stat_badge("Rétention b*", _fmt(res['b_opt']), _A2),
        stat_badge("E[D] retenue", _fmt(res['e_d']), _MUT),
        stat_badge("Prime P_R", _fmt(res['premium']), _MUT),
        stat_badge("σ(D) Stop-Loss", _fmt(std_sl), winner_color),
        stat_badge("σ(D) Quote-Part", _fmt(std_qs), loser_color),
        stat_badge("Gain SL vs QS", f"+{res['gain_pct']:.1f}%", _GR),
    ]
    return items


# ─── Chart builders — Scenario 2 ─────────────────────────────────────────────

def _fig_s2_var(res):
    """Var(D_QS) = (1-a)²·Var(S) as a function of a."""
    var_s = res['var_s']
    a_opt = res['a_opt']
    var_sl = res['var_sl']

    a_vals = np.linspace(0, 0.98, 300)
    var_qs_vals = (1 - a_vals) ** 2 * var_s

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=a_vals, y=var_qs_vals,
        name='Var(D_QS) = (1−a)²·Var(S)',
        line=dict(color=_GR, width=2.5),
        fill='tozeroy', fillcolor=_rgba(_GR, 0.08),
        hovertemplate='a = %{x:.3f}<br>Var(D) = %{y:,.0f}<extra>Quote-Part</extra>',
    ))
    # Optimal a*
    var_at_opt = (1 - a_opt) ** 2 * var_s
    fig.add_trace(go.Scatter(
        x=[a_opt], y=[var_at_opt],
        mode='markers',
        marker=dict(color=_GR, size=12, symbol='star',
                    line=dict(color='white', width=1.5)),
        name=f'a* = {a_opt:.3f}',
        hovertemplate=f'a* = {a_opt:.3f}<br>Var(D*) = {var_at_opt:,.0f}<extra></extra>',
    ))
    fig.add_vline(x=a_opt, line=dict(color=_GR, width=1.5, dash='dash'))

    # SL variance for same Var(R)
    if var_sl is not None:
        fig.add_hline(y=var_sl,
                      line=dict(color=_OR, width=2, dash='dot'),
                      annotation_text=f"Var(D_SL) même Var(R) = {_fmt(var_sl, '')}",
                      annotation_font=dict(color=_OR, size=11),
                      annotation_position='top right')

    layout = plotly_layout("Var(D) en fonction de la proportion cédée a", height=300)
    layout['xaxis']['title'] = 'Proportion cédée a'
    layout['yaxis']['title'] = 'Var(D)'
    layout['xaxis']['tickformat'] = '.0%'
    layout['margin'] = dict(l=72, r=20, t=50, b=56)
    fig.update_layout(**layout)
    return fig


def _fig_s2_dist(res, name, p):
    """KDE distributions of D_QS vs D_SL."""
    s_arr = res['s_samples']
    a_opt = res['a_opt']
    b_sl = res['b_sl']

    d_qs = (1 - a_opt) * s_arr
    x_max = float(np.percentile(s_arr, 99.5))
    xs = np.linspace(0, x_max, 400)

    fig = go.Figure()
    if np.std(d_qs) > 0:
        kde_qs = gaussian_kde(d_qs, bw_method='scott')
        fig.add_trace(go.Scatter(
            x=xs, y=kde_qs(xs),
            name=f'D_QS (a*={a_opt:.2f})',
            line=dict(color=_GR, width=2.5),
            fill='tozeroy', fillcolor=_rgba(_GR, 0.15),
            hovertemplate='D = %{x:,.0f}<br>f(D) = %{y:.3e}<extra>Quote-Part</extra>',
        ))

    if b_sl is not None:
        d_sl = np.minimum(s_arr, b_sl)
        # Add tiny jitter to the atom at b_sl so KDE doesn't collapse
        at_atom = d_sl >= b_sl * 0.9999
        d_sl_kde = d_sl.copy().astype(float)
        d_sl_kde[at_atom] += np.random.default_rng(0).normal(0, b_sl * 5e-4, int(at_atom.sum()))
        if np.std(d_sl_kde) > 0:
            kde_sl = gaussian_kde(d_sl_kde, bw_method='scott')
            fig.add_trace(go.Scatter(
                x=xs, y=kde_sl(xs),
                name=f'D_SL (b={_fmt(b_sl)})',
                line=dict(color=_OR, width=2, dash='dot'),
                fill='tozeroy', fillcolor=_rgba(_OR, 0.10),
                hovertemplate='D = %{x:,.0f}<br>f(D) = %{y:.3e}<extra>Stop-Loss</extra>',
            ))

    layout = plotly_layout("Distribution de D — QS vs SL (même Var(R))", height=300)
    layout['xaxis']['title'] = 'Perte retenue D'
    layout['yaxis']['title'] = 'Densité'
    layout['margin'] = dict(l=60, r=20, t=50, b=56)
    fig.update_layout(**layout)
    return fig


def _fig_s2_cor(res):
    """Bar chart: Cor(S, R) for QS vs SL."""
    cor_qs = res['cor_qs']
    cor_sl = res['cor_sl']

    labels = ['Quote-Part (optimal)', 'Stop-Loss (concurrent)']
    values = [cor_qs, cor_sl if cor_sl is not None else 0]
    colors = [_GR, _OR]
    texts = [f"{cor_qs:.4f}", f"{cor_sl:.4f}" if cor_sl is not None else 'N/A']

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=texts,
        textposition='outside',
        textfont=dict(size=13, color=_TXT, family="'JetBrains Mono', monospace"),
        hovertemplate='%{x}<br>Cor(S, R) = %{y:.4f}<extra></extra>',
        width=0.4,
    ))

    # Annotation explaining why Cor=1 matters
    fig.add_annotation(
        x='Quote-Part (optimal)', y=cor_qs,
        text="Cor = 1 — Cauchy-Schwarz atteint",
        showarrow=True, arrowhead=2, arrowcolor=_GR,
        ax=0, ay=-40,
        font=dict(color=_GR, size=11),
        bgcolor='rgba(0,0,0,0)',
    )

    layout = plotly_layout("Corrélation Cor(S, R) — QS = 1 par construction", height=300)
    layout['yaxis']['title'] = 'Cor(S, R)'
    layout['yaxis']['range'] = [0, 1.15]
    layout['xaxis']['tickfont'] = dict(size=12, color=_TXT)
    layout['margin'] = dict(l=60, r=20, t=50, b=56)
    fig.update_layout(**layout)
    return fig


def _metrics_s2(res):
    var_qs, var_sl = res['var_qs'], res['var_sl']
    std_qs = np.sqrt(var_qs) if var_qs is not None and var_qs >= 0 else None
    std_sl = np.sqrt(var_sl) if var_sl is not None and var_sl >= 0 else None

    items = [
        stat_badge("Proportion a*", f"{res['a_opt']:.3f}", _GR),
        stat_badge("E[D] retenue", _fmt(res['e_d']), _MUT),
        stat_badge("Prime P_R", _fmt(res['premium']), _MUT),
        stat_badge("σ(D) Quote-Part", _fmt(std_qs) if std_qs else 'N/A', _GR),
        stat_badge("σ(D) Stop-Loss", _fmt(std_sl) if std_sl else 'N/A', _OR),
        stat_badge("Gain QS vs SL", f"+{res['gain_pct']:.1f}%", _GR),
    ]
    return items


# ─── Main callback — Scenario 1 ──────────────────────────────────────────────

@app.callback(
    Output('s1-chart-pdf', 'figure'),
    Output('s1-chart-cdf', 'figure'),
    Output('s1-chart-var', 'figure'),
    Output('s1-metrics', 'children'),
    Output('s1-dist-info', 'children'),
    Input('s1-dist',      'value'),
    Input('s1-exp-mean',  'value'),
    Input('s1-ln-mu',     'value'),
    Input('s1-ln-sigma',  'value'),
    Input('s1-gam-alpha', 'value'),
    Input('s1-gam-beta',  'value'),
    Input('s1-theta',     'value'),
    Input('s1-er-frac',   'value'),
)
def update_s1(dist, exp_mean, ln_mu, ln_sigma, gam_alpha, gam_beta, theta, er_frac):
    dist = dist or 'lognormal'
    p = _build_params(dist, exp_mean, ln_mu, ln_sigma, gam_alpha, gam_beta)
    theta = float(theta or 0.2)
    er_frac = float(er_frac or 0.2)

    try:
        res = scenario1(dist, p, theta, er_frac)
        fig_pdf = _fig_s1_pdf(dist, p, res)
        fig_cdf = _fig_s1_cdf(dist, p, res)
        fig_var = _fig_s1_var(dist, p, res)
        metrics = _metrics_s1(res)
        info = _dist_info(dist, p)
    except Exception as e:
        empty = go.Figure()
        empty.update_layout(**plotly_layout(f"Erreur : {e}", height=300))
        return empty, empty, empty, [], str(e)

    return fig_pdf, fig_cdf, fig_var, metrics, info


# ─── Main callback — Scenario 2 ──────────────────────────────────────────────

@app.callback(
    Output('s2-chart-var',  'figure'),
    Output('s2-chart-dist', 'figure'),
    Output('s2-chart-cor',  'figure'),
    Output('s2-metrics', 'children'),
    Output('s2-dist-info', 'children'),
    Input('s2-dist',      'value'),
    Input('s2-exp-mean',  'value'),
    Input('s2-ln-mu',     'value'),
    Input('s2-ln-sigma',  'value'),
    Input('s2-gam-alpha', 'value'),
    Input('s2-gam-beta',  'value'),
    Input('s2-alpha-v',   'value'),
    Input('s2-q-frac',    'value'),
)
def update_s2(dist, exp_mean, ln_mu, ln_sigma, gam_alpha, gam_beta, alpha_v, q_frac):
    dist = dist or 'lognormal'
    p = _build_params(dist, exp_mean, ln_mu, ln_sigma, gam_alpha, gam_beta)
    alpha_v = float(alpha_v or 0.05)
    q_frac = float(q_frac or 0.25)

    try:
        res = scenario2(dist, p, q_frac, alpha_v)
        fig_var  = _fig_s2_var(res)
        fig_dist = _fig_s2_dist(res, dist, p)
        fig_cor  = _fig_s2_cor(res)
        metrics  = _metrics_s2(res)
        info = _dist_info(dist, p)
    except Exception as e:
        empty = go.Figure()
        empty.update_layout(**plotly_layout(f"Erreur : {e}", height=300))
        return empty, empty, empty, [], str(e)

    return fig_var, fig_dist, fig_cor, metrics, info
