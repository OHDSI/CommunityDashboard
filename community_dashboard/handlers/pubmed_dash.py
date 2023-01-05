import dash_bootstrap_components as dbc
import ast
from dash import dcc, html, dash_table
from . import  pubmed_miner
import plotly.express as px
import pandas as pd 
import re

def build_pubs_dash():
    container_name='pubmed'
    container=pubmed_miner.init_cosmos(container_name)
    dateLastUpdated = pubmed_miner.getTimeOfLastUpdate()
    query = "SELECT * FROM c"
    items = list(container.query_items(
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
                    'Grant Funding':item['data']['grantNum'],
                    'Publication Year':item['data']['pubYear'],
                    'SNOMED Terms (n)':item['data']['termFreq']})
    df1=pd.DataFrame(data)   

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
    #([A-Z0-9]+[A-Z0-9\s\-\:_]+[0-9])([A-Z]?)
    df1['grantid']=""
    grantRegex = re.compile(r"([A-Z0-9]+[a-zA-Z0-9\s\-\:_]+[0-9][A-Z]?)")
    for i,row in df1.iterrows():
        if((row['Grant Funding'] == "nan") | (row['Grant Funding'] == "None")):
            df1.loc[i,'Grant Funding']= "None"
        else:
            grant_list=ast.literal_eval(row['Grant Funding'])
            # print(type(grant_list), grant_list)
            # grant_num = len(grant_list)
            grant_clean = ""
            for grant in grant_list:
                matchedStr = grantRegex.search(grant)
                if isinstance(matchedStr, type(None)) == False:
                    grant_clean = grant_clean + matchedStr.group() + "; "
            if grant_clean == "":
                grant_clean = grant_list[0]
            else:
                grant_clean = grant_clean[:-1]
            df1.loc[i,'Grant Funding']= grant_clean
            

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
    df1['SNOMED Terms (n)']=df1.apply(lambda row:"[{}](/abstracts?id={})".format(row['SNOMED Terms (n)'], row['PubMed ID']),axis=1)
    df1['Publication']=df1.apply(lambda row:"[{}](https://pubmed.gov/{})".format(row.Title,row['PubMed ID']),axis=1)
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

