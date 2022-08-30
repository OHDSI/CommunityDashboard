import pandas as pd 
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from . import key_vault, pubmed_miner
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import ast

def get_author_names(items):
    output=""
    for item in items:
        output +=", " + item['firstname'] + " " + item['lastname']
    return output[1:]

def build_ehden_dash():
    results_container=pubmed_miner.init_cosmos('dashboard')
    query="SELECT * FROM c where c.id = 'ehden'"
    items = list(results_container.query_items(query=query, enable_cross_partition_query=True ))
    df=pd.DataFrame(items[0]['data'][1]['users'])
    df['year']=pd.to_numeric(df.year)
    df=df[df.year!=1970]
    df['number_of_users']=pd.to_numeric(df.number_of_users)
    bar_fig1=go.Figure()
    bar_fig1.add_trace(
        go.Bar(
            x=df.year,
            y=df.number_of_users,
            marker=dict(color = '#20425A'),
            showlegend=False
        )
    )
    bar_fig1.update_layout(
        title={
        'text': "Users by Year",
        'y':0.9,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'})
    bar_fig1.update_xaxes(type='category')

    df=pd.DataFrame(items[0]['data'][3]['completions'])
    df['year']=pd.to_numeric(df.year)
    df=df[df.year!=1970]
    df['completions']=pd.to_numeric(df.completions)
    bar_fig2=go.Figure()
    bar_fig2.add_trace(
        go.Bar(
            x=df.year,
            y=df.completions,
            marker=dict(color = '#20425A'),
            showlegend=False
        )
    )
    bar_fig2.update_layout(
        title={
        'text': "Course Completions by Year",
        'y':0.9,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'})
    bar_fig2.update_xaxes(type='category')
    bar_fig2.update_yaxes(range=[0,1500])


    df=pd.DataFrame(items[0]['data'][4]['course_stats'])


    df2=df.groupby('course_id').max().reset_index()
    df2['authors']=df2.teachers.apply(get_author_names)
    df2['course_started']=pd.to_datetime(df2.course_started)
    df2['course_fullname']=df2.apply(lambda row:"[{}](https://academy.ehden.eu/course/view.php?id={})".format(row.course_fullname,row.course_id),axis=1)
    df2['completions']=pd.to_numeric(df2.completions)
    df2['started']=pd.to_numeric(df2.started)
    df2=df2[df2.started!=0]
    df2.drop(['course_id','teachers'],axis=1,inplace=True)
    df2.sort_values('course_started',ascending=False,inplace=True)
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
                                            html.Div(children=
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(dcc.Graph(id='bar-fig1',figure=bar_fig1), width = 6),
                                        dbc.Col(dcc.Graph(id='bar-fig2',figure=bar_fig2), width = 6)
                                    ]
                                )
                            ]),
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
                    style_filter=[
                        {
                            'color': 'black',
                            'backgroundColor': '#20425A',
                            'font-family': 'Saira Extra Condensed'
                        }
                    ],
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