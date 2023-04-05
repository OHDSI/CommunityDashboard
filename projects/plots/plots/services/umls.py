from abc import ABC, abstractmethod
from typing import Union
from flask import current_app, g
import requests

URL = 'https://uts-ws.nlm.nih.gov/rest/search/current?string={}&sabs=SNOMEDCT_US&returnIdType=code&apiKey={}'

class Umls(ABC):

    @abstractmethod
    def find(self, term: str) -> Union[str, None]:
        ...

def get_umls() -> Umls:
    if 'umls' not in g:
        g.umls = current_app.config['Umls']()
    return g.umls

class UmlsNih(Umls):

    def __init__(self):
        ...
    
    def find(self, term: str) -> Union[str, None]:
        if term == 'NA':
            return None
        search = URL.format(term, current_app.config['UMLS_API'])
        response = requests.get(search).json()
        results = response['result']['results']
        if len(results) > 0:
            return results[0]['name']
        else:
            return None

