import dash
from dash import html, dcc

from plots.figures import youtube_monthly
from plots.services import db

dash.register_page(__name__, '/plots/youtube-monthly')

def layout(height="450px", width=None):
    if width:
        width = int(width)
    df = db.get_youtube_monthly()
    fig = youtube_monthly.figure(df, width)
    return html.Div(children=[dcc.Graph(
        id = 'bar-chart', 
        figure=fig,
        style={"height": height}
    )])