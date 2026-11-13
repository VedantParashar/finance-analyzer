import plotly.graph_objects as go

from finance_analyzer import charts


def test_style_gives_every_chart_the_same_look_and_formats_hover_values():
    figure = charts.style(go.Figure(go.Scatter(x=[1, 2], y=[0.1, 0.2])), ".0%", "Margins")
    assert figure.layout.font.family.startswith("Inter") and figure.layout.title.text == "Margins"
    assert list(figure.layout.colorway) == charts.SERIES and figure.layout.hovermode == "x unified"
    assert (figure.layout.yaxis.tickformat, figure.layout.yaxis.hoverformat) == (".1~%", ".1%")
    assert figure.layout.xaxis.showgrid is False
    amounts = charts.style(go.Figure(go.Bar(x=[1], y=[5])), "$,.0f")
    assert amounts.layout.yaxis.hoverformat == "$,.0f"
