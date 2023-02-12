from azure.cosmos import CosmosClient,PartitionKey
import os, uuid
from oauth2client.tools import argparser
from Bio import Entrez, Medline #http://biopython.org/DIST/docs/tutorial/Tutorial.html#sec%3Aentrez-specialized-parsers
import xmltodict #https://marcobonzanini.com/2015/01/12/searching-pubmed-with-python/
import time
import datetime as date   
import pandas as pd
import numpy as np
import json
import re
from serpapi  import GoogleSearch
import csv
import Levenshtein as lev
from fuzzywuzzy import fuzz, process
from os.path import exists
from pprint import pprint
from collections import defaultdict, Counter
from dateutil.parser import *
import ast
from flask import current_app
#import scispacy
import spacy
# try:
#     from scispacy.linking import EntityLinker
# except: # https://github.com/allenai/scispacy/issues/372
#     pass
from ratelimit import limits, RateLimitException, sleep_and_retry
import requests

from plots.services.db import get_db

try:
    from plots.config import Keys
except ImportError:
    pass

# account_url = "https://bidsclassfs2.blob.core.windows.net"

# # Create the BlobServiceClient object
# blob_service_client = BlobServiceClient(account_url, credential=default_credential)
# container_client = blob_service_client.get_container_client("ohdsistore")
# resultObj = container_client.list_blobs(name_starts_with='en_core_sci_md-0.5.1/en_core_sci_md/en_core_sci_md-0.5.1/')


def init_cosmos(container_name:str):
    """ Initialize the Cosmos client
    Parameters
    ---
    * container_name : str - Name of azure container in cosmos db
    Returns container for cosmosclient
    """
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

@sleep_and_retry
@limits(calls=3, period=1)
def pubmedAPI(searchQuery):

    """ For each of the search terms (searchQuery), search on pubmed databases
        Called in getPMArticles()

    parameters
        searchQuery: list of search strategies, key words, or article pubmed id

    Returns:
        outputTable: a dataframe with an article per row and attributes as columns
    """
    Entrez.email = current_app.config['ENTREZ_EMAIL'], #Keys.ENTREZ_EMAIL #personal email address for Pubmed to reach out if necessary
    paramEutils = { 'usehistory':'Y' } #using cache
    queryList = searchQuery
    dbList = ['pubmed'] #Search through all databases of interest 'nlmcatalog', 'ncbisearch' 
    articleList = [] #empty placeholder
    retMax = 1000 #number of results to return
    
    if(type(queryList) == list):
        for searchStringItem in queryList:
            # generate query to Entrez eSearch
            time.sleep(1)
            eSearch = Entrez.esearch(db="pubmed", term=searchStringItem, **paramEutils, retmax = retMax)

            # get eSearch result as dict object
            res = Entrez.read(eSearch)
            idList = res["IdList"]
            handle = Entrez.efetch(db="pubmed",
                                   id=idList, rettype="medline", retmode="json", retmax = retMax)
            articleListTemp = Medline.parse(handle)
            articleListTemp = list(articleListTemp)
            articleList.extend(articleListTemp)
        print("Found in PubMed:", len(articleList))
    else:
        for dB in dbList: 
                time.sleep(1)
                # generate query to Entrez eSearch
                eSearch = Entrez.esearch(db=dB, term=searchQuery, **paramEutils, retmax = retMax)

                # get eSearch result as dict object
                res = Entrez.read(eSearch)
                idList = res["IdList"]
                handle = Entrez.efetch(db="pubmed",
                                       id=idList, rettype="medline", retmode="json", retmax = retMax)
                articleListTemp = Medline.parse(handle)
                articleListTemp = list(articleListTemp)
                articleList.extend(articleListTemp)
                print(dB, ":", len(articleListTemp))

    print("Total number of articles :", len(articleList))

    #reshape the table
    outputTable = pd.DataFrame.from_dict(articleList[0], orient = "index")
    for i in range(len(articleList)-1):
        row = pd.DataFrame.from_dict(articleList[i+1], orient = "index")
        outputTable = pd.concat([outputTable, row], axis = 1)
    outputTable = outputTable.T
    return outputTable

def selectAndDropCol(table):

    """ Rename, select, and drop columns
        Called in getPMArticles()

    parameters
        table: dataframe with an article per row and attributes as columns, output from pubmedAPI() 

    Returns:
        outputTable: a dataframe with reduced and renamed columns
    """
    outputTable = table.rename(columns={"AB": "abstract", "CI": "copyrightInformation", "AD": "affiliation",
                               "IRAD": "investigatorAffiliation", "AID": "articleID", "AU": "author",
                               "AUID": "authorID", "FAU": "fullAuthor", "BTI": "bookTitle",
                               "CTI": "collectionTitle", "COIS": "confOfInterest", "CN": "corporateAuthor",
                               "CRDT": "creationDate", "DCOM": "dtAddedToDB", "DA": "dtProcesCreated",
                               "LR": "lastRevised", "DEP": "dtOfElecPub", "DP": "dtOfPub",
                               "EN": "edition", "ED": "editorName", "FED": "fullEditorName",
                               "EDAT": "dtCitationAdded", "GS": "geneSymbol", "GN": "generalNote",
                               "GR": "grantNum", "IR": "investName", "FIR": "fullInvestName",
                               "ISBN": "isbn", "IS": "issn", "IP": "issue",
                               "TA": "journalTitleAbbrev", "JT": "journalTitle", "LA": "language",
                               "LID": "locID", "MID": "manuID", "MHDA": "dtMeshAddedtoCitation", 
                               "MH": "meshT", "JID": "nlmID", "RF": "numOfRefer", 
                               "OAB": "othAbstract", "OCI": "othCopyRInfo", "OID": "otherID", 
                               "OT": "othTerm", "OTO": "othTermOwner", "OWN": "owner", 
                               "PG": "pagination", "PS": "personalNameAsSubject", "FPS": "fullpNAS", 
                               "PL": "countryOfPub", "PHST": "pubHistStatus", "PST": "pubStatus",
                               "PT": "pubType", "PUBM": "pubModel", "PMC": "pmcID",
                               "PMCR": "pmcRelease", "PMID": "pubmedID",
                               "RN": "registryNum", "NM": "suppleConceptRecord", "SI": "secondSoID",
                               "SO": "source", "SFM": "spaceFlightMission", "STAT": "status",
                               "SB": "subset", "TI": "title", "TT": "translitTitle",
                               "VI": "volume", "VTI": "volumeTitle"
                              })

    #affiliation, author, authorID, fullAuthor, creationDate, grantNum, investName, fullInvestName, language, locID, nlmID
    #numOfRefer(ences), countryOfPub(lication), pmcID, pubmedID, source, title
    listOfCol = ["pmcID", "pubmedID", "nlmID", "journalTitle", "title",  "creationDate", "affiliation",
    "locID", "countryOfPub", "language", "grantNum", "fullAuthor", "abstract", "meshT", "source"]
    #for any missing column, create it
    for i in range(len(listOfCol)):
        if ((listOfCol[i] in outputTable.columns) == False):
            outputTable[listOfCol[i]] = None
    outputTable = outputTable.drop_duplicates('pubmedID', keep = 'first')[["pmcID", "pubmedID", "nlmID", 
                                                                         "journalTitle",
                                                                         "title", 
                                                                          "creationDate", "affiliation", 
                                                                         "locID", "countryOfPub", "language",
                                                                         "grantNum", "fullAuthor", "abstract",
                                                                           "meshT", 
                                                                         "source"]]
    outputTable = outputTable.reset_index()
    outputTable = outputTable.drop(columns = ['index'])
    return outputTable

def formatName(row):

    """ Format all the names into "first, last" so that it is consistent with Google Scholars
        Called in getPMArticles()

    parameters
        row: each row of a dataframe, used with apply() 

    Returns:
        replacement: a cleaned author string
    """
    fullAuthorStr = str(row['fullAuthor'])
    i = 0
    startQ = 0
    sepQ = 0
    endQ = 0
    numComma = 0
    replacement = "["
    while( i < len(fullAuthorStr)):
        if(fullAuthorStr[i] == "'"):
            numComma += 1
            if(numComma % 2 == 0):
                endQ = i
                replacement = replacement + "'" + str(fullAuthorStr[(sepQ + 2):(endQ)]) + ", " + str(fullAuthorStr[(startQ + 1):(sepQ)]) + "'"
                if(endQ + 2 != len(fullAuthorStr)):
                    replacement = replacement + ", "
                    i += 3

            else:
                startQ = i
                i += 1
        elif(fullAuthorStr[i] == ","):
            sepQ = i
            i += 1

        else:
            i += 1
    replacement = replacement + "]"
    return replacement

def splitFullAuthorColumn(outputTable):

    """ Split the full author column into first author, ...etc. keep the first author column only
        Called in getPMArticles()

    parameters
        outputTable: dataframe with articles and articles' attributes

    Returns:
        outputTable: dataframe with added columns for first author
    """
    # testFind = re.sub('[^A-Za-z0-9]+', '', testFind).lower()
    outputTable['fullAuthor'] = outputTable['fullAuthor'].astype("str")
    outputTable['fullAuthorEdited'] = outputTable['fullAuthor'].map(lambda fullAuthor: re.sub(',', '', fullAuthor[1:len(fullAuthor)-1]))

    # re.sub('([^"]|\\")*', '', finalTable['fullAuthor']).lower()
    tempSplit = outputTable['fullAuthorEdited'].str.split("' '", n = -1, expand = True)
    tempSplit = tempSplit.add_prefix('author')
    outputTable = pd.concat([outputTable, tempSplit], axis = 1)
    # finalTable['fullAuthor'][13]
    return outputTable

def getYear(row):

    """ Get the year published for every article. Used for filtering articles after 2010
        Called in getPMArticles()

    parameters
        row: each row of a dataframe

    Returns:
        year
    """
    if(row['creationDate'] == 'nan'):
        return(2000)
    else:
        return(pd.to_numeric(row['creationDate'][0:4]))
    
def getPMArticles(query):

    """ Fetch relevant articles from PubMed
        Perform final cleaning on this dataframe before it is passed for google scholar
            citation search and match (getGoogleScholarCitation() applied to each row)
        Called in main()

    parameters
        query: list of search strategies, key words, or article pubmed id

    Returns:
        outputTable: dataframe with fetched articles
    """
    outputTable = pubmedAPI(query)
    outputTable = selectAndDropCol(outputTable)
    outputTable['fullAuthor'] = outputTable.apply(formatName, axis = 1)
    outputTable = splitFullAuthorColumn(outputTable)
    
    outputTable['creationDate'] = outputTable['creationDate'].astype(str)
    outputTable['creationDate'] = outputTable.apply(lambda x: x['creationDate'][2:-2], axis = 1)
    outputTable['pubYear'] = outputTable.apply(lambda x: getYear(x), axis = 1)
    outputTable['titleAuthorStr'] = "" + outputTable['title'] + " " + outputTable['author0']
    outputTable['datePulled'] = date.datetime.now().strftime("%m-%d-%Y")

    outputTable = outputTable.rename(columns = {
       "author0": "firstAuthor"
    })
    outputTable = outputTable[outputTable.columns.drop(list(outputTable.filter(regex='author[0-9]+')))]
    if ('Unnamed: 0' in outputTable.columns):
        del outputTable['Unnamed: 0']
    
    return outputTable

def serpAPI(query, api_key):

    """ Input API key and search term for Google Scholars
        Called in getGoogleScholarCitation()

    parameters
        api_key,
        query: unique article title + first author string

    Returns:
        results: dictionary of fetched articles from google scholars
    """
    fromYr = 2010
    params = {
      "engine": "google_scholar",
      "q": query,
      "hl": "en",
      "start": 0,
      "num": "20",
      "api_key": api_key
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    
    return results

def saveRawSerpApiAsDict(serpRawResult):

    """ concatenate all the results into one JSON object
        Called in getGoogleScholarCitation()

    parameters
        serpRawResult: dictionary of fetched articles from google scholars

    Returns:
        extractedResult: json of fetched articles from google scholars with selected organic_results field
    """
    extractedResult = {}
    if('organic_results' in serpRawResult.keys()):
        lengthResult = len(serpRawResult['organic_results'])
        if(lengthResult == 1):
            extractedResult = {'gScholarQResults': [serpRawResult['organic_results'][0]]}
        if(lengthResult > 1):
            extractedResult = {'gScholarQResults': [serpRawResult['organic_results'][0]]}
            for k in range(lengthResult-1):
                extractedResult['gScholarQResults'].append(serpRawResult['organic_results'][k+1])
                
    return extractedResult

def serpApiExtract(extractedResult):

    """ From the JSON object produced by saveRawSerpApiAsDict(), 
        extract title, author, and citation information based on rules.
        Called in getGoogleScholarCitation()

    parameters
        extractedResult: json of fetched articles from google scholars with selected organic_results field

    Returns:
        extractedResult: json of articles with selected features: citation counts, link, ...
    """
    searchDict = {"citationInfo": {}, 'firstAuthorInfo': {}, 'fullAuthorInfo': {}, 'titleAuthorStr': {}, 'googleScholarLink': {}}
    dashIndex = 0
    #if there is more than one article returned
    if(len(extractedResult['gScholarQResults']) < 2):
        #get the title
        title = extractedResult['gScholarQResults'][0]['title']
        #if there is no citation information, set to 0
        if(('cited_by' in extractedResult['gScholarQResults'][0]['inline_links'].keys()) == False):
            searchDict['citationInfo'][title] = 0
            searchDict['googleScholarLink'][title] = "Link Not Available"
        else:
            numCitedBy = extractedResult['gScholarQResults'][0]['inline_links']['cited_by']['total']
            searchDict['citationInfo'][title] = numCitedBy
            if(('versions' in extractedResult['gScholarQResults'][0]['inline_links'].keys())):
                googleScholarLink = extractedResult['gScholarQResults'][0]['inline_links']['versions']['link']
                searchDict['googleScholarLink'][title] = googleScholarLink
            else:
                searchDict['googleScholarLink'][title] = "Link Not Available"

        #find author(s) if it is populated
        if(('authors' in extractedResult['gScholarQResults'][0]['publication_info']) == False):
            searchDict['firstAuthorInfo'][title] = "No information available"
            if((('summary' in extractedResult['gScholarQResults'][0]['publication_info']) == True)):
                if("-" in extractedResult['gScholarQResults'][0]['publication_info']['summary']):
                    dashIndex = extractedResult['gScholarQResults'][0]['publication_info']['summary'].index("-")
                    searchDict['fullAuthorInfo'][title] = extractedResult['gScholarQResults'][0]['publication_info']['summary'][0:dashIndex]
                else:
                    searchDict['fullAuthorInfo'][title] = "No information available"
            else:
                searchDict['fullAuthorInfo'][title] = "No information available"
        else:
            findAuthors = extractedResult['gScholarQResults'][0]['publication_info']['authors']
            resultStr = "["
            for i in range(len(findAuthors)):
                if (i == len(findAuthors) - 1):
                    resultStr = resultStr + "'" + findAuthors[i]['name'] + "'"
                else:
                    resultStr = resultStr + "'" + findAuthors[i]['name'] + "', "

            resultStr = resultStr + "]"
            searchDict['firstAuthorInfo'][title] = findAuthors[0]['name']
            searchDict['fullAuthorInfo'][title] = resultStr
    
    else:
        for i in range(len(extractedResult['gScholarQResults'])):
            title = extractedResult['gScholarQResults'][i]['title']

            #check if the keys under inline_links contain cited by, if not set to 0.
            if(('cited_by' in extractedResult['gScholarQResults'][i]['inline_links'].keys()) == False):
                #check if it already exists
                if((title in searchDict['citationInfo'].keys()) == False):

                    searchDict['citationInfo'][title] = 0
                    searchDict['googleScholarLink'][title] = "Link Not Available"
            else:

                numCitedBy = extractedResult['gScholarQResults'][i]['inline_links']['cited_by']['total']
                searchDict['citationInfo'][title] = numCitedBy

                if(('versions' in extractedResult['gScholarQResults'][0]['inline_links'].keys())):
                    googleScholarLink = extractedResult['gScholarQResults'][0]['inline_links']['versions']['link']
                    searchDict['googleScholarLink'][title] = googleScholarLink
                else:
                    searchDict['googleScholarLink'][title] = "Link Not Available"


            #find author(s) if it is populated
            if(('authors' in extractedResult['gScholarQResults'][i]['publication_info']) == False):
                searchDict['firstAuthorInfo'][title] = "No information available"
                if((('summary' in extractedResult['gScholarQResults'][i]['publication_info']) == True)):
                    if("-" in extractedResult['gScholarQResults'][i]['publication_info']['summary']):
                        dashIndex = extractedResult['gScholarQResults'][i]['publication_info']['summary'].index("-")
                        searchDict['fullAuthorInfo'][title] = extractedResult['gScholarQResults'][i]['publication_info']['summary'][0:dashIndex]
                    else:
                        searchDict['fullAuthorInfo'][title] = "No information available"
                else:
                    searchDict['fullAuthorInfo'][title] = "No information available"
            else:
                findAuthors = extractedResult['gScholarQResults'][i]['publication_info']['authors']
                resultStr = "["
                for i in range(len(findAuthors)):
                    if (i == len(findAuthors) - 1):
                        resultStr = resultStr + "'" + findAuthors[i]['name'] + "'"
                    else:
                        resultStr = resultStr + "'" + findAuthors[i]['name'] + "', "

                resultStr = resultStr + "]"
                searchDict['firstAuthorInfo'][title] = findAuthors[0]['name']
                searchDict['fullAuthorInfo'][title] = resultStr

    #populate the last dictionary with full title + first author for better levenshtein matching
    for key in searchDict['firstAuthorInfo']:
        if(searchDict['firstAuthorInfo'][key] != "No information available"):
            newStr = "" + key + " " + searchDict['firstAuthorInfo'][key]
        else: 
            newStr = "" + key
        searchDict['titleAuthorStr'][newStr] = key

    return searchDict

fixture = {}
def getGoogleScholarCitation(row, serp_api_key):

    """ From the JSON object produced by saveRawSerpApiAsDict(), 
        extract title, author, and citation information based on rules.
        Called in main() and applied to each row of the table output from getPMArticles()

    parameters
        row: applied to each row of the table output from getPMArticles()

    Returns:
        results: Output into 4 new columns: 
                    title found on Google Scholar (could have different capitalization, abbrevation, spacing...etc), 
                    number of citation, 
                    levenshtein probability, and 
                    a list of full authors from Google Scholar
    """
    searchTitle = str(row['titleAuthorStr']) #get search string
    results = serpAPI(searchTitle, serp_api_key) #search on google scholar
    fixture[searchTitle] = results
    appendedResults = saveRawSerpApiAsDict(results) #save results as json dictionary
    
    #create 4 new columns
    if(len(appendedResults) == 0):
        dictArticlesToMatch = {"citationInfo": {}, 'firstAuthorInfo': {}, 'fullAuthorInfo': {}, 'titleAuthorStr': {}, 'googleScholarLink': {}}
    else:
        dictArticlesToMatch = serpApiExtract(appendedResults)
    strOptions = dictArticlesToMatch['titleAuthorStr'].keys()
    if(len(strOptions) == 0):
        result = ["NA", "NA", "NA", "NA", "NA"]
        return result
    
    elif(len(strOptions) == 1):
        title = list(dictArticlesToMatch['titleAuthorStr'].values())[0]
        levenP = fuzz.token_set_ratio(searchTitle, list(dictArticlesToMatch['titleAuthorStr'].keys())[0])
        result = [title, dictArticlesToMatch['citationInfo'][title], levenP, dictArticlesToMatch['fullAuthorInfo'][title], dictArticlesToMatch['googleScholarLink'][title]]
        return result
    
    elif(len(strOptions) > 1):
        result = process.extractOne(str(searchTitle), strOptions) #extract the highest probability of match
        title = dictArticlesToMatch['titleAuthorStr'][result[0]]
        result = [title, dictArticlesToMatch['citationInfo'][title], result[1], dictArticlesToMatch['fullAuthorInfo'][title], dictArticlesToMatch['googleScholarLink'][title]]
        return result

def getLastUpdatedCitations(containerName):

    """ Retrieve the number of citation for each article from the most recent update.
        Called in trackCitationChanges()

    parameters
        containerName: containerName on azure cosmosdb

    Returns:
        lastUpdateResults: citation counts

    """
    container = init_cosmos(containerName)
    lastUpdateResults = {'citationInfo': {}}
    numCitation = 0
    for item in container.query_items(query=str('SELECT * FROM ' + containerName), enable_cross_partition_query=True):
        title = item['data']['title']
        numCitation = item['data']['trackingChanges'][len(item['data']['trackingChanges'])-1]['numCitations']
        lastUpdateResults['citationInfo'][title] = numCitation
    return lastUpdateResults

def trackCitationChanges(table):

    """ Calculate the change in the number of citations
        Called in main()

    parameters
        table: table of articles

    Returns:
        table: dataframe with added columns of added citation count

    """
    #format the input table into a dictionary of {title: citation count}
    table = table.reset_index()
    if ('index' in table.columns):
        del table['index']
    retrievalResults = {"citationInfo": {}}
    tableLength = len(table['title'])
    for row in range(tableLength):
        retrievalResults['citationInfo'][table['title'][row]] = int(table['numCitations'][row])
    table['additionalCitationCount'] = 0
    #retrieve the counts from the last update
    lastUpdateResults = getLastUpdatedCitations('pubmed')
    for key in (getLastUpdatedCitations('pubmed_ignore')['citationInfo']):
        lastUpdateResults['citationInfo'][key] = getLastUpdatedCitations('pubmed_ignore')['citationInfo'][key]
    for key in retrievalResults['citationInfo']:
        if(key in lastUpdateResults.keys()):
            table.loc[table['title'] == key, 'additionalCitationCount'] = retrievalResults['citationInfo'][key] - lastUpdateResults['citationInfo'][key]
        else:
            table.loc[table['title'] == key, 'additionalCitationCount'] = 0
    return table

def fetchCurrentDataAndUpdate(containerName):
    """ Retrieve all existing records and add in updates
        Called in makeCSVJSON()

    parameters
        containerName: containerName

    Returns:
        result: dictionary of lists of articles

    """
    container = init_cosmos(containerName)
    result = defaultdict(list)
    for item in container.query_items(query = str('SELECT * FROM ' + containerName), enable_cross_partition_query=True):
        result[item['id']] = item['data']
    return result


def makeCSVJSON(table, containerChosen: str, forUpdate: bool):
  
    """ Add new records to the existing records and update container
        Called in main()

    parameters
        table: dataframe with articles

    Returns:
        upserts articles

    """
    container = init_cosmos( 'pubmed')
    container_ignore = init_cosmos( 'pubmed_ignore')
    container_chosen = init_cosmos( containerChosen)
    if(forUpdate):
        data = fetchCurrentDataAndUpdate( 'pubmed')
        data_ignore = fetchCurrentDataAndUpdate('pubmed_ignore')
        for key in data_ignore:
            data[key] = data_ignore[key]
    else: 
        data = defaultdict(list)
    d_timeseries = defaultdict(list)
    #format table into dictionary
    for row in range(len(table['pubmedID'])):
        d_trackingChanges = {}
        d_articleInfo = {}
        for k in table.columns:  
            if (k == 'pubmedID'):
                d_articleInfo[k] = str(int(float(table[k][row])))
            elif (k in ['pmcID', 'nlmID', 'journalTitle', 'title', 'creationDate', 'affiliation', 'locID',
                        'countryOfPub', 'language','grantNum', 'fullAuthor', 'source', 
                        'fullAuthorEdited', 'firstAuthor', 'meshT', "abstract",
                        'titleAuthorStr', 'foundInGooScholar', 
                        'fullAuthorGooScholar', 'googleScholarLink',
                        'rxnormIDspacy', 'rxnormTermspacy', 'rxnormStartChar', 'rxnormEndChar',
                        'umlsIDspacy', 'umlsTermspacy', 'umlsStartChar', 'umlsEndChar', 
                        'snomedIDs', 'snomedNames', 'termFreq']):
                d_articleInfo[k] = str(table[k][row])
            elif( k in ['pubYear', 'levenProb']):
                if( (k == "levenProb") & (table[k][row] == "NA")):
                    d_articleInfo[k] = int(0)
                else:
                    d_articleInfo[k] = int(float(table[k][row]))
            elif( k in ['additionalCitationCount', 'numCitations', 'datePulled']):
                d_trackingChanges['t'] = int(parse(table["datePulled"][row]).timestamp())
                if( k == 'datePulled'):
                    d_trackingChanges[k] = str(table[k][row])
                else:
                    if(table[k][row] == 'NA'):
                        d_trackingChanges[k] = 0
                    else:
                        d_trackingChanges[k] = int(float(table[k][row]))


        id = "PMID: " + str(int(float(table['pubmedID'][row])))
        if(id in data.keys()):    
            if((id in d_timeseries.keys()) == False):
                for i in range(len(data[id]['trackingChanges'])):
                    d_timeseries[id].append(data[id]['trackingChanges'][i])
        d_timeseries[id].append(d_trackingChanges) 
        data[id] = d_articleInfo
        data[id]['trackingChanges'] = d_timeseries[id]
    
    data = dict(data)
    #for articles in the ignore list, add to the ignore container; otherwise, add to the pubmed container
    ignore_list = getExistingIDandSearchStr( 'pubmed_ignore')[0]
    for k, v in data.items(): 
        if(k[6:len(k)] in ignore_list):
            container_ignore.upsert_item({
                    'id': k,
                    'data': v
                }
            )
        
        else:
            container_chosen.upsert_item({
                    'id': k,
                    'data': v
                }
            )

def getTimeOfLastUpdate():

    """ Not every article has the same last date of update. Find the most recent date. 
        Called in main()

    parameters
        
    Returns:
        dateOfLastUpdate: most recent data pull

    """
    db = get_db()
    # container = init_cosmos('pubmed')
    dateOfLastUpdate = date.datetime.strptime("01-01-2022", "%m-%d-%Y")
    # for item in container.query_items(query='SELECT * FROM beta', enable_cross_partition_query=True):
    for item in db.find('beta'):
        testDate = date.datetime.strptime(item['data']['trackingChanges'][len(item['data']['trackingChanges'])-1]['datePulled'], "%m-%d-%Y")
        if(dateOfLastUpdate < testDate):
            dateOfLastUpdate = testDate
    dateOfLastUpdate = str(dateOfLastUpdate)
    dateOfLastUpdate = dateOfLastUpdate[5:7] + "-" + dateOfLastUpdate[8:10] + "-" + dateOfLastUpdate[0:4]
    return dateOfLastUpdate

def getExistingIDandSearchStr(containerName):

    """ Get a list of PMIDs and a list of title-author search strings
        Called in main()

    parameters
        containerName: containerName

    Returns:
        result: existing pubmed IDs,
                existing articles' title and author string

    """
    db = get_db()
    result = []
    exisitingIDs = []
    exisitingTitleAuthorStr = []
    for item in db.find(containerName):
        exisitingIDs.append(item['data']['pubmedID'])
        exisitingTitleAuthorStr.append(item['data']['titleAuthorStr'])
    result = [exisitingIDs, exisitingTitleAuthorStr]

    return result

def retrieveAsTable( fullRecord: bool, containerName):

    """ Retrieves the data as a dataframe

    parameters
        fullRecord: timeseries yes or no

    Returns:
        df: dataframe, either static or timeseries data

    """
    container = init_cosmos( containerName)
    pmcID, pubmedID, nlmID, journalTitle, title = [],[],[],[],[]
    creationDate, affiliation, locID, countryOfPub, language = [],[],[],[],[]
    grantNum, fullAuthor, abstract, meshT, source, fullAuthorEdited = [],[],[],[],[],[]
    firstAuthor, pubYear, titleAuthorStr, datePulled = [],[],[],[]
    foundInGooScholar, numCitations , levenProb, fullAuthorGooScholar, googleScholarLink = [],[],[],[],[]
    rxnormIDspacy, rxnormTermspacy , rxnormStartChar, rxnormEndChar = [],[],[],[]
    umlsIDspacy, umlsTermspacy , umlsStartChar, umlsEndChar = [],[],[],[]
    snomedIDs, snomedNames , termFreq = [],[],[]

    colNames = ['pmcID', 'pubmedID', 'nlmID', 'journalTitle', 'title',
           'creationDate', 'affiliation', 'locID', 'countryOfPub', 'language',
           'grantNum', 'fullAuthor', 'abstract', 'meshT', 'source', 'fullAuthorEdited',
           'firstAuthor', 'pubYear', 'titleAuthorStr', 'datePulled',
            'foundInGooScholar','numCitations', 'levenProb', 'fullAuthorGooScholar', 'googleScholarLink',
            'rxnormIDspacy', 'rxnormTermspacy', 'rxnormStartChar', 'rxnormEndChar',
                'umlsIDspacy', 'umlsTermspacy', 'umlsStartChar', 'umlsEndChar', 'snomedIDs', 'snomedNames', 'termFreq'
               ]

    for item in container.query_items(query = str('SELECT * FROM ' + containerName), enable_cross_partition_query=True):
        lastIndex = len(item['data']['trackingChanges']) - 1
        if(fullRecord == False):
            startIndex = lastIndex
        else:
            startIndex = 0
        for i in range(startIndex, lastIndex + 1):
            pmcID.append(item['data']['pmcID'])
            pubmedID.append(item['data']['pubmedID'])
            nlmID.append(item['data']['nlmID'])
            journalTitle.append(item['data']['journalTitle'])
            title.append(item['data']['title'])

            creationDate.append(item['data']['creationDate'])
            affiliation.append(item['data']['affiliation'])
            locID.append(item['data']['locID'])
            countryOfPub.append(item['data']['countryOfPub'])
            language.append(item['data']['language'])

            grantNum.append(item['data']['grantNum'])
            fullAuthor.append(item['data']['fullAuthor'])
            abstract.append(item['data']['abstract'])
            meshT.append(item['data']['meshT'])
            source.append(item['data']['source'])
            fullAuthorEdited.append(item['data']['fullAuthorEdited'])

            firstAuthor.append(item['data']['firstAuthor'])
            pubYear.append(item['data']['pubYear'])
            titleAuthorStr.append(item['data']['titleAuthorStr'])
            
            datePulled.append(item['data']['trackingChanges'][i]['datePulled'])
            foundInGooScholar.append(item['data']['foundInGooScholar'])
            numCitations.append(item['data']['trackingChanges'][i]['numCitations'])
            levenProb.append(item['data']['levenProb'])
            fullAuthorGooScholar.append(item['data']['fullAuthorGooScholar'])
            googleScholarLink.append(item['data']['googleScholarLink'])
            
            rxnormIDspacy.append(item['data']['rxnormIDspacy'])
            rxnormTermspacy.append(item['data']['rxnormTermspacy'])
            rxnormStartChar.append(item['data']['rxnormStartChar'])
            rxnormEndChar.append(item['data']['rxnormEndChar'])
            umlsIDspacy.append(item['data']['umlsIDspacy'])
            umlsTermspacy.append(item['data']['umlsTermspacy'])
            umlsStartChar.append(item['data']['umlsStartChar'])
            umlsEndChar.append(item['data']['umlsEndChar'])
            snomedIDs.append(item['data']['snomedIDs'])
            snomedNames.append(item['data']['snomedNames'])
            termFreq.append(item['data']['termFreq'])

        df = pd.DataFrame([pmcID, pubmedID, nlmID, journalTitle, title, creationDate, affiliation, 
                           locID, countryOfPub, language, grantNum, fullAuthor, abstract, meshT, source, 
                           fullAuthorEdited, firstAuthor, pubYear, titleAuthorStr, datePulled,
                           foundInGooScholar, numCitations, levenProb, fullAuthorGooScholar, googleScholarLink,
                           rxnormIDspacy, rxnormTermspacy, rxnormStartChar, rxnormEndChar, umlsIDspacy, 
                           umlsTermspacy, umlsStartChar, umlsEndChar, snomedIDs, snomedNames, termFreq
                         ]).T
        df.columns = colNames
    return df

def moveItemToIgnoreContainer( pmIDList, fromContainerName: str, toContainerName: str):

    """ Moves one or many articles from one container to another

    parameters
        pmIDList: IDs to move
        fromContainerName: departure ontainer
        toContainerName: destination container

    Returns:
        Message indicating task success

    """
    fromContainer = init_cosmos( fromContainerName)
    toContainer = init_cosmos( toContainerName)
    for i in range(len(pmIDList)):
        pmID = pmIDList[i]
        #check if the article exists in the current container.
        checkID = getExistingIDandSearchStr(fromContainerName)[0]
        if(str("" + pmID) in checkID):
            #move out of current container to another container
            for item in fromContainer.query_items( query = str('SELECT * FROM ' + fromContainerName), enable_cross_partition_query=True):
                if(item['id'] == str('PMID: ' + pmID)):
                    #first move to the other container
                    toContainer.upsert_item({
                            'id': item['id'],
                            'data': item['data']
                        }
                    )

                    #then delete from current container
                    fromContainer.delete_item(item, partition_key = item['id'])
                    print("" + pmID + " has been moved to the new and deleted from the old.")
        else:
            print("" + pmID + " is not in this container. Check the direction of migration.")
            
def identifyNewArticles(table):

    """ Identify new articles for a limited search. Used to search for new articles on a daily basis. 
        Called in main()

    parameters
        table: dataframe with articles

    Returns:
        result: dataframe with only new articles

    """
    trueArticles = getExistingIDandSearchStr('pubmed')
    ignoreArticles = getExistingIDandSearchStr('pubmed_ignore')
    allExistingIDs = list(np.append(trueArticles[0], ignoreArticles[0]))
    newArticles = list(set(list(table['pubmedID'])) - set(allExistingIDs))
    if(len(newArticles) > 0):
        outputTable = table[table['pubmedID'].isin(newArticles)]
        result = [outputTable, len(newArticles)]
    else:
        outputTable = pd.DataFrame()
        result = [outputTable, len(newArticles)]

    return result

# def includeMissingCurrentArticles(table):
#     """ For the 27 articles that were added in manually (any other manually added articles in the future), 
#         we need to do add them to the total list of articles to search for.
#         Called in main()

#     parameters
#         table: dataframe with articles

#     Returns:
#         outputTable: dataframe with articles that were previously manually added

#     """
#     trueArticles = getExistingIDandSearchStr('pubmed')
#     ignoreArticles = getExistingIDandSearchStr('pubmed_ignore')
#     allExistingIDs = list(np.append(trueArticles[0], ignoreArticles[0]))
#     missingArticles = list(set(allExistingIDs) - set(list(table['pubmedID'])))
#     outputTable = getPMArticles(missingArticles)
#     outputTable = pd.concat([outputTable, table], axis=0)
#     outputTable = outputTable.reset_index()
#     if ('index' in outputTable.columns):
#         del outputTable['index']
            
#     return outputTable

def findUniqueAuthors(multipleAuthors: bool, placeHolder, articleAuthors):

    """ finds unique authors regardless of authorship
        Called in main()

    parameters
        placeHolder: empty list or list of existing authors
        articleAuthors: list of authors to filter

    Returns:
        placeHolder: list of unique authors identified

    """
    indexStart = 1
    indexFQ = 0
    indexSQ = 0
    i = 0
    while i < len(articleAuthors)-1:
        if((articleAuthors[i] == "'") & (articleAuthors[i+1] == ",")):
            indexFQ = i
            indexSQ = i + 3
            author = articleAuthors[indexStart:indexFQ]
#                 author = author.replace(",", "")
            author = author.replace("\"", "")
            if(author[0] == " "):
                author = author[1:-1]

            if(len(placeHolder) > 0):
                try:
                    highestOne = process.extractOne(author, placeHolder)
                except RecursionError:
                    indexStart = indexSQ + 1
                    i = indexSQ + 1
                else:
                    # highestOne = process.extractOne(author, placeHolder)
                    if(highestOne[1] < 95):
                        if((fuzz.token_set_ratio(author, highestOne[0])) < 95):
                            if((author != "") & (author != ', ')):
                                author = re.sub(',|"', '', author)
                                author = re.sub("'", '', author)
                                if((author[0] == " ") | (author[0] == "'")):
                                    author = author[1:-1]

                                placeHolder.append(author)

                    indexStart = indexSQ + 1
                    i = indexSQ + 1
            else:

                placeHolder.append(author)
                indexStart = indexSQ + 1
                i = indexSQ + 1
        else:
            i += 1
    # placeHolder = sorted(placeHolder)
    return placeHolder

def findUniqueFirstAuthors(multipleAuthors: bool, placeHolder, articleAuthors):

    """ uses levenshtein fuzzy matching to find unique first authors, not unique authors (besides first authors)

    parameters
        placeHolder: empty list or list of existing first authors
        articleAuthors: list of first authors to filter

    Returns:
        placeHolder: list of unique first authors identified

    """
    indexStartQ = 1
    indexEndQ = 0
    indexStart = 0
    i = 0

    indexEndQ = len(articleAuthors)
    indexStartQ = 0
    author = articleAuthors[indexStart:indexEndQ]

    if(author != ""):
        if(author[0] == " "):
            author = author[1:-1]
        
        if(len(placeHolder) > 0):
            try:
                highestOne = process.extractOne(author, placeHolder)
            except RecursionError:
                indexStart = indexStartQ + 1
                i = indexStartQ + 1
            else:
                # highestOne = process.extractOne(author, placeHolder)
                if(highestOne[1] < 95):
                    if((fuzz.token_set_ratio(author, highestOne[0])) < 95):
                        if((author != "") & (author != ', ')):
                            author = re.sub(',|"', '', author)
                            author = re.sub("'", '', author)
                            if((author[0] == " ") | (author[0] == "'")):
                                author = author[1:-1]
                            placeHolder.append(author)
                indexStart = indexStartQ + 1
                i = indexStartQ + 1
        else:

            placeHolder.append(author)
            indexStart = indexStartQ + 1
            i = indexStartQ + 1
    
    # placeHolder = sorted(placeHolder)
    return placeHolder

def authorSummary(authorDf):

    """ Creates author summary table from the articles

    parameters
        authorDf: dataframe of articles with authorship info

    Returns:
        finalAuthorDf: dataframe of authors, first authors, unique authors, and unique first authors grouped by year

    """
    authorDf['firstAuthor'] = authorDf.apply(lambda x: x['firstAuthor'].replace("'", ""), axis = 1)
    firstAuthorDf = authorDf.groupby(['pubYear'])['firstAuthor'].apply(', '.join).reset_index()

    authorDf = authorDf.groupby(['pubYear'])['fullAuthor'].apply(', '.join).reset_index()
    #full authors
    placeHolder = []
    authorDf['cleanFullAuthors'] = authorDf.apply(lambda x: x['fullAuthor'].replace("[", ""), axis = 1)
    authorDf['cleanFullAuthors'] = authorDf.apply(lambda x: x['cleanFullAuthors'].replace("]", ""), axis = 1)
    authorDf['cleanFullAuthors'] = authorDf.apply(lambda x: re.sub('([A-Za-z])(,)', '\\1', x['cleanFullAuthors']), axis = 1)
    authorDf['uniqueAuthors'] = authorDf.apply(lambda x: findUniqueAuthors(True, placeHolder, x['cleanFullAuthors']), axis = 1)
    authorDf['numberNewAuthors'] = len(authorDf['uniqueAuthors'][0])
    authorDf['cumulativeAuthors'] = len(authorDf['uniqueAuthors'][0])
    for i in range(1,authorDf.shape[0]):
        numberNewAuthors = len(list(set(authorDf['uniqueAuthors'][i]) - set(authorDf['uniqueAuthors'][i-1])))
        authorDf['numberNewAuthors'][i] = numberNewAuthors
        authorDf['cumulativeAuthors'][i] = numberNewAuthors + authorDf['cumulativeAuthors'][i-1]
        
    #first authors
    faPlaceHolder = []
    firstAuthorDf['uniqueFirstAuthors'] = firstAuthorDf.apply(lambda x: findUniqueFirstAuthors(True, faPlaceHolder, x['firstAuthor']), axis = 1)
    firstAuthorDf['numberNewFirstAuthors'] = len(firstAuthorDf['uniqueFirstAuthors'][0])
    firstAuthorDf['cumulativeFirstAuthors'] = len(firstAuthorDf['uniqueFirstAuthors'][0])
    for i in range(1,firstAuthorDf.shape[0]):
        numberNewAuthors = len(list(set(firstAuthorDf['uniqueFirstAuthors'][i]) - set(firstAuthorDf['uniqueFirstAuthors'][i-1])))
        firstAuthorDf['numberNewFirstAuthors'][i] = numberNewAuthors
        firstAuthorDf['cumulativeFirstAuthors'][i] = numberNewAuthors + firstAuthorDf['cumulativeFirstAuthors'][i-1]
    
    #merge
    finalAuthorDf = pd.concat([firstAuthorDf,\
                authorDf[['fullAuthor', 'cleanFullAuthors', 'uniqueAuthors', 'numberNewAuthors', 'cumulativeAuthors']]], axis=1)
    
    return(finalAuthorDf)

def pushTableToDB(summaryTable, containerName, idName):

    """ pushes summary table to CosmosDB and store as a single object.

    parameters
        summaryTable: dataframe of articles

    Returns:
        Message indicating task success

    """
    container = init_cosmos(containerName)
    for item in container.query_items(query = str('SELECT * FROM ' + containerName), enable_cross_partition_query=True):
        if(item['id'] == idName):
            print("Specified ID Name already exists. Updating...")
    results = {}
    if ('abstract' in summaryTable.columns):
        del summaryTable['abstract']
    results['data'] = summaryTable.to_json()
    results['id'] = idName
    container.upsert_item(body = results)
    print("Update completed.")
        
        
def retrieveAuthorSummaryTable(containerName, selectedID):

    """ Retrieves the author data as a dataframe
        Called in dataupdate()

    parameters
        containerName: containerName
        selectedID: document id from the list cached dataframes in the dashboard container

    Returns:
        outputDf: dataframe

    """
    container = init_cosmos(containerName)
    for item in container.query_items(query = str('SELECT * FROM ' + containerName), enable_cross_partition_query=True):
        if(item['id'] == selectedID):
            authorSum = json.dumps(item['data'], indent = True)
            authorSum = json.loads(authorSum)
            outputDf = pd.DataFrame(pd.read_json(authorSum))
            return outputDf

def checkAuthorRecord(newArticleTable, currentAuthorSummary, monthlyUpdate = False):

    """ Checks for new authors and add to the list of authors
        Called in dataupdate()

    parameters
        newArticleTable: dataframe of newly identified articles
        currentAuthorSummary: current dataframe with summary authorship info (grouped by year)
        monthlyUpdate: indicating whether this is during daily or monthly update

    Returns:
        currentAuthorSummary: updated dataframe with added authorship

    """
    placeHolder = list(currentAuthorSummary['uniqueAuthors'])[0]
    faPlaceHolder = list(currentAuthorSummary['uniqueFirstAuthors'])[0]

    #clean first author 
    newArticleTable['firstAuthor'] = newArticleTable.apply(lambda x: x['firstAuthor'].replace("'", ""), axis = 1)
    #clean full author
    newArticleTable['cleanFullAuthors'] = newArticleTable.apply(lambda x: x['fullAuthor'].replace("[", ""), axis = 1)
    newArticleTable['cleanFullAuthors'] = newArticleTable.apply(lambda x: x['cleanFullAuthors'].replace("]", ""), axis = 1)
    newArticleTable['cleanFullAuthors'] = newArticleTable.apply(lambda x: re.sub('([A-Za-z])(,)', '\\1', x['cleanFullAuthors']), axis = 1)
    #find unique authors and first authors
    placeHolder = newArticleTable.apply(lambda x: findUniqueAuthors(True, placeHolder, x['cleanFullAuthors']), axis = 1)[newArticleTable.shape[0] - 1]
    faPlaceHolder = newArticleTable.apply(lambda x: findUniqueFirstAuthors(True, faPlaceHolder, x['firstAuthor']), axis = 1)[newArticleTable.shape[0] - 1]
    
    
    currentAuthorSummary['uniqueAuthors'] = [placeHolder]
    currentAuthorSummary['uniqueFirstAuthors'] = [faPlaceHolder]

    if(monthlyUpdate == True):
        #recalculate the results as some articles may have been moved to the ignore container
        currentYear = int(date.datetime.now().strftime("%m-%d-%Y")[6:10])
        newArticleTable['firstAuthor'] = newArticleTable.apply(lambda x: x['firstAuthor'].replace("'", ""), axis = 1)
        firstAuthorDf = newArticleTable.groupby(['pubYear'])['firstAuthor'].apply(', '.join).reset_index()
        fullAuthorDf = newArticleTable.groupby(['pubYear'])['fullAuthor'].apply(', '.join).reset_index()
        
        #full authors
        fullAuthorDf['cleanFullAuthors'] = fullAuthorDf.apply(lambda x: x['fullAuthor'].replace("[", ""), axis = 1)
        fullAuthorDf['cleanFullAuthors'] = fullAuthorDf.apply(lambda x: x['cleanFullAuthors'].replace("]", ""), axis = 1)
        fullAuthorDf['cleanFullAuthors'] = fullAuthorDf.apply(lambda x: re.sub('([A-Za-z])(,)', '\\1', x['cleanFullAuthors']), axis = 1)    
        firstAuthorDf = pd.DataFrame(firstAuthorDf)

        if(sum(firstAuthorDf['pubYear'] == currentYear) == 0):
            currentYear = currentYear - 1
            
        currentAuthorSummary['firstAuthor'] = list(firstAuthorDf[firstAuthorDf['pubYear'] == currentYear]['firstAuthor'])
        currentAuthorSummary['fullAuthor'] = list(fullAuthorDf[fullAuthorDf['pubYear'] == currentYear]['fullAuthor'])
        currentAuthorSummary['cleanFullAuthors'] = list(fullAuthorDf[fullAuthorDf['pubYear'] == currentYear]['cleanFullAuthors'])

    currentAuthorSummary['cumulativeFirstAuthors'] = len(list(currentAuthorSummary['uniqueFirstAuthors'])[0])
    currentAuthorSummary['cumulativeAuthors'] = len(list(currentAuthorSummary['uniqueAuthors'])[0])

    
    
def calculateNewAuthors(currentAuthorSummary):

    """ Calculate the number of new authors and update summary statistics

    parameters
        currentAuthorSummary: current dataframe with summary authorship info (grouped by year)

    Returns:
        currentAuthorSummary: two updated columns:
                                number of new first authors,
                                number of new authors in total

    """
    lastRowIndex = currentAuthorSummary['numberNewFirstAuthors'].shape[0]
    currentAuthorSummary['numberNewFirstAuthors'][lastRowIndex-1] = currentAuthorSummary['cumulativeFirstAuthors'][lastRowIndex-1] - currentAuthorSummary['cumulativeFirstAuthors'][lastRowIndex-2]
    currentAuthorSummary['numberNewAuthors'][lastRowIndex-1] = currentAuthorSummary['cumulativeAuthors'][lastRowIndex-1] - currentAuthorSummary['cumulativeAuthors'][lastRowIndex-2]
                
#functions for NER
def scispacyNER(text, lowerThreshold, upperThreshold, nlp):

    """ SciSpacy NER applied to YouTube transcripts

    parameters
        text: abstract or transcript
        lowerThreshold: lower threshold for NER
        upperThreshold: upper threshold for NER
        nlp: corpus

    Returns:
        currentAuthorSummary: two updated columns:
                                number of new first authors,
                                number of new authors in total

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

    """ Initializes spacy corpus and linker
        Called in scispacyOntologyNER()

    parameters
        corpus: corpus
        ontology: ontology

    Returns:
        nlp: model

    """
    # import pathlib
    # path = pathlib.Path(__file__).parent / 'en_ner_bc5cdr_md/en_ner_bc5cdr_md/en_ner_bc5cdr_md-0.5.0'
    # path = "/lib/en_core_sci_md/en_ner_bc5cdr_md/en_ner_bc5cdr_md/en_ner_bc5cdr_md-0.5.0"
    # nlp = spacy.load(path) # en_core_sci_sm, en_ner_bc5cdr_md
    nlp = spacy.load('en_ner_bc5cdr_md')
    nlp.add_pipe("scispacy_linker", config={"resolve_abbreviations": True, "linker_name": ontology})
    return nlp

def scispacyOntologyNER(inputData, ontology, corpus = "en_ner_bc5cdr_md"):

    """ Loads spacy corpus and linker. Applies scispacyNER to each row or item. 
        Called in main()

    parameters
        inputData: dataframe of videos with transcript
        ontology: ontology
        corpus: default corpus en_ner_bc5cdr_md

    Returns:
        inputData: the updated dataframe or dictionary

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
    """ Maps transcript to SNOMED terms

    parameters
        ids: umls ids
        apiKey: UMLS api key

    Returns:
        [snomed id, name of the term]

    """
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

    """ Loads spacy corpus and linker. Applies scispacyNER to each row or item. 
        Called in main()
    parameters
        inputData: dataframe of videos with abstract/transcripts
        apiKey: UMLS api key

    Returns:
        inputData: dataframe with added snomed ids and names

    """

    if (isinstance(inputData, pd.DataFrame)):
        inputData[["snomedIDs", "snomedNames"]] = inputData.apply(lambda x: mapToSnomed(list(x['umlsIDspacy']), apiKey), axis = 1, result_type='expand')
    
    elif(isinstance(inputData, dict)):
        ids, terms= mapToSnomed(inputData['umlsIDspacy'], apiKey)
        inputData["snomedIDs"] = list(ids)
        inputData["snomedNames"] = list(terms)

    return inputData

def termFreq(eachArticle):
    """ Finds the frequency of each term 
        Called in findTermFreq()

    parameters
        eachArticle: called in apply() on each row of the dataframe

    Returns:
        termAndFreqStr: concatenated string of terms and frequencies

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

    """ Finds the frequency of each term 
        Called in main()
        
    parameters
        inputdata: dataframe of articles

    Returns:
        inputData: dataframe with new column with terms(frequency)

    """
    if (isinstance(inputData, pd.DataFrame)):
        inputData['termFreq'] = inputData.apply(lambda x: termFreq(x), axis = 1)
    
    elif(isinstance(inputData, dict)):
        termsWFreq = termFreq(inputData)
        inputData["termFreq"] = termsWFreq

    return inputData
                
def update_data():

    #initialize the cosmos db dictionary
    dateMY = "" + date.datetime.now().strftime("%m-%d-%Y")[0:2] + date.datetime.now().strftime("%m-%d-%Y")[5:10]
    # secret_api_key = Keys.SERPAPI_KEY #SERPAPI key
    
    # #search terms/strings
    searchAll = ['ohdsi', 'omop', 'Observational Medical Outcomes Partnership Common Data Model', \
             '"Observational Medical Outcomes Partnership"', '"Observational Health Data Sciences and Informatics"']  
    # searchAll = addTheseArticles   #27 without relevent key words in the title/abstract/author
    # searchAll = ['36395615', '36389281']
    #first search pubmed
    finalTable = getPMArticles(searchAll)
    finalTable = finalTable[finalTable['pubYear'] > 2010]
    # finalTable = includeMissingCurrentArticles(finalTable)
    numNewArticles = 0
    #check if an update has already been performed this month
    lastUpdated = getTimeOfLastUpdate()[0:2] + getTimeOfLastUpdate()[5:10]

    if(lastUpdated == dateMY):
        print("Already updated this month on " + getTimeOfLastUpdate())
        print("Identifying new articles...")
        #check if an update has already been performed today
        if(getTimeOfLastUpdate() != str("" + date.datetime.now().strftime("%m-%d-%Y"))):
            #if not search and filter for new articles
            finalTable, numNewArticles = identifyNewArticles(finalTable)
            #if no new articles are found. End the update/script.
            if(numNewArticles == 0):
                print("" + str(numNewArticles) + " new articles found. Update is not needed." )
            else:
                print("" + str(numNewArticles) + " new articles found. Proceed to update..." )
        else:
            print("Already checked for new articles today. Come back later:)")
    else:
        print("First update of the month.")

    #if it is the first update of the month, or if new articles have been found within the same month, upsert those articles
    if((lastUpdated != dateMY) or (numNewArticles > 0)):
        #search google scholar and create 4 new columns
        finalTable[
            ['foundInGooScholar', 'numCitations', 'levenProb', 'fullAuthorGooScholar', 'googleScholarLink']
        ] = finalTable.apply(
            lambda x: getGoogleScholarCitation(x, current_app.config['SERPAPI_KEY']), axis = 1, result_type='expand'
        )
        finalTable = finalTable.reset_index()
        if ('index' in finalTable.columns):
            del finalTable['index']
        if ('level_0' in finalTable.columns):
            del finalTable['level_0']
            
        newArticlesTable, numNewArticles = identifyNewArticles(finalTable)
        
        if(numNewArticles > 0):
            #NER and mapping of abstracts to SNOMED
            newArticlesTable = scispacyOntologyNER(newArticlesTable, "rxnorm")
            newArticlesTable = scispacyOntologyNER(newArticlesTable, "umls")
            newArticlesTable = mapUmlsToSnomed(newArticlesTable, Keys.UMLSAPI_KEY)
            newArticlesTable = findTermFreq(newArticlesTable)
            newArticlesTable = newArticlesTable.reset_index(drop = True)
            # if ('index' in newArticlesTable.columns):
            #     del newArticlesTable['index']
            #push new articles
            makeCSVJSON(newArticlesTable, 'pubmed', True)
            asOfDate =  retrieveAsTable(False, 'pubmed')
            pushTableToDB(asOfDate, 'dashboard', 'pubmed_articles')

            # newArticlesTable.to_csv("tempNewArticle.csv")

            #author summary tables
            currentAuthorSummaryTable = retrieveAuthorSummaryTable('dashboard', 'pubmed_authors')
            numRows = pd.DataFrame(currentAuthorSummaryTable).shape[0]
            #past years
            pastYears = pd.DataFrame(currentAuthorSummaryTable.iloc[0:-1])
            #this year
            asOfThisYear = pd.DataFrame(currentAuthorSummaryTable.iloc[numRows - 1]).T
            #look for new authors and add to the list
            checkAuthorRecord(newArticlesTable, asOfThisYear)
            #rbinds
            currentAuthorSummaryTable = pd.concat([pastYears, asOfThisYear])
            #update summary statistics
            calculateNewAuthors(currentAuthorSummaryTable)
            pushTableToDB(currentAuthorSummaryTable, 'dashboard', 'pubmed_authors')
            
        if(lastUpdated != dateMY):
            #merge in NER and snomed mapping columns
            finalTable = finalTable[finalTable.pubmedID.isin(asOfDate.pubmedID)]
            colList = ['pubmedID', 'rxnormIDspacy', 'rxnormTermspacy', 'rxnormStartChar', 'rxnormEndChar',
                       'umlsIDspacy', 'umlsTermspacy', 'umlsStartChar', 'umlsEndChar', 'snomedIDs', 'snomedNames', 'termFreq']
            finalTable = pd.merge(finalTable, asOfDate[colList], on='pubmedID')
            
            #update the current records
            makeCSVJSON(finalTable, 'pubmed', True)
            #also cache the table as an object
            asOfDate = retrieveAsTable(False, 'pubmed')
            asOfDate = asOfDate[['pmcID', 'pubmedID', 'nlmID', 'journalTitle',
             'title', 'creationDate','fullAuthorEdited', 'firstAuthor', 'fullAuthor', 'pubYear']]
            pushTableToDB(asOfDate, 'dashboard', 'pubmed_articles')

            #author Summary table, re-count, some articles may be moved to the ignore container, remove those authors
            currentAuthorSummaryTable = retrieveAuthorSummaryTable('dashboard', 'pubmed_authors')
            numRows = pd.DataFrame(currentAuthorSummaryTable).shape[0]
            #past years
            pastYears = pd.DataFrame(currentAuthorSummaryTable.iloc[0:-1])
            #this year
            currentAuthorSummaryTable['uniqueFirstAuthors'][numRows - 1] = []
            currentAuthorSummaryTable['uniqueAuthors'][numRows - 1] = []
            asOfThisYear = pd.DataFrame(currentAuthorSummaryTable.iloc[numRows - 1]).T
            #look for new authors and add to the list
            checkAuthorRecord(asOfDate, asOfThisYear, monthlyUpdate =True)
            #rbinds
            currentAuthorSummaryTable = pd.concat([pastYears, asOfThisYear])
            currentAuthorSummaryTable = currentAuthorSummaryTable.reset_index(drop = True)
            #update summary statistics
            calculateNewAuthors(currentAuthorSummaryTable)
            pushTableToDB(currentAuthorSummaryTable, 'dashboard', 'pubmed_authors')

        print("Update completed.")
    else:
        print("No updates were performed.")

