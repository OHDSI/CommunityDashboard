from datetime import datetime, date
from numpy import double
from community_dashboard import app
from community_dashboard.handlers import pubmed_miner, youtube_miner, ehden_miner
from community_dashboard.config import Keys
from flask import Flask, jsonify, render_template, request
import json
from azure.cosmos import CosmosClient, PartitionKey

def init_cosmos(container_name:str):
    """Initialize the Cosmos client
    Parameters
    ---
    * container_name : str - Name of azure container in cosmos db
    Returns container for cosmosclient
    """
    endpoint = Keys['AZURE_ENDPOINT']
    azure_key = Keys['AZURE_KEY']
    client = CosmosClient(endpoint, azure_key)
    database_name = Keys['DB_NAME']
    database = client.create_database_if_not_exists(id=database_name)
    container = database.create_container_if_not_exists(
        id=container_name, 
        partition_key=PartitionKey(path="/id"),
        offer_throughput=400
    )
    return container

def numberFormatter(number):
    number = int(number)
    if(number > 999999):
        number = str(int(number/1000000)) + "M"
    elif(number > 9999):
        number = str(int(number/1000)) + "K"
    elif(number > 999):
        number = "{:,}".format(number)
    return number

@app.route('/')
def index():
    """Main route for the application"""
    totalAuthors = 0
    totalArticles = 0
    totalHoursWatched = 0
    totalVideos = 0
    totalCourses = 0
    totalCompletions = 0
    container_dashboard = init_cosmos('dashboard')
    container_youtube = init_cosmos('youtube')
    for item in container_dashboard.query_items(query='SELECT * FROM dashboard WHERE dashboard.id=@id',
                parameters = [{ "name":"@id", "value": "pubmed_authors" }], 
                enable_cross_partition_query=True):
        totalAuthors = json.loads(item['data'])['cumulativeAuthors']['' + str(len(json.loads(item['data'])['cumulativeAuthors']) - 1)]
        totalAuthors = numberFormatter(totalAuthors)

    for item in container_dashboard.query_items(query='SELECT * FROM dashboard WHERE dashboard.id=@id',
                parameters = [{ "name":"@id", "value": "pubmed_articles" }], 
                enable_cross_partition_query=True):
        totalArticles = len(json.loads(item['data'])['pubmedID'])
        totalArticles = numberFormatter(totalArticles)

    for item in container_dashboard.query_items(query='SELECT * FROM dashboard WHERE dashboard.id=@id',
                parameters = [{ "name":"@id", "value": "youtube_annual" }], 
                enable_cross_partition_query=True):
        yearlyCounts = item['data']['hrsWatched']
        totalHoursWatched = sum(yearlyCounts.values())
        totalHoursWatched = numberFormatter(totalHoursWatched)

    videoIDs = []
    for item in container_youtube.query_items( query='SELECT * FROM youtube', enable_cross_partition_query=True):
    #     print(json.dumps(item['data'][0]['meshIDs'], indent = True))
        videoIDs.append(item['id'])
    totalVideos = len(videoIDs)
    totalVideos = numberFormatter(totalVideos)

    for item in container_dashboard.query_items(query='SELECT * FROM dashboard WHERE dashboard.id=@id',
                parameters = [{ "name":"@id", "value": "ehden" }], 
                enable_cross_partition_query=True):
    #     print(item['data'][0])
        for i in range(len(item['data'])):
    #         print(list(item['data'][i].keys())[0])
            if(list(item['data'][i].keys())[0] == "courses"):
                courses = item['data'][i]['courses']
                for i in range(len(courses)):
                    totalCourses += int(courses[i]['number_of_courses'])
    #             print(item['data'][i]['courses'])
            elif(list(item['data'][i].keys())[0] == "completions"):
                completions = item['data'][i]['completions']
                for i in range(len(completions)):
    #                 print(completions[i])
                    if(isinstance(completions[i]['year'], type(None)) == False):
                        totalCompletions += int(completions[i]['completions'])
        totalCourses = numberFormatter(totalCourses)
        totalCompletions = numberFormatter(totalCompletions)

    liveTable = {'totalAuthors': totalAuthors, 
                'totalArticles': totalArticles,
                'totalHoursWatched': totalHoursWatched,
                'totalVideos': totalVideos,
                'totalCourses': totalCourses,
                'totalCompletions': totalCompletions}

    #data as of
    dateCheckedOn = pubmed_miner.getTimeOfLastUpdate()

    return render_template('home.html', liveTable = liveTable, dateCheckedOn = dateCheckedOn)

@app.route('/update_all', methods=['GET'])
def update_all():
    """Run the miners to update data sources"""
    if Keys['PASS_KEY']!=request.args.get('pass_key'):
        return "Not authorized to access this page"
    pubmed_miner.update_data()
    ehden_miner.update_data()
    youtube_miner.update_data()
    return render_template('home.html')