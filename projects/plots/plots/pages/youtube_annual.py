import dash
from dash import html, dcc

from plots.figures import youtube_annual
from plots.services import db

dash.register_page(__name__, '/plots/youtube-annual')

def layout(height="450px", width=None):
    if width:
        width = int(width)
    df, _ = db.get_youtube()
    fig = youtube_annual.figure(df, width)
    return html.Div(children=[dcc.Graph(
        id = 'bar-chart', 
        figure=fig,
        style={"height": height}
    )])