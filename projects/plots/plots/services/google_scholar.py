from abc import ABC, abstractmethod
from typing import List, NamedTuple, Union
from flask import current_app, g
from serpapi import GoogleSearch

SEARCH_PARAMS = {
    "engine": "google_scholar",
    "hl": "en",
    "start": 0,
    "num": "20",
}

class GoogleScholarAuthor(NamedTuple):
    name: str
    link: str

class GoogleScholarResult(NamedTuple):
    summary: str
    link: Union[str, None]
    versions_link: Union[str, None]
    citations_link: Union[str, None]
    title: str
    total_citations: Union[int, None]
    authors: List[GoogleScholarAuthor]

class GoogleScholarSearch(NamedTuple):
    created_at: str
    results: List[GoogleScholarResult]


class GoogleScholarBase(ABC):

    @abstractmethod
    def find(self, search: str) -> GoogleScholarSearch:
        ...

def get_google_scholar() -> GoogleScholarBase:
    if 'google_scholar' not in g:
        g.google_scholar = current_app.config['GoogleScholar']()
    return g.google_scholar

class GoogleScholar(GoogleScholarBase):

    def find(self, search: str) -> GoogleScholarSearch:
        p = dict(SEARCH_PARAMS)
        p['q'] = search
        p['api_key'] = current_app.config['SERPAPI_KEY']
        return asGoogleScholarSearch(GoogleSearch(p).get_dict())
    
def asGoogleScholarSearch(d: dict) -> GoogleScholarSearch:
    results = []
    if 'organic_results' not in d:
        print('no results', d)
        raise 'no results'
    for r in d['organic_results']:
        authors = []
        for a in r['publication_info'].get('authors', []):
            authors.append(GoogleScholarAuthor(a['name'], a['link']))
        results.append(GoogleScholarResult(
            r['publication_info']['summary'],
            r.get('link', None),
            r['inline_links'].get('versions', {}).get('link', None),
            r['inline_links'].get('cited_by', {}).get('link', None),
            r['title'],
            r['inline_links'].get('cited_by', {}).get('total', None),
            authors
        ))
    return GoogleScholarSearch(
        d['search_metadata']['created_at'],
        results
    )