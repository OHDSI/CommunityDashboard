from tkinter import E
import dash
import dash_bootstrap_components as dbc
import ast
from dash import dcc, html, dash_table
from . import key_vault, pubmed_miner
import plotly.express as px
import pandas as pd 


def build_pubs_dash():
    container_name='pubmed'
    container_for_author_data='pubmed_author'
    key_dict = key_vault.get_key_dict()
    container=pubmed_miner.init_cosmos(key_dict, container_name)
    container_author_data=pubmed_miner.init_cosmos(key_dict, container_for_author_data)

    query = "SELECT * FROM c"
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    author_items = list(container_author_data.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    data=[]
    for item in items:
        t=0
        for citations in item['data']['trackingChanges']:
            if citations['t']>t:
                t=citations['t']
                citation_count=citations['numCitations']
        data.append({'PubMed ID':item['data']['pubmedID'],
                    'Creation Date':item['data']['creationDate'],
                    'Citation Count':citation_count,
                    'First Authors':item['data']['firstAuthor'],
                    'Authors':item['data']['fullAuthor'],
                    'Title':item['data']['title'],
                    'Journal':item['data']['journalTitle'],
                    'Publication Year':item['data']['pubYear'],
                    'MeSH Terms':item['data']['meshT']})
    df1=pd.DataFrame(data)   

    # authorData=[]
    # for item in author_items:
    #     authorData.append({'Year':item['authorSummary']['pubYear'],
    #                 'First Author Names':item['authorSummary']['uniqueFirstAuthors'],
    #                 'New First Authors':item['authorSummary']['numberNewFirstAuthors'],
    #                 'Total First Authors':item['authorSummary']['cumulativeFirstAuthors'],
    #                 "New Authors' Names":item['authorSummary']['uniqueAuthors'],
    #                 'All New Authors':item['authorSummary']['numberNewAuthors'],
    #                 'Total Authors':item['authorSummary']['cumulativeAuthors']})

    #parse authors to set a limit on authors shown n_authors
    df1['authors']=""
    n_authors=3
    for i,row in df1.iterrows():
        authors=ast.literal_eval(row['Authors'])
        auth_list=""
        if len(authors)>n_authors:
            for j in range(n_authors):
                auth_list+="{}, ".format(authors[j].replace(',',''))
            auth_list += "+ {} authors, ".format(len(authors)-n_authors)
            auth_list += "{} ".format(authors[-1].replace(',',''))
        else:
            for auth in authors:
                auth_list+="{}, ".format(auth.replace(',',''))
            auth_list=auth_list[:-2]
        df1.loc[i,'Authors']=auth_list

    for i,row in df1.iterrows():
        meshTerms = row['MeSH Terms'].replace("]", "")
        meshTerms = meshTerms.replace("[", "")
        meshList = meshTerms.split(",")
        # terms=ast.literal_eval(meshTerms)
        term_list=""
        for term in meshList:
            term_list+= term + ", "
        term_list = term_list.replace("'", "")
        term_list = term_list.replace("*", "")
        term_list=term_list[:-2]
        if(term_list == "nan"):
            df1.loc[i,'MeSH Terms']= "Not Yet Available"
        else:
            df1.loc[i,'MeSH Terms']=term_list

    df1['Creation Date']=df1['Creation Date'].str[:-6]
    df2=df1.groupby('Publication Year')['PubMed ID'].count().reset_index()
    df2.columns=['Year','Count']
    bar_fig=px.bar(
        data_frame=df2,
        x="Year",
        y='Count',
        title="OHDSI Publications")
    df3=df1.groupby('Publication Year')['Citation Count'].sum().reset_index()
    df3['cumulative']=df3['Citation Count'].cumsum()
    df3.columns=['Year','citations','Count']
    line_fig=px.line(
        data_frame=df3,
        x='Year',
        y='Count',
        title="OHDSI Cumulative Citations")
        
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go
    # fig = make_subplots(rows=1, cols=2,
    #                     subplot_titles=("<b> Publications </b>","<b> Cumulative Citations </b>"))
    # fig.add_trace(
    #     go.Bar(
    #     x=df2['Year'],
    #     y=df2['Count'],
    #     marker=dict(color = '#20425A')),
    #     row=1, col=1
    #     )
    # fig.add_trace(
    #     go.Line(
    #     x=df3['Year'],
    #     y=df3['Count'],
    #     marker=dict(color = '#20425A')),
    #     row=1, col=2
    #     )
    # fig.update_layout(showlegend=False, font_family="Saira Extra Condensed")
    df1['Publication']=df1.apply(lambda row:"[{}](http://pubmed.gov/{})".format(row.Title,row['PubMed ID']),axis=1)
    cols=['PubMed ID', 'Creation Date','Authors','Publication','Journal','MeSH Terms', 'Citation Count']
    layout= html.Div([
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000 # in milliseconds
                ),
                html.Div(
                    
                    children=[
                            # html.Div(dcc.Input(id='input-on-submit', type='text', value = "")),
                            # html.Button('Add Article', id='submit-val'),
                            # html.Div(id='container-button-basic',
                            #         children='Enter article PubMed ID or name'),
                            html.Br(),
                            html.Br(),
                            html.Br(),
                            html.H1("Publication Analysis", 
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
                                        dbc.Col(html.Div(id='bar-container'), width = 6),
                                        dbc.Col(html.Div(id='line-container'), width = 6)
                                    ]
                                )
                            ]),
                            
                            
                            # dcc.Graph(id='publications',figure=fig), 
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
                            
                    ], style={'padding-top': '0px', 'overflow-y': 'hidden'}
                )
            ])
    return layout

