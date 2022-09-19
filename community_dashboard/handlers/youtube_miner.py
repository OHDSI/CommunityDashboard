
from azure.cosmos import CosmosClient,PartitionKey
from googleapiclient.discovery import build # googleapiclient. not apiclient
from googleapiclient.errors import HttpError
from oauth2client.tools import argparser
from community_dashboard.handlers.youtube_dash import convert_time
import pandas as pd
import datetime
from community_dashboard.handlers import key_vault as kv
from collections import defaultdict
#scispacy
import numpy as np
import spacy
from scispacy.linking import EntityLinker
from ratelimit import limits, RateLimitException, sleep_and_retry
import requests

#youtube transcript API
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter

""" Steps
1. Initialize the cosmos client
2. Update all videos
    For each video check to see if they have been updated this month
    Get video details from youtube using videoID
    Update the cosmos db with new counts
3. Look for new videos
"""

def init_cosmos(container_name:str):
    """Initialize the Cosmos client
    Parameters
    ---
    * container_name : str - Name of azure container in cosmos db

    Returns container for cosmosclient
    """
    endpoint = kv.key['AZURE_ENDPOINT']
    azure_key = kv.key['AZURE_KEY']
    client = CosmosClient(endpoint, azure_key)
    database_name = 'ohdsi-impact-engine'
    database = client.create_database_if_not_exists(id=database_name)
    container = database.create_container_if_not_exists(
        id=container_name, 
        partition_key=PartitionKey(path="/id"),
        offer_throughput=400
    )
    return container

#functions for NER
def scispacyNER(text, lowerThreshold, upperThreshold, nlp):
    """
    SciSpacy NER applied to YouTube transcripts
    """
    doc = nlp(str(text))
    #extract linker information
    linker = nlp.get_pipe("scispacy_linker")
    #placeholder
    conceptIDs = []
    concepts = []
    startChar = []
    endChar = []
    #for each entity identified in a document
    for ent in doc.ents:
        #if there exists entities
        if(len(ent._.kb_ents) != 0):
            #if the matching score is greater than 0.85 (threshold)
            if((ent._.kb_ents[0][1] >= lowerThreshold) & (ent._.kb_ents[0][1] <= upperThreshold)):
                conceptID = linker.kb.cui_to_entity[ent._.kb_ents[0][0]][0]
                concept = linker.kb.cui_to_entity[ent._.kb_ents[0][0]][1]
                #if ID is new
                if(conceptID not in conceptIDs):
                    conceptIDs = np.append(conceptIDs, conceptID)
                    concepts = np.append(concepts, concept)
                    startChar = np.append(startChar, ent.start_char)
                    endChar = np.append(endChar, ent.end_char)
    
    if(len(conceptIDs) == 0):
        conceptIDs = ['NA']
        concepts = ['NA']
        startChar = ['NA']
        endChar = ['NA']
    
    return [conceptIDs, concepts, startChar, endChar]
    
    
def scispacyCorpusLinkerLoader(corpus, ontology):
    """
    Called in scispacyOntologyNER()
    Loads spacy corpus and linker
    """
    nlp = spacy.load(corpus) # en_core_sci_sm, en_ner_bc5cdr_md
    nlp.add_pipe("scispacy_linker", config={"resolve_abbreviations": True, "linker_name": ontology})
    return nlp

def scispacyOntologyNER(inputData, ontology, corpus = "en_ner_bc5cdr_md"):
    """
    Called in main()
    Loads spacy corpus and linker. Applies scispacyNER to each row or item. 
    Returns the updated dataframe or dictionary
    """
    nlp = scispacyCorpusLinkerLoader(corpus, ontology)
    onotologyIDs = ontology + "IDspacy"
    onotologyTerms = ontology + "Termspacy"
    onotologyStart = ontology + "StartChar"
    onotologyEnd = ontology + "EndChar"
    if(ontology == "mesh"):
        threshold = 0.85
    elif(ontology == "rxnorm"):
        threshold = 0.7
    else:
        threshold = 0.95
    if (isinstance(inputData, pd.DataFrame)):
        inputData[[onotologyIDs, onotologyTerms, onotologyStart, onotologyEnd]] = inputData.apply(lambda x: scispacyNER(x['abstract'], threshold, 1, nlp), axis = 1, result_type='expand')
    
    elif(isinstance(inputData, dict)):
        ids, terms, startChar, endChar = scispacyNER(inputData['transcript'], threshold, 1, nlp)
        inputData[onotologyIDs] = list(ids)
        inputData[onotologyTerms] = list(terms)
        inputData[onotologyStart] = list(startChar)
        inputData[onotologyEnd] = list(endChar)
    return inputData



period = 1
MAX_CALLS = 15


@sleep_and_retry
@limits(calls=MAX_CALLS, period=period)
def mapToSnomed(ids, apiKey):
    snomedIDs = []
    snomedNames = []
    if(isinstance(ids, list)):
        for i in ids:
            if(i != 'NA'):
    #             #mesh to umls
                baseUrl = "https://uts-ws.nlm.nih.gov/rest/"
    #             meshToUmlsQuery = "search/current?string=" + i + "&inputType=sourceUi&searchType=exact&sabs=MSH&apiKey="
    #             search_url = baseUrl + meshToUmlsQuery + apiKey
    #             umlsResp = requests.get(search_url)
    #             umlsJson = umlsResp.json()
                #get umls ui and map to snomed

    #             if(len(umlsJson['result']['results']) != 0):
    #                 umlsID = umlsJson['result']['results'][0]['ui']
                umlsToSnomedQuery = "search/current?string=" + i + "&sabs=SNOMEDCT_US&returnIdType=code&apiKey="
                search_url = baseUrl + umlsToSnomedQuery + apiKey
                snomedResp = requests.get(search_url)
                snomedJson = snomedResp.json()
                if(len(snomedJson['result']['results']) != 0):
                    snomedID = snomedJson['result']['results'][0]['ui']
                    snomedName = snomedJson['result']['results'][0]['name']
                else:
                    snomedID = "00000000"
                    snomedName = "No Mapping Found"
    #             else:
    #                 snomedID = "00000000"
    #                 snomedName = "No Mapping Found"
                snomedIDs = np.append(snomedIDs, snomedID)
                snomedNames = np.append(snomedNames, snomedName)
            else:
                snomedID = "00000000"
                snomedName = "No Mapping Found"
                snomedIDs = np.append(snomedIDs, snomedID)
                snomedNames = np.append(snomedNames, snomedName)
            if(len(snomedIDs) == 0):
                snomedIDs = ['NA']
                snomedNames = ['NA']
        return [snomedIDs, snomedNames]

    else:
#         #mesh to umls
        if(ids != 'NA'):
            baseUrl = "https://uts-ws.nlm.nih.gov/rest/"
    #         meshToUmlsQuery = "search/current?string=" + ids + "&inputType=sourceUi&searchType=exact&sabs=MSH&apiKey="
    #         search_url = baseUrl + meshToUmlsQuery + apiKey
    #         umlsResp = requests.get(search_url)
    #         umlsJson = umlsResp.json()
    #         #get umls ui and map to snomed

    #         if(len(umlsJson['result']['results']) != 0):
    #             umlsID = umlsJson['result']['results'][0]['ui']
            umlsToSnomedQuery = "search/current?string=" + ids + "&sabs=SNOMEDCT_US&returnIdType=code&apiKey="
            search_url = baseUrl + umlsToSnomedQuery + apiKey
            snomedResp = requests.get(search_url)
            snomedJson = snomedResp.json()
            if(len(snomedJson['result']['results']) != 0):
                snomedID = snomedJson['result']['results'][0]['ui']
                snomedName = snomedJson['result']['results'][0]['name']
            else:
                snomedID = "00000000"
                snomedName = "No Mapping Found"
    #         else:
    #             snomedID = "00000000"
    #             snomedName = "No Mapping Found"
            if(len(snomedIDs) == 0):
                snomedID = ['NA']
                snomedName = ['NA']
            return [snomedID, snomedName]
        else:
            return ['NA', 'NA']

def mapUmlsToSnomed(inputData, apiKey):
    """
    Called in main()
    Loads spacy corpus and linker. Applies scispacyNER to each row or item. 
    Returns the updated dataframe or dictionary
    """

    if (isinstance(inputData, pd.DataFrame)):
        inputData[["snomedIDs", "snomedNames"]] = inputData.apply(lambda x: mapToSnomed(list(x['umlsIDspacy']), apiKey), axis = 1, result_type='expand')
    
    elif(isinstance(inputData, dict)):
        ids, terms= mapToSnomed(inputData['umlsIDspacy'], apiKey)
        inputData["snomedIDs"] = list(ids)
        inputData["snomedNames"] = list(terms)

    return inputData

def termFreq(eachArticle):
    """
    Called in findTermFreq()
    Finds the frequency of each term 
    Returns a concatenated string of terms and frequencies
    """
    termAndFreqStr = ""
    try:
        isinstance(eachArticle[0]['umlsStartChar'], type(None))
    except:
        if(isinstance(eachArticle['umlsStartChar'], type(None))):
            return termAndFreqStr
        else:
            length = len(eachArticle['umlsStartChar'])
#             print(eachArticle['umlsIDspacy'])
#             print(eachArticle['snomedIDs'])
#             print(eachArticle['umlsStartChar'])
            terms = []
            termFreqs = []
            if(length == 0):
                return 'No Mappings Found'
            else:
                for i in range(0, length):
                    if(eachArticle['snomedIDs'][i] != '00000000'):
                        if(eachArticle['umlsEndChar'][i] != "NA"):
                            termStart = int(eachArticle['umlsStartChar'][i])
                            termEnd = int(eachArticle['umlsEndChar'][i])
                            searchTerm = eachArticle['abstract'][termStart:termEnd]
                            term = eachArticle['snomedNames'][i]
                            termFreq = eachArticle['abstract'].count(searchTerm)
                            terms = np.append(terms, term)
                            termFreqs = np.append(termFreqs, termFreq)
                sortedOrder = np.argsort(termFreqs)[::-1]
                for sortedIndex in sortedOrder:
                    term = terms[sortedIndex]
                    termFreq = termFreqs[sortedIndex]
                    termAndFreqStr = termAndFreqStr + term + " (" + str(int(termFreq)) + "); "
                if(len(termAndFreqStr) == 0):
                    return 'No Mappings Found'
                else:
                    return termAndFreqStr
    else:
        if(isinstance(eachArticle[0]['umlsStartChar'], type(None))):
            return termAndFreqStr
        else:
            length = len(eachArticle[0]['umlsStartChar'])
            terms = []
            termFreqs = []
            if(length == 0):
                return 'No Mappings Found'
            else:
                for i in range(0, length):
                    if(eachArticle[0]['snomedIDs'][i] != '00000000'):
                        if(eachArticle[0]['umlsEndChar'][i] != "NA"):
                            termStart = int(eachArticle[0]['umlsStartChar'][i])
                            termEnd = int(eachArticle[0]['umlsEndChar'][i])
                            searchTerm = eachArticle[0]['transcript'][termStart:termEnd]
                            term = eachArticle[0]['snomedNames'][i]
                            termFreq = eachArticle[0]['transcript'].count(searchTerm)
                            terms = np.append(terms, term)
                            termFreqs = np.append(termFreqs, termFreq)
                sortedOrder = np.argsort(termFreqs)[::-1]
                for sortedIndex in sortedOrder:
                    term = terms[sortedIndex]
                    termFreq = termFreqs[sortedIndex]
                    termAndFreqStr = termAndFreqStr + term + " (" + str(int(termFreq)) + "); "
                if(len(termAndFreqStr) == 0):
                    return 'No Mappings Found'
                else:
                    return termAndFreqStr

def findTermFreq(inputData):
    """
    Called in main()
    Finds the frequency of each term 
    Adds a new column
    """
    
    if (isinstance(inputData, pd.DataFrame)):
        inputData['termFreq'] = inputData.apply(lambda x: termFreq(x), axis = 1)
    
    elif(isinstance(inputData, dict)):
        termsWFreq = termFreq(inputData)
        inputData["termFreq"] = termsWFreq

    return inputData


def pullNerMapTranscript(videoDict):
    
    newTranscriptsDict = defaultdict(list)
    #For each video, save the id, title, channel title, and transcript
    videoID = videoDict['id']
    #dictionary of videos stored as dictionaries with ID, title, channel, and transcript
    try:
        transcript = YouTubeTranscriptApi.get_transcript(videoID)
    except Exception as exception:
        videoDict['transcript'] = type(exception).__name__
    else:
        # for pos, item in enumerate(collection):
        # Extract transcripts and append into a single string
        singleStr = ""
        for text in transcript:
            singleStr = singleStr + text['text'] + " "
        videoDict['transcript'] = singleStr

    #rxnorm and umls NERs
    #en_ner_bc5cdr_md, en_core_sci_scibert, "en_core_sci_lg"
    # newTranscriptsDict = scispacyOntologyNER(newTranscriptsDict, "mesh", "en_ner_bc5cdr_md") 
    videoDict = scispacyOntologyNER(videoDict, "umls", "en_ner_bc5cdr_md")
    videoDict = scispacyOntologyNER(videoDict, "rxnorm", "en_ner_bc5cdr_md") 

    #map umls to SNOMED
    umlsApiKey = kv['UMLSAPI_KEY']
    videoDict = mapUmlsToSnomed(videoDict, umlsApiKey)
    videoDict = findTermFreq(videoDict)

def response_test(response: dict):
    """Quick test of the http request to make sure it has the data structure needed to analyze

    Args:
        response (dict): dictionary of http response

    Returns:
        boolean test 
    """
    if 'items' in response:
        if len(response['items'])>0:
            if 'snippet' in response['items'][0]:
                if 'channelTitle' in response['items'][0]['snippet']:
                    return True
    return False

def video_details(video_id: str):
    """
    Takes a video_id and returns details like duration and viewcount
    This function queries the Youtube Data api 
    https://developers.google.com/youtube/v3/docs/search/list

    Parameters
    ----------
    * video_id : str - youtube unique id for video

    Returns
    -------
    * video: dict - A dictionary of results
    * title: str - name of the youtube video
    * duration: str - length of video in 'PT8M52S' format
    * channelId: str - unique hash for channelId
    * channeltitle: str - human readable 'OHDSI'
    * categoryID: str - category id
    * viewCount: int - number of views of video
    * publishedAt: str - date the video was published

    """
    youtube = build(kv.key['YOUTUBE_API_SERVICE_NAME'], kv.key['YOUTUBE_API_VERSION']\
        ,developerKey=kv.key['YOUTUBE_DEVELOPER_KEY'])
    """use youtube data api to get details on a video"""
    video={}
    response = youtube.videos().list(part='statistics, snippet, contentDetails', \
        id=video_id).execute()
    if response_test(response):
        video['title']=response['items'][0]['snippet']['title']
        video['duration']=response['items'][0]['contentDetails']['duration']
        video['channelId']=response['items'][0]['snippet']['channelId']
        video['channelTitle']=response['items'][0]['snippet']['channelTitle']
        video['categoryId']=response['items'][0]['snippet']['categoryId']
        video['viewCount']=response['items'][0]['statistics']['viewCount']
        video['publishedAt']=response['items'][0]['snippet']['publishedAt']
    return video

def update_video_stats():
    """Queries youtube api based upon list of items in azure cosmos db youtube container


    """
    container=init_cosmos('youtube')
    query = "SELECT * FROM c"
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    this_month=datetime.date.today().month
    for item in items:
        month_checked=datetime.datetime.strptime(item['lastChecked'], "%Y-%m-%d").month
        if month_checked != this_month:
            #print("updating item {}".format(item['id']))
            updates=video_details(item['id'])
            if len(updates)>0: # Case where video_details turns up empty
                today='{}'.format(datetime.date.today())
                item['counts'].append({'checkedOn':today,'viewCount':updates['viewCount']})
                item['lastChecked']=today
                container.upsert_item(body=item)
    return

def get_existing_ids():
    """queries the azure containers for all the ids the system already knows about

    parameters

    Returns:
        ids: list of unique id's of videos from youtube
    """
    container=init_cosmos('youtube') 
    query = "SELECT * FROM c"
    ids=[]
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True))
    for item in items:
        ids.append(item['id'])
    container_ignore=init_cosmos('youtube_ignore')
    query = "SELECT * FROM c"
    items = list(container_ignore.query_items(
        query=query,
        enable_cross_partition_query=True))
    for item in items:
        ids.append(item['id'])
    return ids

def youtube_search(q: str, max_results:int =50,order:str ="relevance"):
    """
    Take q as a search string to find all hits with youtube api to look for new videos.

    This function queries the Youtube Data api 
    https://developers.google.com/youtube/v3/docs/search/list

    Parameters
    ----------
    * q : str - query string for search
    * max_results: int - number of results to return in each page
    * order: str - relevance algorithm to run the search 

    Returns
    -------
    * youtube_df: pd.DataFrame - Pandas dataframe of search resulst with 2 columns
    title and videoId.

    """
    youtube = build(kv.key['YOUTUBE_API_SERVICE_NAME'], kv.key['YOUTUBE_API_VERSION']\
        ,developerKey=kv.key['YOUTUBE_DEVELOPER_KEY'])
    request = youtube.search().list(
        q=q, type="video", order = order,
        part="id,snippet", # Part signifies the different types of data you want 
        maxResults=max_results)
    id_list = []
    while request is not None:
        activities_doc = request.execute()
        for search_result in activities_doc.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                id_list.append(search_result['id']['videoId'])
        request=youtube.search().list_next(request, activities_doc)
    return id_list
    
def sort_new_videos(candidate_list:list):
    """ Take a list of candidate video ids
    - get the video details
    - if the video channel is OHDSI, add to youtube
    - otherwise add to ignore
    Args:
        candidat_list (list): A list of youtube id's that are candidates for getting details

  
    """
    today='{}'.format(datetime.date.today())
    container=init_cosmos('youtube') 
    container_ignore=init_cosmos('youtube_ignore') 
    for candidate in candidate_list:
        video=video_details(candidate)
        if video['channelTitle'][:5]=='OHDSI':
            pullNerMapTranscript(video)

            item={'id':candidate,'title':video['title'],'duration':video['duration'],\
                  'channelId':video['channelId'],'channelTitle':video['channelTitle'],\
                  'categoryId':video['categoryId'],'publishedAt':video['publishedAt'],\
                  'rxnormIDspacy': video['rxnormIDspacy'], 'rxnormTermspacy': video['rxnormTermspacy'],\
                  'rxnormStartChar': video['rxnormStartChar'], 'rxnormEndChar': video['rxnormEndChar'],\
                  'umlsIDspacy': video['umlsIDspacy'], 'umlsTermspacy': video['umlsTermspacy'],\
                  'umlsStartChar': video['umlsStartChar'], 'umlsEndChar': video['umlsEndChar'],\
                  'snomedIDs': video['snomedIDs'], 'snomedNames': video['snomedNames'],\
                  'termFreq': video['termFreq'],
                  'lastChecked':today}
            item['counts']=[{'checkedOn':today,'viewCount':str(video['viewCount'])}]
            print("Good Candidate {} created on {}".format(item['id'],item['publishedAt']))
            container.create_item(body=item)
        else:
            item={'id':candidate}
            print("Add to ignore list {}".format(item['id']))
            container_ignore.upsert_item(body=item)
    return

def diff_series(item_dict):
    """ Generates a Differential from a series of monthly counts

    Args:
        item_dict (Dict): Dictionary of all the youtube items in CosmosDB

    Returns:
        sr_duation Pandas Series: A series with an index of yyyy-mm monthly dates with totals from the month before
    """
    duration=convert_time(item_dict['duration'])
    df=pd.DataFrame(item_dict['counts'])
    df['checkedOn']=pd.to_datetime(df.checkedOn)
    df['checkedOn']=df.checkedOn.dt.strftime('%Y-%m')
    df['viewCount']=pd.to_numeric(df.viewCount)
    df[item_dict['id']]=df.viewCount
    df.drop(['viewCount'],axis=1,inplace=True)
    df.set_index('checkedOn',inplace=True)
    sr1=df[item_dict['id']].diff().fillna(0)
    sr_duration=(sr1*duration.total_seconds())/3600
    return sr_duration

def update_monthly_dash():
    """ Updates the dataframe in dashboard stored queries for monthly analytics
    """
    container=init_cosmos('youtube') 
    query = "SELECT * FROM c"
    ids=[]
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True))
    df=pd.DataFrame(diff_series(items[0]))
    for item in items[1:]:
        df=df.merge(diff_series(item),on='checkedOn',copy=True,how='outer')
    df2=df.sum(axis=1).to_frame()
    df2.reset_index(inplace=True)
    df2.columns=['Date','Count']
    container2=init_cosmos('dashboard')
    results={}
    results['data'] = df2[1:].to_json()
    results['id'] = 'youtube_monthly'
    container2.upsert_item(body = results)
    return

def update_yearly_dash():
    """ 
    Updates the dataframe in dashboard stored queries for yearly analytics
    """
    container_dashboard = init_cosmos('dashboard')
    container_youtube = init_cosmos('youtube')
    query = "SELECT * FROM c"
    items = list(container_youtube.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    videos=[]
    for item in items:
        df=pd.DataFrame(item['counts']).sort_values('checkedOn',ascending=False).reset_index()
        total_views=int(df.viewCount[0])
        videos.append({'id':item['id'],
                    'Title':item['title'],
                    'Duration':item['duration'],
                    'Date Published':pd.to_datetime(item['publishedAt']),
                    'Total Views':total_views,
                    'channelTitle':item['channelTitle']}
                    )
    df=pd.DataFrame(videos)
    df=df[df.channelTitle.str.startswith('OHDSI')].copy(deep=True)
    # df['Duration'] = df.apply(lambda x: str(x['Duration'])[2:], axis = 1)
    df['Duration'] = df.apply(lambda x: convert_time(x['Duration']), axis = 1)
    df['yr']=df['Date Published'].dt.year

    df['hrsWatched']=(df.Duration.dt.days*24+df.Duration.dt.seconds/3600)*df['Total Views']

    yrlyTotal = pd.DataFrame(df.groupby('yr')['hrsWatched'].sum())
    container_dashboard.upsert_item({'id': 'youtube_annual', 'data': yrlyTotal.to_dict()})

def update_data():
    ignore_list=get_existing_ids()
    search_qry="OHDSI"
    search_list=youtube_search(search_qry)
    candidate_list=list(set(search_list)-set(ignore_list))
    sort_new_videos(candidate_list)
    update_video_stats()
    update_monthly_dash()
    update_yearly_dash()

