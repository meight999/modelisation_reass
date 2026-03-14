PALETTE = {
    'bg': '#0F1923',
    'surface': '#1A2535',
    'surface2': '#243044',
    'accent': '#00D4B4',
    'accent2': '#0099FF',
    'danger': '#FF4D6D',
    'warning': '#FFB703',
    'success': '#06D6A0',
    'text': '#E8EDF5',
    'text_muted': '#7A8BA0',
    'border': '#2D4060',
    'below_freq': '#1ABC9C',
    'above_freq': '#E74C3C',
}

SEV_DIST_NAMES = {'gamma': 'Gamma', 'lognorm': 'Lognormale', 'weibull': 'Weibull', 'pareto': 'Pareto'}
SEV_COLORS = {'gamma': '#E55039', 'lognorm': '#2E86C1', 'weibull': '#D4AC0D', 'pareto': '#7D3C98'}

FREQ_DIST_NAMES = {'poisson': 'Poisson', 'neg_binomial': 'Binomiale Négative', 'geometric': 'Géométrique'}
FREQ_COLORS = {'poisson': '#E55039', 'neg_binomial': '#2E86C1', 'geometric': '#D4AC0D'}

GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background-color: #0E1520 !important;
  font-family: 'Space Grotesk', 'Inter', sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: #F1F5F9;
  -webkit-font-smoothing: antialiased;
}

/* ── Scrollbar ─────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0E1520; }
::-webkit-scrollbar-thumb { background: #2D3F5E; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #3D5278; }

/* ── Inputs ────────────────────────────────────────────── */
input, textarea {
  font-family: 'Space Grotesk', sans-serif !important;
  transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
input:focus, textarea:focus {
  outline: none !important;
  border-color: #00C4A7 !important;
  box-shadow: 0 0 0 3px rgba(0,196,167,0.12) !important;
}
input[type=number]::-webkit-inner-spin-button { opacity: 0.25; }

/* ── Dash Tabs ─────────────────────────────────────────── */
.tab {
  background-color: #162032 !important;
  color: #6B7FA0 !important;
  border: 1px solid #2D3F5E !important;
  border-bottom: none !important;
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  letter-spacing: 0.3px !important;
  transition: color 0.15s ease, background-color 0.15s ease !important;
  cursor: pointer !important;
}
.tab:hover {
  color: #A8BACE !important;
  background-color: #1A2840 !important;
}
.tab--selected, .tab-selected {
  font-weight: 700 !important;
  border-bottom: none !important;
}

/* ── Details / Summary ─────────────────────────────────── */
details summary { cursor: pointer; user-select: none; }
details summary::-webkit-details-marker { color: #6B7FA0; }

/* ── Dash DataTable ────────────────────────────────────── */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td,
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
}

/* ── Dropdown (react-select v1 used by Dash) ───────────── */
.Select-control {
  background-color: #1E2D42 !important;
  border: 1px solid #2D3F5E !important;
  border-radius: 6px !important;
  transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
  min-height: 36px !important;
}
.Select-value-label { color: #E8EDF5 !important; font-size: 13px !important; font-family: 'Space Grotesk', sans-serif !important; }
.Select-placeholder { color: #6B7FA0 !important; font-size: 13px !important; }
.Select-arrow { border-color: #6B7FA0 transparent transparent !important; }
.Select.is-focused > .Select-control {
  border-color: #00C4A7 !important;
  box-shadow: 0 0 0 3px rgba(0,196,167,0.12) !important;
}
.Select-input > input { color: #E8EDF5 !important; font-family: 'Space Grotesk', sans-serif !important; }
.Select-menu-outer {
  background-color: #1A2A3E !important;
  border: 1px solid #2D3F5E !important;
  border-radius: 8px !important;
  box-shadow: 0 12px 32px rgba(0,0,0,0.6) !important;
  z-index: 9999 !important;
  margin-top: 2px !important;
}
.Select-menu { background-color: transparent !important; }
.Select-option {
  background-color: transparent !important;
  color: #C0CEDF !important;
  font-size: 13px !important;
  padding: 9px 14px !important;
  font-family: 'Space Grotesk', sans-serif !important;
  transition: background-color 0.1s ease !important;
}
.Select-option:hover, .Select-option.is-focused { background-color: #243348 !important; color: #E8EDF5 !important; }
.Select-option.is-selected { background-color: rgba(0,196,167,0.15) !important; color: #00C4A7 !important; font-weight: 600 !important; }
.VirtualizedSelectFocusedOption { background-color: #243348 !important; color: #E8EDF5 !important; }
.VirtualizedSelectSelectedOption { background-color: rgba(0,196,167,0.15) !important; color: #00C4A7 !important; }
.Select-value { background-color: #243348 !important; border-color: #2D3F5E !important; color: #E8EDF5 !important; border-radius: 4px !important; }
.Select-value-icon { color: #6B7FA0 !important; border-right-color: #2D3F5E !important; }
.Select-value-icon:hover { background-color: #EF4444 !important; color: #fff !important; border-radius: 4px 0 0 4px !important; }

/* ── Loading overlay ───────────────────────────────────── */
._dash-loading { opacity: 0.5; transition: opacity 0.2s ease; }
"""
