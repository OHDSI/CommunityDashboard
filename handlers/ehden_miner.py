from azure.cosmos import CosmosClient,PartitionKey
import pandas as pd
import datetime
from . import pubmed_miner
import requests


def update_data():
    results={}
    data=requests.get('https://academy.ehden.eu/api.php')
    container=pubmed_miner.init_cosmos('dashboard')
    results['data'] = data.json()
    results['id'] = 'ehden'
    container.upsert_item(body = results)
    return 