import dash
from dash import callback, Output, Input, dcc, html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from plots.services import db
from plots.figures import publications_citations, researchers

dash.register_page(__name__, '/pub_dash')

def layout():
    dateLastUpdated = db.getTimeOfLastUpdate()
    df1 = db.get_publications()
    cols=['PubMed ID', 'Creation Date','Authors','Publication','Journal', 'Grant Funding', 'SNOMED Terms (n)', 'Citation Count']
    layout= html.Div([
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000 # in milliseconds
                ),
                html.Div(
                    
                    children=[
                            html.Br(),

                            html.H1("Publication Analysis", 
                                style={
                                    'font-family': 'Saira Extra Condensed',
                                    'color': '#20425A',
                                    'fontWeight': 'bold',
                                    'text-align': 'center'

                                }
                            ),
                            html.Div("PubMed Publication Tracking highlights scholarship generated \
                                    using the OMOP Common Data Model, OHDSI tools, or the OHDSI network. \
                                    These publications represent scientific accomplishments across areas of \
                                    data standards, methodological research, open-source development, \
                                    and clinical applications. We provide the resource \
                                    to search and browse the catalogue of OHDSI-related publications by date, \
                                    author, title, journal, and SNOMED terms. We monitor the impact of our community \
                                    using summary statistics (number of publications and citations), \
                                    and the growth and diversity of our community with the number of \
                                    distinct authors. Searches for new papers are performed daily, and \
                                    citation counts are updated monthy.", 
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
                                        dbc.Col(html.Div(id='bar-container'), width = 6),
                                        dbc.Col(html.Div(id='line-container'), width = 6)
                                    ]
                                )
                            ]),
                            
                            
                            # dcc.Graph(id='publications',figure=fig), 
                            html.H6("Data as of: " + str(dateLastUpdated), 
                                style={
                                    'font-family': 'Saira Extra Condensed',
                                    'color': '#20425A',
                                    'text-align': 'right'

                                }
                            ),
                            html.Div(id='my-output'),
                            dash_table.DataTable(
                                id='datatable-interactivity',
                                data = df1.sort_values('Creation Date',ascending=False).to_dict('records'), 
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
                            
                            
                    ], style={'padding-top': '0px', 'overflow-y': 'hidden'}
                )
            ])
    return layout



@callback(
    Output(component_id='bar-container', component_property='children'),
    [Input(component_id='datatable-interactivity', component_property="derived_virtual_data"),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_selected_rows'),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_selected_row_ids'),
    Input(component_id='datatable-interactivity', component_property='selected_rows'),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_indices'),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_row_ids'),
    Input(component_id='datatable-interactivity', component_property='active_cell'),
    Input(component_id='datatable-interactivity', component_property='selected_cells')], prevent_initial_call=True
)
def update_bar(all_rows_data, slctd_row_indices, slct_rows_names, slctd_rows,
            order_of_rows_indices, order_of_rows_names, actv_cell, slctd_cell):
    dff = pd.DataFrame(all_rows_data)
    fig = publications_citations.figure(dff)
    return [
        dcc.Graph(id = 'bar-chart', 
                figure=fig,
                style={'width': '100%', 'padding-left': '50px'},
                )
        ]

@callback(
    Output(component_id='line-container', component_property='children'),
    [Input(component_id='datatable-interactivity', component_property="derived_virtual_data"),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_selected_rows'),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_selected_row_ids'),
    Input(component_id='datatable-interactivity', component_property='selected_rows'),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_indices'),
    Input(component_id='datatable-interactivity', component_property='derived_virtual_row_ids'),
    Input(component_id='datatable-interactivity', component_property='active_cell'),
    Input(component_id='datatable-interactivity', component_property='selected_cells')], prevent_initial_call=True
)
def update_author_bar(all_rows_data, slctd_row_indices, slct_rows_names, slctd_rows,
            order_of_rows_indices, order_of_rows_names, actv_cell, slctd_cell):

    currentAuthorSummaryTable = db.get_researchers()
    fig = researchers.figure(currentAuthorSummaryTable)

    return [
        dcc.Graph(id = 'bar-chart', 
                    figure = fig,
                    style={'width': '100%', 'padding-left': '50px'},
                    )
            ]