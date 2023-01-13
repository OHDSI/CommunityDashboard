import dash
from dash import html, dcc

from plots.figures import researchers
from plots.services import db

dash.register_page(__name__, '/plots/researchers')

def layout(height="450px", width=None):
    if width:
        width = int(width)
    df = db.get_researchers()
    fig = researchers.figure(df, width)
    return html.Div(children=[dcc.Graph(
        id = 'bar-chart', 
        figure=fig,
        style={"height": height}
    )])
