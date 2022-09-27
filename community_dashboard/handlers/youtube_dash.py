from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from . import pubmed_miner
import plotly.express as px
import pandas as pd 
import numpy as np
from datetime import datetime, date
import plotly.graph_objects as go

import time

def convert_time(time_str):
    """Takes time values from Youtube duration
        '8M12S' or '3H10M5S' 
    """
    import datetime,time
    #Strip PT from string (Period Time)
    time_str=time_str[2:]
    filter=''
    filter_list=['H','M','S']
    for filter_item in filter_list:
        if filter_item in time_str:
            filter+='%'+filter_item*2
    ntime=time.strptime(time_str,filter)
    return datetime.timedelta(hours=ntime.tm_hour,minutes=ntime.tm_min,seconds=ntime.tm_sec)


def build_education_dash():
    """Builds Dash Dashboard for education page

    Returns:
        layout: object for Dash
    """
    
    container_name='youtube'
    # container_name='pubmed_test'
    container=pubmed_miner.init_cosmos(container_name)
    # container_transcripts=pubmed_miner.init_cosmos("transcripts")
    query = "SELECT * FROM c"
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    startTime = time.time()
    # transcript_items = list(container_transcripts.query_items(
    #     query=query,
    #     enable_cross_partition_query=True
    # ))
    

    videos=[]
    transcriptsDict = []
    dateCheckedOn = pubmed_miner.getTimeOfLastUpdate()
    for item in items:
        #Review the log of counts and find the last two and subtract them for recent views
        df=pd.DataFrame(item['counts']).sort_values('checkedOn',ascending=False).reset_index()
        # dateCheckedOn = str(date.today().replace(day=1))
        # dateCheckedOn = dateCheckedOn[5:len(dateCheckedOn)] + dateCheckedOn[4:5] + dateCheckedOn[0:4]
        total_views=int(df.viewCount[0])
        if len(df)==1:
            recent_views=int(df.viewCount[0])
        else:
            recent_views=int(df.viewCount[0])-int(df.viewCount[1])
        videos.append({'id':item['id'],
                    'Title':item['title'],
                    # 'Duration':convert_time(item['duration']),
                    'Duration':item['duration'],
                    'Date Published':pd.to_datetime(item['publishedAt']),
                    'Total Views':total_views,
                    'Recent Views':recent_views,
                    'channelTitle':item['channelTitle'], 
                    'SNOMED Terms (n)': item['termFreq']}
                    )
    df=pd.DataFrame(videos)
    endTime = time.time()
    print(endTime - startTime)
    # for transcript in container_transcripts.query_items(
    #     query=query,
    #     enable_cross_partition_query=True
    # ):
    #     transcriptsDict.append({
    #         'id':transcript['id'],
    #         'SNOMED Terms (n)':transcript['data'][0]['termFreq'],

    #     })
    # df_transcripts = pd.DataFrame(transcriptsDict) 
    # df_transcripts['SNOMED Terms'] = df_transcripts.apply(lambda x: ([i for i in x['SNOMED Terms'] if ((i != "No Mapping Found") & (i != "Sodium-22"))]), axis = 1)
    # df_transcripts['SNOMED Terms'] = df_transcripts.apply(lambda x: "No Mapping Found" if len(x['SNOMED Terms']) == 0 else x['SNOMED Terms'], axis = 1)
    # df_transcripts['SNOMED Terms'] = df_transcripts.apply(lambda x: "No Mapping Found" if x['SNOMED Terms'] == '' else x['SNOMED Terms'], axis = 1)
    

    df=df[df.channelTitle.str.startswith('OHDSI')].copy(deep=True)
    # df['Duration'] = df.apply(lambda x: str(x['Duration'])[2:], axis = 1)
    df['Duration'] = df.apply(lambda x: convert_time(x['Duration']), axis = 1)
    df['yr']=df['Date Published'].dt.year
    
    df['hrsWatched']=(df.Duration.dt.days*24+df.Duration.dt.seconds/3600)*df['Total Views']

    results_container=pubmed_miner.init_cosmos('dashboard')
    query="SELECT * FROM c where c.id = 'youtube_monthly'"
    items = list(results_container.query_items(query=query, enable_cross_partition_query=True ))
    df2=pd.read_json(items[0]['data'])
    df2['Date']=pd.to_datetime(df2['Date']).dt.strftime('%Y-%m')
    bar_fig2=go.Figure()
    bar_fig2.add_trace(
        go.Bar(
            x=df2['Date'],
            y=df2['Count'],
            marker=dict(color = '#20425A'),
            showlegend=False
        )
    )
    bar_fig2.update_layout(
        title={
        'text': "<b>Hours Viewed for each month</b>",
        'y':0.9,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'})
    bar_fig2.update_xaxes(type='category')

    # DataTable Prep
    df['Date Published']=df['Date Published'].dt.strftime('%Y-%m-%d')
    # df['Title']=df.apply(lambda row:"[{}](https://www.youtube.com/watch?v={})".format(row.Title,row.id),axis=1)
    df['Title']=df.apply(lambda row:"[{}](https://www.youtube.com/watch?v={})".format(row.Title,row.id),axis=1)
    df['Length'] = df.apply(lambda x: str(x['Duration'])[7:], axis = 1)
    # del df['Duration']
    # fig.update_layout( title_text="Youtube Video Analysis", showlegend=False)
    # df = pd.merge(df, df_transcripts, how = 'left', left_on= 'id', right_on = 'id')
    df['SNOMED Terms (n)']=df.apply(lambda row:"[{}](/transcripts?id={})".format(row['SNOMED Terms (n)'], row.id),axis=1)
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
                            keep our community aware of the latest activities within our open science community."], 
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
                                dbc.Col(html.Div(id='bar-container', children=[]), width = 6),
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