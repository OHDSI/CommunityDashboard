import requests

from plots.services.db import get_db


def update_data():
    results={}
    data=requests.get('https://academy.ehden.eu/api.php')
    db = get_db()
    results['data'] = data.json()
    results['id'] = 'ehden'
    db.replaceById('dashboard', 'ehden', results)
    return 