import dash
from dash import html, dcc
import pandas as pd

from plots.figures import youtube_annual
from plots.services.db import get_db

dash.register_page(__name__, '/plots/youtube-annual')

def layout(height="450px", width=None):
    if width:
        width = int(width)
    db = get_db()
    df = pd.DataFrame(db.find('youtube'))
    fig = youtube_annual.figure(df, width)
    return html.Div(children=[dcc.Graph(
        id = 'bar-chart', 
        figure=fig,
        style={"height": height}
    )])