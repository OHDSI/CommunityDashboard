import datetime as date 
import numpy as np 
import pandas as pd 
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output, State
from flask import Flask, jsonify, render_template, request, render_template_string
from community_dashboard.handlers import youtube_miner, youtube_dash
from community_dashboard import app, youtubeDashApp
from community_dashboard.handlers import pubmed_miner, key_vault as kv
import re

transcriptContainer = pubmed_miner.init_cosmos('transcripts')

@app.route('/transcripts', methods = ['GET'])
def transcripts():
    # find and highlight all matching mesh terms in a new page 
    #example: http://127.0.0.1:5000/transcripts?id=5jZhZmzl0Co
    transcriptID = request.args.get('id', None)
    transcript = ''
    for item in transcriptContainer.query_items( query='SELECT * FROM transcripts', enable_cross_partition_query=True):
        if(item['id'] == request.args.get('id', None)):
            if((isinstance(item['data'][0]['meshTermspacy'], type(None)) == False)):
                transcript = item['data'][0]['transcript']
                listOfTerms = []
                #highlight all instances
                for i in range(0, len(item['data'][0]['startChar'])):
                    start = int(item['data'][0]['startChar'][i])
                    end = int(item['data'][0]['endChar'][i])
                    # print(transcript)
                    targetString = transcript[start:end+1]
                    listOfTerms = np.append(listOfTerms, targetString)
                for term in listOfTerms:
                    transcript = re.sub((term + "|" + term.upper() + "|" + term.lower() + "|" + term.capitalize()), ('<mark>' + term + '</mark>'), transcript)
                del transcriptID
            else:
                transcript = "No Mesh Terms Identified"
    return render_template_string(str(transcript))


@app.route('/youtube_dashboard/', methods = ['POST', 'GET'])
def dashboard_education():
    return render_template("youtube_dashboard.html")


@app.route('/youtube_dash', methods = ['POST', 'GET'])
def dash_app_education():
    return youtubeDashApp.index()


@youtubeDashApp.callback(
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
def youtubeupdate_bar(all_rows_data, slctd_row_indices, slct_rows_names, slctd_rows,
            order_of_rows_indices, order_of_rows_names, actv_cell, slctd_cell):
    df = pd.DataFrame(all_rows_data)
    df=df[df.channelTitle.str.startswith('OHDSI')].copy(deep=True)
    # print(df['Length'])
    df['Duration'] = df.apply(lambda x: int(x['Length'][0:2]) * 3600 + \
                                int(x['Length'][3:5]) * 60 + \
                                    int(x['Length'][6:8]), axis = 1)

    from plotly.subplots import make_subplots
    import plotly.graph_objects as go
    # fig = make_subplots(rows=1, cols=2,
    #                     subplot_titles=("Youtube Hours Created","Cumulative Hrs Watched"))
    df4=df.groupby('yr').Duration.sum().reset_index()
    df4.columns=['Year','SumSeconds']
    # df4['Hrs Created']=df4['SumSeconds'].dt.days*24 + df4['SumSeconds'].dt.seconds/3600
    df4['Hrs Created']=df4['SumSeconds']/3600
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add traces
    fig.add_trace(
        go.Bar(
            x=df4['Year'],
            y=df4['Hrs Created'],
            marker=dict(color = '#20425A'),
            hovertemplate =
                '<i>%{x}</i>: %{y:.0f} hours of content created <extra></extra>',
            showlegend = False
            
            ), 
        secondary_y=False,
    )
    # df['hrsWatched']=(df.Duration.dt.days*24+df.Duration.dt.seconds/3600)*df['Total Views']
    df4=df.groupby('yr').hrsWatched.sum().reset_index()
    df4.columns=['Year','HrsWatched']
    df4['Cumulative Hrs Watched']= np.round(df4['HrsWatched'].cumsum(), 0)
    # df4['Cumulative Hrs Watched'] = df4['Cumulative Hrs Watched'].apply(lambda x :int(x))
    # df4['Cumulative Hrs Watched'] = df4['Cumulative Hrs Watched'].apply(lambda x : "{:,}".format(x))
    fig.add_trace(
        go.Line(
            x=df4['Year'],
            y=df4['Cumulative Hrs Watched'],
            marker=dict(color = '#f6ac15'),
            hovertemplate =
                '<i>%{x}</i>: %{y} hours of video watched <extra></extra>'

            ),
            
        secondary_y='Secondary'
    )
    # Add figure title
    fig.update_layout(title_text="<b> YouTube Analysis </b>", title_x=0.5, showlegend=False)
    # Set x-axis title
    fig.update_xaxes(title_text="Year")
    # Set y-axes titles
    fig.update_yaxes(
        title_text="Content Hours Created", 
        secondary_y=False)
    fig.update_yaxes(
        title_text="Cumulative Hours Watched", 
        secondary_y=True)

    return [
        dcc.Graph(id = 'bar-chart', 
                    figure = fig.update_layout(yaxis={'tickformat': '{:,}'}),
                    style={'width': '100%', 'padding-left': '50px'},
                    )
                ]