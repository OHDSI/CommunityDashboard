import requests

from plots.services.db import init_cosmos


def update_data():
    results={}
    data=requests.get('https://academy.ehden.eu/api.php')
    container=init_cosmos('dashboard')
    results['data'] = data.json()
    results['id'] = 'ehden'
    container.upsert_item(body = results)
    return 