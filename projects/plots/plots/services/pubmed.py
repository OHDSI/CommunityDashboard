from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import List, NamedTuple, Union
from Bio import Entrez, Medline #http://biopython.org/DIST/docs/tutorial/Tutorial.html#sec%3Aentrez-specialized-parsers
from flask import current_app, g
from ratelimit import sleep_and_retry, limits

ENTREZ_PARAMS = {
    'retmax': 1000,
    'db': 'pubmed'
}

class PubmedArticle(NamedTuple):
    pmcID: Union[str, None]
    pubmedID: str
    nlmID: str
    journalTitle: str
    title: str
    creationDate: str
    affiliation: Union[List[str], None]
    locID: Union[str, None]
    countryOfPub: str
    language: List[str]
    grantNum: Union[str, None]
    fullAuthor: Union[List[str], None]
    abstract: Union[str, None]
    meshT: Union[str, None]
    source: str

class Pubmed(ABC):

    @abstractmethod
    def find(self, term: str) -> Iterable[PubmedArticle]:
        ...

def get_pubmed() -> Pubmed:
    if 'pubmed' not in g:
        g.pubmed = current_app.config['Pubmed']()
    return g.pubmed

class PubmedBioPython(Pubmed):

    def __init__(self):
        Entrez.email = current_app.config['ENTREZ_EMAIL']
    
    @sleep_and_retry
    @limits(calls=3, period=1)
    def find(self, term: str) -> Iterable[PubmedArticle]:
        id_list = Entrez.read(
            Entrez.esearch(term=term, usehistory='Y', **ENTREZ_PARAMS)
        )['IdList']
        records = Medline.parse(
            Entrez.efetch(
                id=id_list, rettype="medline", retmode="json", **ENTREZ_PARAMS
            )
        )
        for r in records:
            yield from_medline_record(r)

def from_medline_record(r: Medline.Record) -> PubmedArticle:
    return PubmedArticle(
        r.get('PMC', None),
        r['PMID'],
        r['JID'],
        r['JT'],
        r['TI'],
        r['CRDT'][0],
        r.get('AD', None),
        r.get('LID', None),
        r['PL'],
        r['LA'],
        r.get('GR', None),
        r.get('FAU', None),
        r.get('AB', None),
        r.get('MH', None),
        r['SO']
    )
