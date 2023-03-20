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
        db.replaceById('pubmed', a.pubmedID, a)

def updated_pubmed_google_scholar(u: DatabaseTrigger[PubmedArticle]):
    db = get_db()
    google_scholar = get_google_scholar()
    search = _search_string_for_article(u.value)
    db.replaceById('google_scholar', u.value.pubmedId, asdict(google_scholar.find(search)))

def updated_pubmed_nlp(u: DatabaseTrigger[PubmedArticle]):
    db = get_db()
    n = get_nlp()
    db.replaceById('nlp', u.value.pubmedId, n.nlp(u.value.abstract))

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