"""The one chart look every Plotly figure in the app uses (see "Charts" in DESIGN.md)."""

import plotly.graph_objects as go

SERIES = ["#2563EB", "#F59E0B", "#8B5CF6", "#06B6D4"]  # same order as chartCategoricalColors in config.toml
GRID = "rgba(100,116,139,0.18)"  # translucent, so it reads on the light and the dark background
MUTED = "#64748B"

# Set as explicit layout, not a template: Streamlit swaps the template for its own theme (which handles
# light and dark text colours), but keeps layout values a figure sets itself.
LAYOUT = {
    "font": {"family": "Inter, system-ui, sans-serif", "size": 13},
    "title": {"x": 0, "xanchor": "left", "font": {"size": 15, "weight": 600}},
    "colorway": SERIES,
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "height": 320,
    "margin": {"t": 48, "b": 24, "l": 8, "r": 8},
    "legend": {"orientation": "h", "x": 0, "y": 1.02, "yanchor": "bottom", "title": None},
    "hovermode": "x unified",
    "bargap": 0.3,
}


def style(figure: go.Figure, tickformat: str = "", title: str | None = None) -> go.Figure:
    """Apply the shared look; tickformat (d3 format) is used for the y axis and the hover values."""
    figure.update_layout(LAYOUT)
    if title:
        figure.update_layout(title_text=title)
    figure.update_xaxes(showgrid=False, tickfont_color=MUTED, title_font_color=MUTED)
    figure.update_yaxes(
        gridcolor=GRID, zeroline=False, tickformat=tickformat, hoverformat=".1%" if tickformat.endswith("%") else tickformat,  # axis 20%, hover 24.3%
        tickfont_color=MUTED, title_font_color=MUTED,
    )
    return figure
