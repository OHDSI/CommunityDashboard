import datetime as date  
import pandas as pd 
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output, State
from flask_session import Session
from flask import Flask, jsonify, render_template, request
from azure.cosmos import CosmosClient, PartitionKey
import re
import numpy as np
import string
import ast
from community_dashboard.handlers import htmlBuilderFunctions
from flask import Flask, jsonify, render_template, request, render_template_string

from community_dashboard import app, pubmedDashApp
from community_dashboard.handlers import pubmed_miner
from community_dashboard.config import Keys


container = pubmed_miner.init_cosmos('pubmed')
container_ignore = pubmed_miner.init_cosmos('pubmed_ignore')

@app.route('/publication_dashboard/', methods = ['POST', 'GET'])
def dashboard():
    # dashHtml = BeautifulSoup(pubmedDashApp.index(), 'html.parser')
    return render_template("publication_dashboard.html")
    # return jsonify({'htmlresponse': render_template('publication_dashboard.html', dashHtml = pubmedDashApp)})


@app.route('/pub_dash', methods = ['POST', 'GET'])
def dash_app_pub():
    return pubmedDashApp.index()

@pubmedDashApp.callback(
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
    df2=((dff.groupby('Publication Year')['PubMed ID']).count()).reset_index()
    df2.columns=['Year','Count']
    df3=((dff.groupby('Publication Year')['Citation Count']).sum()).reset_index()
    df3['cumulative']= round(df3['Citation Count'].cumsum(), 0) 
    df3.columns=['Year','citations','Count']
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Add traces
    fig.add_trace(
        go.Bar(
            x=df2['Year'],
            y=df2['Count'],
            marker=dict(color = '#20425A'),
            hovertemplate =
                '<i>Publications in %{x}</i>: %{y:.0f}<extra></extra>',
            showlegend = False
            
            ), 
        secondary_y=False,
    )

    fig.add_trace(
        go.Line(
            x=df3['Year'],
            y=df3['Count'],
            marker=dict(color = '#f6ac15'),
            hovertemplate =
                '<i>Citations in %{x}</i>: %{y} <extra></extra>',
            ),
        secondary_y='Secondary'
    )

    # Add figure title
    fig.update_layout(title_text="<b> OHDSI Publications & Cumulative Citations</b>", title_x=0.5, showlegend=False)
    # Set x-axis title
    fig.update_xaxes(title_text="Year")
    # Set y-axes titles
    fig.update_yaxes(
        title_text="Number of Publications", 
        secondary_y=False)
    fig.update_yaxes(
        title_text="Number of Citations", 
        secondary_y=True)

    return [
        dcc.Graph(id = 'bar-chart', 
                    figure = fig.update_layout(yaxis={'tickformat': '{:,}'}),
                    style={'width': '100%', 'padding-left': '50px'},
                    )
            ]


@pubmedDashApp.callback(
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
    #currentAuthorSummaryTable = pubmed_miner.retrieveAuthorSummaryTable('pubmed_author')
    results_container=pubmed_miner.init_cosmos('dashboard')
    query="SELECT * FROM c where c.id = 'pubmed_authors'"
    items = list(results_container.query_items(query=query, enable_cross_partition_query=True ))
    currentAuthorSummaryTable=pd.read_json(items[0]['data'])
    currentAuthorSummaryTable = currentAuthorSummaryTable[['pubYear', 'numberNewFirstAuthors', 'cumulativeFirstAuthors', 'numberNewAuthors', 'cumulativeAuthors']]
    currentAuthorSummaryTable.columns = ['Year', 'New First Authors', 'Total First Authors', 'All New Authors', 'Total Authors']

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Add traces
    fig.add_trace(
        go.Bar(
            x=currentAuthorSummaryTable['Year'],
            y=currentAuthorSummaryTable['All New Authors'],
            marker=dict(color = '#20425A'),
            hovertemplate =
                '<i>New Authors in %{x}</i>: %{y:.0f}<extra></extra>',
            showlegend = False
            
            ), 
        secondary_y=False,
    )

    fig.add_trace(
        go.Line(
            x=currentAuthorSummaryTable['Year'],
            y=currentAuthorSummaryTable['Total Authors'],
            marker=dict(color = '#f6ac15'),
            hovertemplate =
                '<i>Cumulative Authors by %{x}</i>: %{y} <extra></extra>',
            ),
        secondary_y='Secondary'
    )

    # Add figure title
    fig.update_layout(title_text="<b> New and Cumulative OHDSI Researchers</b>", title_x=0.5, showlegend=False)
    # Set x-axis title
    fig.update_xaxes(title_text="Year")
    # Set y-axes titles
    fig.update_yaxes(
        title_text="Number of New Authors", 
        secondary_y=False)
    fig.update_yaxes(
        title_text="Number of Cumulative Authors", 
        secondary_y=True)

    return [
        dcc.Graph(id = 'bar-chart', 
                    figure = fig.update_layout(yaxis={'tickformat': '{:,}'}),
                    style={'width': '100%', 'padding-left': '50px'},
                    )
            ]


pubmedContainer = pubmed_miner.init_cosmos('pubmed')


@app.route('/abstracts', methods = ['GET'])
def abstracts():
    pubmedID = "PMID: " + str(int(float(request.args.get('id', None))))
    abstract = ''
    #query item with the search query
    for item in pubmedContainer.query_items( query='SELECT * FROM pubmed WHERE pubmed.id=@id',
            parameters = [{ "name":"@id", "value": pubmedID }], 
            enable_cross_partition_query=True):
        if(item['id'] == pubmedID):
            snomedNamesStr = item['data']['snomedNames'].strip('][')
            snomedNames = re.split("', '|\n", snomedNamesStr[1:-1])
            umlsStartChar = item['data']['umlsStartChar'].strip('][').split('. ')
            umlsEndChar = item['data']['umlsEndChar'].strip('][').split('. ')
            if(item['data']['abstract'] == 'TranscriptsDisabled'):
                abstract = 'Transcripts Disabled. Please check back later...'
            elif((isinstance(snomedNames, type(None)) == False) & \
                (isinstance(umlsStartChar, type(None)) == False) & \
                    ((((list(set(snomedNames))[0] == "No Mapping Found") & (len(list(set(snomedNames))) == 1)) == False)) & \
                        ((((list(set(snomedNames))[0] == 'Sodium-22') & (len(list(set(snomedNames))) == 1)) == False)) ):
                    # (((len(snomedNames) == 1 )& (snomedNames[0] == "No Mapping Found")) == False)):
                # print(list(set(snomedNames))[0])
                #get full transcript
                abstract = item['data']['abstract']
                #identify list of meshterms
                lsTerms = []
                lsOccurenceTimes = []
                umlsTermsLength = len(umlsStartChar)
                for i in range(0, umlsTermsLength):
                    if(umlsStartChar[i] != 'NA'):
                            #extract the string from the transcript based on positions
                            
                            start = int(float(umlsStartChar[i]))
                            end = int(float(umlsEndChar[i])) - 1
                            targetString = abstract[start:end+1]
                            lsTerms = np.append(lsTerms, targetString)

                #highlight all instances
                for term in lsTerms:
                    abstract = re.sub((term + "|" + term.upper() + "|" + term.lower() + "|" + term.capitalize()), ('<mark>' + term + '</mark>'), abstract)
                
                # print(lsTerms)
                #find all the highlighted instances
                markStart = [i for i in range(len(abstract)) if abstract.startswith("<mark>", i)]
                markEnd = [i + 7 for i in range(len(abstract)) if abstract.startswith("</mark>", i)]
                for i in range(len(markStart)):
                    stringUptoTerm = abstract[0: markStart[i]]
                    #find number of words stripping of punctuations
                    strAsListWords = re.sub('['+string.punctuation+']', '', stringUptoTerm).split()
                    numWords = len(strAsListWords)
                    timeOccurred = "It might be around " + str(int(np.floor(((numWords / 150) * 60) / 60))) + " minute(s)" + " " + \
                                        str(int(np.floor(((numWords / 150) * 60) % 60))) + " second(s) ± 15 seconds"
                    lsOccurenceTimes = np.append(lsOccurenceTimes, timeOccurred)

                #underlilne is faulty
                addedLength = 0
                for i in range(len(markStart)):
                    strBeforeMark = abstract[0:markStart[i] + addedLength]
                    strWithinMark = abstract[markStart[i] + addedLength:markEnd[i] + addedLength]
                    strAfterMark = abstract[markEnd[i] + addedLength:len(abstract)]

                    abstract = strBeforeMark + " <div class='tooltip'> " + strWithinMark + \
                                    " <span class='tooltiptext'> " + lsOccurenceTimes[i] + "</span>" + \
                                        " </div> " + strAfterMark
                    addedLength = addedLength + len(" <div class='tooltip'>  <span class='tooltiptext'> " + lsOccurenceTimes[i] + "</span> </div> ")


                #occurrence time is faulty
                # for i in range(len(lsTerms)):
                #     pattern = ("<mark>" + lsTerms[i] + "</mark>" + "|" +\
                #                         "<mark>" + lsTerms[i].upper() + "</mark>" + "|" +\
                #                             "<mark>" + lsTerms[i].lower() + "<mark>" + "|" + \
                #                                 "<mark>" + lsTerms[i].capitalize() + "</mark>")
                #     abstract = re.sub(pattern, " <div class='tooltip'> " + ('<mark>' + lsTerms[i] + '</mark>') + \
                #                     " <span class='tooltiptext'> " + lsOccurenceTimes[i] + "</span>" + \
                #                         " </div> ", abstract)

                # print(lsOccurenceTimes)
                #fill out the rest of the html codes
                abstract = htmlBuilderFunctions.addTagWrapper(abstract, "body")
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

                abstract = tooltipStyle + abstract
                abstract = htmlBuilderFunctions.addTagWrapper(abstract, "html")


                # del abstractID
            else:
                abstract = "No SNOMED Terms Identified"
    if(abstract == ""):
        abstract = "To be updated soon..."
    return render_template_string(str(abstract))
            
@app.route('/articleManager')
def articleManager():
    # count = 0
    # countIgnore = 0
    # listHolder = []
    # listHolderIgnore = []
    # for item in container.query_items( query='SELECT * FROM pubmed', enable_cross_partition_query=True):
    #     count += 1
    #     listHolder.append(item['data']['title'])
    
    # for item in container_ignore.query_items( query='SELECT * FROM pubmed_ignore', enable_cross_partition_query=True):
    #     countIgnore += 1
    #     listHolderIgnore.append(item['data']['title'])
    # return render_template("index.html",articles=listHolder )
    # if Keys['PASS_KEY']!=request.args.get('pass_key'):
    #     return "Not authorized to access this page"
    return render_template("articleManager.html")

# @app.route("/fetchrecords",methods=["POST","GET"])
# def fetchrecords():
#     if Keys['PASS_KEY']!=request.args.get('pass_key'):
#         return "Not authorized to access this page"
#     count = 0
#     listHolder = []
#     if request.method == 'POST':
#         query = request.form['query']

#         if(query == ''):
#             for item in container.query_items( query='SELECT * FROM pubmed ORDER BY pubmed.data.pubYear DESC', enable_cross_partition_query=True):
#                 count += 1
#                 listHolder.append(item['data'])

#         elif((query != '') ):
#             search_text = "%" + request.form['query'] + "%"
#             for item in container.query_items( 'SELECT * FROM pubmed WHERE ((LOWER(pubmed.data.title) LIKE LOWER(@searchStr)) or \
#                                                                             (LOWER(pubmed.id) LIKE @searchStr) or \
#                                                                                 (LOWER(pubmed.data.firstAuthor) LIKE LOWER(@searchStr)) ) ORDER BY pubmed.data.pubYear DESC',
#                                                 [{"name": "@searchStr", "value": search_text}], enable_cross_partition_query=True
#                                                 ):
#                 count += 1
#                 listHolder.append(item['data'])
#     # return jsonify("success")
#     return jsonify({'htmlresponse': render_template('response.html', articleList=listHolder, numArticle = count)})


@app.route("/insert",methods=['POST'])
def insert():
    if(request.method):
        # print(request.form.keys())
        print(request.form['passKeyHiddenInsert'])
        # if Keys['PASS_KEY']!=request.args.get('pass_key'): #Need to add hidden field for POST condition
        #     return "Not authorized to access this page"
        dateMY = "" + date.datetime.now().strftime("%m-%d-%Y")[0:2] + date.datetime.now().strftime("%m-%d-%Y")[5:10]
        if((request.method == 'POST') & (Keys['PASS_KEY']!= request.form['passKeyHiddenInsert'])):
            return "Not authorized to access this page"
        elif ((request.method == 'POST') & (Keys['PASS_KEY']== request.form['passKeyHiddenInsert'])) :
            
            searchArticles = request.form['articleIdentifier']
            designatedContainer = request.form['containerChoice']
            numNewArticles = 0
            containerArticles = pubmed_miner.getExistingIDandSearchStr(designatedContainer)

            secret_api_key = Keys['SERPAPI_KEY'] #SERPAPI key
            articleTable = pubmed_miner.getPMArticles(searchArticles)
            # articleTable = articleTable[articleTable['pubYear'] > 2010]
            try:
                specifiedArticle = articleTable['pubmedID'][0]
            except KeyError:
                return jsonify("This article may not be officially available in the system yet. Check back again...")
            else:

                specifiedArticle = articleTable['pubmedID'][0]
                articleTable = articleTable[articleTable.pubmedID.notnull()]
                articleTable, numNewArticles = pubmed_miner.identifyNewArticles(articleTable)

                if(numNewArticles == 0):
                    if(specifiedArticle in containerArticles[0]):
                        return jsonify("This article already exists in the '" + str(designatedContainer) + "' container. Please verify." )
                    else:
                        return jsonify("This article already exists in the other container. Please verify." )
                else:
                    #search google scholar and create 4 new columns
                    articleTable[['foundInGooScholar', 'numCitations', 'levenProb', 'fullAuthorGooScholar', 'googleScholarLink']] = articleTable.apply(lambda x: pubmed_miner.getGoogleScholarCitation(x, secret_api_key), axis = 1, result_type='expand')
                    articleTable = articleTable.reset_index()
                    if ('index' in articleTable.columns):
                        del articleTable['index']
                    if ('level_0' in articleTable.columns):
                        del articleTable['level_0']
                        
                    newArticlesTable, numNewArticles = pubmed_miner.identifyNewArticles(articleTable)
                    if(numNewArticles > 0):
                        #NER and mapping of abstracts to SNOMED
                        newArticlesTable = pubmed_miner.scispacyOntologyNER(newArticlesTable, "rxnorm")
                        newArticlesTable = pubmed_miner.scispacyOntologyNER(newArticlesTable, "umls")
                        newArticlesTable = pubmed_miner.mapUmlsToSnomed(newArticlesTable, Keys['UMLSAPI_KEY'])
                        newArticlesTable = pubmed_miner.findTermFreq(newArticlesTable)
                        #push new articles
                        pubmed_miner.makeCSVJSON(newArticlesTable, designatedContainer, False)
                        asOfDate = pubmed_miner.retrieveAsTable(False, designatedContainer)
                        pubmed_miner.pushTableToDB(asOfDate, 'dashboard', 'pubmed_articles')
                        
                        #author summary tables
                        currentAuthorSummaryTable = pubmed_miner.retrieveAuthorSummaryTable('dashboard', 'pubmed_authors')
                        asOfThisYear = pd.DataFrame(currentAuthorSummaryTable.iloc[10]).T
                        pubmed_miner.checkAuthorRecord(newArticlesTable, asOfThisYear)
                        pubmed_miner.pushTableToDB(currentAuthorSummaryTable, 'dashboard', 'pubmed_authors')


                    return jsonify("" + str(numNewArticles) + " new article(s) added successfully")


@app.route('/remove_article', methods=['DELETE'])
def remove_article():
    if(request.method == 'DELETE'):
        # print(request.form.keys())
        print(request.form['passKeyHiddenDelete'])
        # if Keys['PASS_KEY']!=request.args.get('pass_key'): #Need to add hidden field for POST condition
        #     return "Not authorized to access this page"
        dateMY = "" + date.datetime.now().strftime("%m-%d-%Y")[0:2] + date.datetime.now().strftime("%m-%d-%Y")[5:10]
        if((request.method == 'DELETE') & (Keys['PASS_KEY']!= request.form['passKeyHiddenDelete'])):
            return "Not authorized to access this page"
        elif ((request.method == 'DELETE') & (Keys['PASS_KEY']== request.form['passKeyHiddenDelete'])) :
            searchArticles = request.form['articleIDToRemove']
            designatedContainer = request.form['containerWithArticle']
            containerArticles = pubmed_miner.getExistingIDandSearchStr( designatedContainer)
            # print(searchArticles)
            # print(designatedContainer)
            if(designatedContainer == "pubmed_ignore"):
                if(searchArticles in containerArticles[0]):
                    for item in container_ignore.query_items( 'SELECT * FROM pubmed_ignore', enable_cross_partition_query=True):
                        if(item['id'] == ("PMID: " + str(searchArticles))):
                            container_ignore.delete_item(item=item, partition_key=item['id'])
                else:
                    return jsonify('Article does not exist in this container.')
            else:
                if(searchArticles in containerArticles[0]):
                    for item in container.query_items( 'SELECT * FROM pubmed', enable_cross_partition_query=True):
                        if(item['id'] == ("PMID: " + str(searchArticles))):
                            container.delete_item(item=item, partition_key=item['id'])
                else: 
                    return jsonify('Article does not exist in this container.')

            return jsonify('Article removed.')

    
@app.route('/moveToContainer', methods=['POST'])
def moveToContainer():
    if(request.method == 'POST'):
        # print(request.form.keys())
        # print(request.form['passKeyHidden'])
        # if Keys['PASS_KEY']!=request.args.get('pass_key'): #Need to add hidden field for POST condition
        #     return "Not authorized to access this page"
        dateMY = "" + date.datetime.now().strftime("%m-%d-%Y")[0:2] + date.datetime.now().strftime("%m-%d-%Y")[5:10]
        if((request.method == 'POST') & (Keys['PASS_KEY']!= request.form['passKeyHiddenMove'])):
            return "Not authorized to access this page"
        elif ((request.method == 'POST') & (Keys['PASS_KEY']== request.form['passKeyHiddenMove'])) :
            articleToMove = request.form['articleMove']
            containerArticles = pubmed_miner.getExistingIDandSearchStr('pubmed')
            ignoreArticles = pubmed_miner.getExistingIDandSearchStr( 'pubmed_ignore')

            if(articleToMove in containerArticles[0]):
                pubmed_miner.moveItemToIgnoreContainer( [articleToMove], 'pubmed', 'pubmed_ignore')
                return jsonify("Article moved to the ignore container.")
            elif(articleToMove in ignoreArticles[0]):
                pubmed_miner.moveItemToIgnoreContainer( [articleToMove], 'pubmed_ignore', 'pubmed')
                return jsonify("Article moved to the pubmed article container.")
            else:
                return jsonify("Article is not in the database. Add it first.")
