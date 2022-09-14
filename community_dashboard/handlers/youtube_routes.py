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
import string
from community_dashboard.handlers import htmlBuilderFunctions

transcriptContainer = pubmed_miner.init_cosmos('transcripts')

@app.route('/transcripts', methods = ['GET'])
def transcripts():

    transcriptID = request.args.get('id', None)
    transcript = ''
    #query item with the search query
    for item in transcriptContainer.query_items( query='SELECT * FROM transcripts WHERE transcripts.id=@id',
            parameters = [{ "name":"@id", "value": transcriptID }], 
            enable_cross_partition_query=True):
        if(item['id'] == request.args.get('id', None)):
            if((isinstance(item['data'][0]['snomedNames'], type(None)) == False) & \
                (isinstance(item['data'][0]['umlsStartChar'], type(None)) == False) & \
                    ((((list(set(item['data'][0]['snomedNames']))[0] == "No Mapping Found") & (len(list(set(item['data'][0]['snomedNames']))) == 1)) == False)) ):
                    # (((len(item['data'][0]['snomedNames']) == 1 )& (item['data'][0]['snomedNames'][0] == "No Mapping Found")) == False)):
                # print(list(set(item['data'][0]['snomedNames']))[0])
                #get full transcript
                transcript = item['data'][0]['transcript']

                #identify list of meshterms
                lsTerms = []
                lsOccurenceTimes = []
                umlsTermsLength = len(item['data'][0]['umlsStartChar'])
                for i in range(0, umlsTermsLength):
                    if(item['data'][0]['snomedNames'][i] != "No Mapping Found"):

                        #extract the string from the transcript based on positions
                        start = int(item['data'][0]['umlsStartChar'][i])
                        end = int(item['data'][0]['umlsEndChar'][i]) - 1
                        targetString = transcript[start:end+1]
                        lsTerms = np.append(lsTerms, targetString)

                #highlight all instances
                for term in lsTerms:
                    transcript = re.sub((term + "|" + term.upper() + "|" + term.lower() + "|" + term.capitalize()), ('<mark>' + term + '</mark>'), transcript)
                
                # print(lsTerms)
                #find all the highlighted instances
                markStart = [i for i in range(len(transcript)) if transcript.startswith("<mark>", i)]
                markEnd = [i + 7 for i in range(len(transcript)) if transcript.startswith("</mark>", i)]
                for i in range(len(markStart)):
                    stringUptoTerm = transcript[0: markStart[i]]
                    #find number of words stripping of punctuations
                    strAsListWords = re.sub('['+string.punctuation+']', '', stringUptoTerm).split()
                    numWords = len(strAsListWords)
                    timeOccurred = "It might be around " + str(int(np.floor(((numWords / 150) * 60) / 60))) + " minute(s)" + " " + \
                                        str(int(np.floor(((numWords / 150) * 60) % 60))) + " second(s) ± 15 seconds"
                    lsOccurenceTimes = np.append(lsOccurenceTimes, timeOccurred)

                #underlilne is faulty
                addedLength = 0
                for i in range(len(markStart)):
                    strBeforeMark = transcript[0:markStart[i] + addedLength]
                    strWithinMark = transcript[markStart[i] + addedLength:markEnd[i] + addedLength]
                    strAfterMark = transcript[markEnd[i] + addedLength:len(transcript)]

                    transcript = strBeforeMark + " <div class='tooltip'> " + strWithinMark + \
                                    " <span class='tooltiptext'> " + lsOccurenceTimes[i] + "</span>" + \
                                        " </div> " + strAfterMark
                    addedLength = addedLength + len(" <div class='tooltip'>  <span class='tooltiptext'> " + lsOccurenceTimes[i] + "</span> </div> ")


                #occurrence time is faulty
                # for i in range(len(lsTerms)):
                #     pattern = ("<mark>" + lsTerms[i] + "</mark>" + "|" +\
                #                         "<mark>" + lsTerms[i].upper() + "</mark>" + "|" +\
                #                             "<mark>" + lsTerms[i].lower() + "<mark>" + "|" + \
                #                                 "<mark>" + lsTerms[i].capitalize() + "</mark>")
                #     transcript = re.sub(pattern, " <div class='tooltip'> " + ('<mark>' + lsTerms[i] + '</mark>') + \
                #                     " <span class='tooltiptext'> " + lsOccurenceTimes[i] + "</span>" + \
                #                         " </div> ", transcript)

                # print(lsOccurenceTimes)
                #fill out the rest of the html codes
                transcript = htmlBuilderFunctions.addTagWrapper(transcript, "body")
                #add style
                tooltipStyle = '<style> \
                                .tooltip { \
                                position: auto; \
                                display: inline-block;\
                                border-bottom: 1px dotted black;\
                                }\
                                .tooltip .tooltiptext {\
                                visibility: hidden;\
                                width: 120px;\
                                background-color: black;\
                                color: #fff;\
                                text-align: center;\
                                border-radius: 6px;\
                                padding: 5px 0;\
                                position: absolute;\
                                z-index: 1;\
                                }\
                                .tooltip:hover .tooltiptext {\
                                visibility: visible;\
                                }\
                                </style>'

                transcript = tooltipStyle + transcript
                transcript = htmlBuilderFunctions.addTagWrapper(transcript, "html")


                # del transcriptID
            else:
                transcript = "No SNOMED Terms Identified"
    if(transcript == ""):
        transcript = "To be updated soon..."
    return render_template_string(str(transcript))


@app.route('/youtube_dashboard/', methods = ['POST', 'GET'])
def dashboard_youtube():
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