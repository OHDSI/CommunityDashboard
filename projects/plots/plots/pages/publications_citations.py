import dash
from dash import html, dcc

from plots.figures import publications_citations
from plots.services import db

dash.register_page(__name__, '/plots/publications-citations')

def layout(height="450px", width=None):
    if width:
        width = int(width)
    df = db.get_publications()
    fig = publications_citations.figure(df, width)
    return html.Div(children=[dcc.Graph(
        id = 'bar-chart', 
        figure=fig,
        style={"height": height}
    )])
