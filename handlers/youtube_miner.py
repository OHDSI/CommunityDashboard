
from azure.cosmos import CosmosClient,PartitionKey
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
import pandas as pd
import datetime
from . import key_vault as kv

""" Steps
1. Initialize the cosmos client
2. Update all videos
    For each video check to see if they have been updated this month
    Get video details from youtube using videoID
    Update the cosmos db with new counts
3. Look for new videos
"""
def init_cosmos(key_dict: dict, container_name:str):
    """Initialize the Cosmos client
    Parameters
    ---
    * container_name : str - Name of azure container in cosmos db

    Returns container for cosmosclient
    """
    endpoint = key_dict['AZURE_ENDPOINT']
    azure_key = key_dict['AZURE_KEY']
    client = CosmosClient(endpoint, azure_key)
    database_name = 'ohdsi-impact-engine'
    database = client.create_database_if_not_exists(id=database_name)
    container = database.create_container_if_not_exists(
        id=container_name, 
        partition_key=PartitionKey(path="/id"),
        offer_throughput=400
    )
    return container

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

def video_details(key_dict: dict,video_id: str):
    """
    Takes a video_id and returns details like duration and viewcount
    This function queries the Youtube Data api 
    https://developers.google.com/youtube/v3/docs/search/list

    Parameters
    ----------
    * video_id : str - youtube unique id for video
    * api_key: dict - api developer key_dict

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
    youtube = build(key_dict['YOUTUBE_API_SERVICE_NAME'], key_dict['YOUTUBE_API_VERSION']\
        ,developerKey=key_dict['YOUTUBE_DEVELOPER_KEY'])
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

def update_video_stats(key_dict: dict):
    """Queries youtube api based upon list of items in azure cosmos db youtube container

    Args:
        api_key ([dict]): api key_dict to access youtube api
    """
    container=init_cosmos(key_dict,'youtube')
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
            updates=video_details(key_dict,item['id'])
            if len(updates)>0: # Case where video_details turns up empty
                today='{}'.format(datetime.date.today())
                item['counts'].append({'checkedOn':today,'viewCount':updates['viewCount']})
                item['lastChecked']=today
                container.upsert_item(body=item)
    return

def get_existing_ids(key_dict: dict):
    """queries the azure containers for all the ids the system already knows about

    parameters
    * key_dict: dict Dictionary of configuration information
    Returns:
        ids: list of unique id's of videos from youtube
    """
    container=init_cosmos(key_dict,'youtube') 
    query = "SELECT * FROM c"
    ids=[]
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True))
    for item in items:
        ids.append(item['id'])
    container_ignore=init_cosmos(key_dict,'youtube_ignore')
    query = "SELECT * FROM c"
    items = list(container_ignore.query_items(
        query=query,
        enable_cross_partition_query=True))
    for item in items:
        ids.append(item['id'])
    return ids

def youtube_search(key_dict:dict,q: str, max_results:int =50,order:str ="relevance"):
    """
    Take q as a search string to find all hits with youtube api to look for new videos.

    This function queries the Youtube Data api 
    https://developers.google.com/youtube/v3/docs/search/list

    Parameters
    ----------
    * q : str - query string for search
    * max_results: int - number of results to return in each page
    * order: str - relevance algorithm to run the search 
    * key_dict: dict - api key_dict for youtube access

    Returns
    -------
    * youtube_df: pd.DataFrame - Pandas dataframe of search resulst with 2 columns
    title and videoId.

    """
    youtube = build(key_dict['YOUTUBE_API_SERVICE_NAME'], key_dict['YOUTUBE_API_VERSION']\
        ,developerKey=key_dict['YOUTUBE_DEVELOPER_KEY'])
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

def sort_new_videos(key_dict:dict,candidate_list:list):
    """ Take a list of candidate video ids
    - get the video details
    - if the video channel is OHDSI, add to youtube
    - otherwise add to ignore
    """
    today='{}'.format(datetime.date.today())
    container=init_cosmos(key_dict,'youtube') 
    container_ignore=init_cosmos(key_dict,'youtube_ignore') 
    for candidate in candidate_list:
        video=video_details(key_dict,candidate)
        if video['channelTitle'][:5]=='OHDSI':
            item={'id':candidate,'title':video['title'],'duration':video['duration']\
                ,'channelId':video['channelId'],'channelTitle':video['channelTitle'],\
                'categoryId':video['categoryId'],'publishedAt':video['publishedAt'],'lastChecked':today}
            item['counts']=[{'checkedOn':today,'viewCount':str(video['viewCount'])}]
            print("Good Candidate {} created on {}".format(item['id'],item['publishedAt']))
            container.create_item(body=item)
        else:
            item={'id':candidate}
            print("Add to ignore list {}".format(item['id']))
            container_ignore.upsert_item(body=item)
    return

def main():
    key_dict=kv.get_key_dict()
    ignore_list=get_existing_ids(key_dict)
    search_qry="OHDSI"
    search_list=youtube_search(key_dict,search_qry)
    candidate_list=list(set(search_list)-set(ignore_list))
    sort_new_videos(key_dict,candidate_list)
    update_video_stats(key_dict)

if __name__ == '__main__':
    main()

