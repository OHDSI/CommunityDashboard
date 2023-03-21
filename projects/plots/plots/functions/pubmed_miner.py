from typing import List
from plots.services.db import get_db, asdict
from plots.services.pubmed import get_pubmed, PubmedArticle
from plots.services.google_scholar import get_google_scholar
from plots.services.nlp import get_nlp
from plots.functions.events import DatabaseTrigger

PUBMED_SEARCH_TERMS = [
    'ohdsi', 'omop', 'Observational Medical Outcomes Partnership Common Data Model', \
    '"Observational Medical Outcomes Partnership"', '"Observational Health Data Sciences and Informatics"'
]

def created_pubmed_scan():
    db = get_db()
    for a in _combine_all_pubmed_search_terms():
        db.replaceById('pubmed', a.pubmedID, asdict(a))

def updated_pubmed_google_scholar(u: DatabaseTrigger[PubmedArticle]):
    db = get_db()
    google_scholar = get_google_scholar()
    search = _search_string_for_article(u.value)
    db.replaceById('google_scholar', u.value.pubmedID, asdict(google_scholar.find(search)))

def nlp():
    db = get_db()
    articles: List[PubmedArticle] = []
    for r in db.find('pubmed'):
        a = PubmedArticle(**r.data)
        # This is a poorly performing join, but since there's
        # only a few hundred articles I'm not bothered by it for now.
        if a.abstract and not db.findById('nlp', a.pubmedID):
            articles.append(a)
    if len(articles):
        n = get_nlp() # Don't load the heavy models unless we know there is work to do.
        for a in articles:
            db.replaceById('nlp', a.pubmedID, asdict(n.nlpDocument(a.abstract)))

def _combine_all_pubmed_search_terms():
    pubmed = get_pubmed()
    index = {}
    for t in PUBMED_SEARCH_TERMS:
        articles = pubmed.find(t)
        for a in articles:
            index[a.pubmedID] = a
    return index.values()

def _search_string_for_article(a: PubmedArticle) -> str:
    terms = [a.title]
    if a.fullAuthor:
        last, first = a.fullAuthor[0].split(', ')
        terms.append(f'{first} {last}')
    return ' '.join(terms)