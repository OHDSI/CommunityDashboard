import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

from plots.services import db
from plots.figures import ehden_users, ehden_course_completions

dash.register_page(__name__, '/ehden_dash')

def layout():
    dateCheckedOn = db.getTimeOfLastUpdate()
    
    df = db.get_ehden_users()
    bar_fig1 = ehden_users.figure(df)

    df = db.get_ehden_course_completions()
    bar_fig2 = ehden_course_completions.figure(df)

    df2 = db.get_course_stats()
    layout=html.Div([
            dcc.Interval(
                id='interval-component',
                interval=1*1000 # in milliseconds
            ),
            html.Div(
                children=[
                html.Br(),
                html.Br(),
                html.Br(),
                html.H1("Ehden Learning Management System Analysis", 
                    style={
                        'font-family': 'Saira Extra Condensed',
                        'color': '#20425A',
                        'fontWeight': 'bold',
                        'text-align': 'center'
                    }
                ),
                html.Div(children=["Ehden Tracking leverages the Ehden Data API and \
                            highlights training resources on Ehden Academy. \
                            This page is intended to serve two purposes: 1) \
                            assess the background and skillset of the reseachers in OHDSI at large\
                            2) understand the needs of OHDSI researchers and what training are most sought after. "], 
                        style={
                            'width': '70%',
                            'margin-left': '15%',
                            'font-family': 'Saira Extra Condensed',
                            'color': '#20425A',
                            'fontSize': '14pt',
                            'text-align': 'center'

                        }
                    ),
                html.Div(children=
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(dcc.Graph(id='bar-fig1',figure=bar_fig1), width = 6),
                                        dbc.Col(dcc.Graph(id='bar-fig2',figure=bar_fig2), width = 6)
                                    ]
                                )
                            ]),
                # dcc.Graph(id='publications',figure=fig), 
                html.H6("Data as of: " + str(dateCheckedOn), 
                    style={
                        'font-family': 'Saira Extra Condensed',
                        'color': '#20425A',
                        'text-align': 'right'

                    }
                ),
                html.Div(),
                dash_table.DataTable(
                    id = 'datatable-interactivity',
                    data = df2.to_dict('records'), 
                    columns = [{"name": i, "id": i,'presentation':'markdown'} for i in df2.columns],
                    style_cell={
                        'height': 'auto',
                        # all three widths are needed
                        'minWidth': '10px', 'width': '10px', 'maxWidth': '250px',
                        'whiteSpace': 'normal',
                        'textAlign': 'left'
                    },
                    sort_action='native',
                    page_current=0,
                    page_size=20,
                    page_action='native',
                    filter_action='native',
                    sort_mode="single",         # sort across 'multi' or 'single' columns
                    column_selectable="multi",  # allow users to select 'multi' or 'single' columns
                    selected_columns=[],        # ids of columns that user selects
                    selected_rows=[],           # indices of rows that user selects
                    style_data={
                        'color': 'black',
                        'backgroundColor': 'white',
                        'font-family': 'Saira Extra Condensed'
                    },
                    style_filter={
                        'color': 'black',
                        'backgroundColor': '#20425A',
                        'font-family': 'Saira Extra Condensed'
                    },
                    style_header={
                        'font-family': 'Saira Extra Condensed',
                        'background-color': '#20425A',
                        'color': 'white',
                        'fontWeight': 'bold'
                    }
                )
                        
                ]
            )
        ])
    return layout