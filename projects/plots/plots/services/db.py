import time
from azure.cosmos import CosmosClient, PartitionKey
import pandas as pd
import ast
import re
import click
from flask import g, current_app
import sqlite3

from plots.services import youtube_miner

class DbSession:

    def __init__(self):
        self.session = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.session.row_factory = sqlite3.Row

    def close(self):
        self.session.close()

    def init_db(self):
        with current_app.open_resource('test/schema.sql') as f:
            self.session.executescript(f.read().decode('utf8'))

    def find(self, path: str):
        return self.session.execute(f'SELECT * FROM {path}')


        

def get_db():
    if 'db' not in g:
        g.db = DbSession()
    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.init_db()

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def init_cosmos(container_name:str):
    """Initialize the Cosmos client
    Parameters
    ---
    * container_name : str - Name of azure container in cosmos db
    Returns container for cosmosclient
    """
    from plots.config import Keys
    endpoint = Keys.AZURE_ENDPOINT
    azure_key = Keys.AZURE_KEY

    client = CosmosClient(endpoint, azure_key)
    database_name = Keys.DB_NAME
    database = client.create_database_if_not_exists(id=database_name)
    container = database.create_container_if_not_exists(
        id=container_name, 
        partition_key=PartitionKey(path="/id"),
        offer_throughput=400
    )
    return container

def getTimeOfLastUpdate():
    """
    Called in main()
    Not every article has the same last date of update. Find the most recent among all articles. 
    """
    container = init_cosmos('pubmed')
    dateOfLastUpdate = "01-01-2022"
    for item in container.query_items(query='SELECT * FROM beta', enable_cross_partition_query=True):
        if(dateOfLastUpdate < item['data']['trackingChanges'][len(item['data']['trackingChanges'])-1]['datePulled']):
            dateOfLastUpdate = item['data']['trackingChanges'][len(item['data']['trackingChanges'])-1]['datePulled']
    return dateOfLastUpdate

def getExistingIDandSearchStr(containerName):
    """
    Called in main()
    Get a list of PMIDs and a list of title-author search strings
    Two outputs
    """
    container = init_cosmos( containerName)
    result = []
    exisitingIDs = []
    exisitingTitleAuthorStr = []
    for item in container.query_items(query=('SELECT * FROM ' + containerName), enable_cross_partition_query=True):
        exisitingIDs.append(item['data']['pubmedID'])
        exisitingTitleAuthorStr.append(item['data']['titleAuthorStr'])
    result = [exisitingIDs, exisitingTitleAuthorStr]

    return result

def get_publications():
    container_name='pubmed'
    container=init_cosmos(container_name)
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
    df1['SNOMED Terms (n)']=df1.apply(lambda row:"[{}](/abstracts?id={})".format(row['SNOMED Terms (n)'], row['PubMed ID']),axis=1)
    df1['Publication']=df1.apply(lambda row:"[{}](https://pubmed.gov/{})".format(row.Title,row['PubMed ID']),axis=1)
    return df1

def get_youtube():
    
    container_name='youtube'
    # container_name='pubmed_test'
    container=init_cosmos(container_name)
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
    # dateCheckedOn = pubmed_miner.getTimeOfLastUpdate()
    pullDate = 0
    for item in items:
        if(pullDate == 0):
            dateCheckedOn = item['lastChecked']
            dateCheckedOn = dateCheckedOn[5:len(dateCheckedOn)] + dateCheckedOn[4:5] + dateCheckedOn[0:4]
        #Review the log of counts and find the last two and subtract them for recent views
        df=pd.DataFrame(item['counts']).sort_values('checkedOn',ascending=False).reset_index()
        
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
    df['Duration'] = df.apply(lambda x: youtube_miner.convert_time(x['Duration']), axis = 1)
    df['yr']=df['Date Published'].dt.year
    df['hrsWatched']=(df.Duration.dt.days*24+df.Duration.dt.seconds/3600)*df['Total Views'] 
    df['Duration'] = df['Duration'].astype(str)
    
    # DataTable Prep
    df['Date Published']=df['Date Published'].dt.strftime('%Y-%m-%d')
    # df['Title']=df.apply(lambda row:"[{}](https://www.youtube.com/watch?v={})".format(row.Title,row.id),axis=1)
    df['Title']=df.apply(lambda row:"[{}](https://www.youtube.com/watch?v={})".format(row.Title,row.id),axis=1)
    df['Length'] = df.apply(lambda x: str(x['Duration'])[7:], axis = 1)
    # del df['Duration']
    # fig.update_layout( title_text="Youtube Video Analysis", showlegend=False)
    # df = pd.merge(df, df_transcripts, how = 'left', left_on= 'id', right_on = 'id')
    df['SNOMED Terms (n)']=df.apply(lambda row:"[{}](/transcripts?id={})".format(row['SNOMED Terms (n)'], row.id),axis=1)
    
    return df, dateCheckedOn

def get_youtube_monthly():
    results_container=init_cosmos('dashboard')
    query="SELECT * FROM c where c.id = 'youtube_monthly'"
    items = list(results_container.query_items(query=query, enable_cross_partition_query=True ))
    df2=pd.read_json(items[0]['data'])
    df2['Date']=pd.to_datetime(df2['Date']).dt.strftime('%Y-%m')
    return df2

def _get_ehden():
    results_container = init_cosmos('dashboard')
    query = "SELECT * FROM c where c.id = 'ehden'"
    items = list(results_container.query_items(query=query, enable_cross_partition_query=True ))
    return items

def get_ehden_users():
    items = _get_ehden()
    df = pd.DataFrame(items[0]['data'][1]['users'])
    df['year']=pd.to_numeric(df.year)
    df=df[df.year!=1970]
    df['number_of_users']=pd.to_numeric(df.number_of_users)
    return df

def get_ehden_course_completions():
    results_container = init_cosmos('dashboard')
    query = "SELECT * FROM c where c.id = 'ehden'"
    items = list(results_container.query_items(query=query, enable_cross_partition_query=True ))
    df=pd.DataFrame(items[0]['data'][3]['completions'])
    df['year']=pd.to_numeric(df.year)
    df=df[df.year!=1970]
    df['completions']=pd.to_numeric(df.completions)
    return df

def get_course_stats():
    items = _get_ehden()
    df=pd.DataFrame(items[0]['data'][4]['course_stats'])
    df2=df.groupby('course_id').max().reset_index()
    df2['authors']=df2.teachers.apply(_get_author_names)
    df2['course_started']=pd.to_datetime(df2.course_started)
    df2['course_fullname']=df2.apply(lambda row:"[{}](https://academy.ehden.eu/course/view.php?id={})".format(row.course_fullname,row.course_id),axis=1)
    df2['completions']=pd.to_numeric(df2.completions)
    df2['started']=pd.to_numeric(df2.started)
    df2['course_started']=df2.course_started.dt.strftime('%Y/%m/%d')
    df2=df2[df2.started!=0]
    df2.drop(['course_id','teachers'],axis=1,inplace=True)
    df2.sort_values('course_started',ascending=False,inplace=True)
    return df2

def _get_author_names(items):
    output=""
    for item in items:
        output +=", " + item['firstname'] + " " + item['lastname']
    return output[1:]

def get_researchers():
    results_container = init_cosmos('dashboard')
    query = "SELECT * FROM c where c.id = 'pubmed_authors'"
    items = list(results_container.query_items(query=query, enable_cross_partition_query=True ))
    currentAuthorSummaryTable = pd.read_json(items[0]['data'])
    currentAuthorSummaryTable = currentAuthorSummaryTable[['pubYear', 'numberNewFirstAuthors', 'cumulativeFirstAuthors', 'numberNewAuthors', 'cumulativeAuthors']]
    currentAuthorSummaryTable.columns = ['Year', 'New First Authors', 'Total First Authors', 'All New Authors', 'Total Authors']
    return currentAuthorSummaryTable