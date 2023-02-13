import dash
from dash import html, dcc
import pandas as pd

from plots.figures import ehden_course_completions
from plots.services.db import get_db

dash.register_page(__name__, '/plots/ehden-course-completions')

def layout(height="450px", width=None):
    if width:
        width = int(width)
    db = get_db()
    df = pd.DataFrame(db.find('ehden_course_completions'))
    fig = ehden_course_completions.figure(df, width)
    return html.Div(children=[dcc.Graph(
        id = 'bar-chart', 
        figure=fig,
        style={"height": height}
    )])
