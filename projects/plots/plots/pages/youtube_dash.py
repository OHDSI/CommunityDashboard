import dash
from dash import callback, Output, Input, dcc, html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

from plots.services import db
from plots.figures import youtube_annual, youtube_monthly

dash.register_page(__name__, '/youtube_dash')

def layout():
    """Builds Dash Dashboard for education page

    Returns:
        layout: object for Dash
    """
    
    df, dateCheckedOn = db.get_youtube()

    df2 = db.get_youtube_monthly()
    bar_fig2 = youtube_monthly.figure(df2)

    cols=['Title','Date Published','Length','Total Views','Recent Views', 'SNOMED Terms (n)']
    # del df_transcripts

    layout=html.Div(children=[
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000 # in milliseconds
                ),
                html.Div(
                    children=[
                    html.Br(),

                    html.H1("YouTube Analysis", 
                        style={
                            'font-family': 'Saira Extra Condensed',
                            'color': '#20425A',
                            'fontWeight': 'bold',
                            'text-align': 'center'

                        }
                    ),
                    html.Div(children=["Youtube Tracking leverages the Google YouTube Data API and \
                            highlights videos released across the OHDSI Youtube Channels. \
                            These videos are intended to serve two purposes: 1) \
                            provide users a great source of training on learning \
                            how to conduct observational research. 2) \
                            keep our community aware of the latest activities within our open science community. \
                            Searches for new videos are performed daily."], 
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
                                dbc.Col(html.Div(id='youtube-bar-container', children=[]), width = 6),
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
                    # dcc.Graph(id='videos',figure=fig), 
                    html.Div(children=[]),
                    dash_table.DataTable(
                        id = 'datatable-interactivity',
                        data = df.sort_values('Date Published',ascending=False).to_dict('records'), 
                        columns = [{"name": i, "id": i,'presentation':'markdown'} for i in cols],
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

@callback(
    Output(component_id='youtube-bar-container', component_property='children'),
    [Input(component_id='datatable-interactivity', component_property="derived_virtual_data"),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_selected_rows'),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_selected_row_ids'),
    Input(component_id='datatable-interactivity', component_property='selected_rows'),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_indices'),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_row_ids'),
    Input(component_id='datatable-interactivity', component_property='active_cell'),
    Input(component_id='datatable-interactivity', component_property='selected_cells')], prevent_initial_call=True
)
def youtubeupdate_bar(all_rows_data, slctd_row_indices, slct_rows_names, slctd_rows,
            order_of_rows_indices, order_of_rows_names, actv_cell, slctd_cell):
    df = pd.DataFrame(all_rows_data)
    fig = youtube_annual.figure(df)

    return [
        dcc.Graph(id = 'bar-chart', 
                    figure = fig,
                    style={'width': '100%', 'padding-left': '50px'},
                    )
                ]