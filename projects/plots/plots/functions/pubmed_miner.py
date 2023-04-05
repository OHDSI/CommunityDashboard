from typing import List
from plots.services.db import get_db, asdict
from plots.services.pubmed import get_pubmed, PubmedArticle
from plots.services.google_scholar import get_google_scholar
from plots.services.nlp import get_nlp
from plots.functions.events import DatabaseTrigger
from plots.services.umls import get_umls

PUBMED_SEARCH_TERMS = [
    'ohdsi', 'omop', 'Observational Medical Outcomes Partnership Common Data Model', \
    '"Observational Medical Outcomes Partnership"', '"Observational Health Data Sciences and Informatics"'
]

def created_pubmed_scan():
    db = get_db()
    for a in _combine_all_pubmed_search_terms():
        db.replaceById('pubmed', a.pubmedID, asdict(a))
        db.updateById('pubmedJoined', a.pubmedID, {'pubmed': asdict(a)})

def updated_pubmed_google_scholar(u: DatabaseTrigger[PubmedArticle]):
    db = get_db()
    google_scholar = get_google_scholar()
    p = u.value['fields']
    search = _search_string_for_article(p)
    results = asdict(google_scholar.find(search))
    db.replaceById('google_scholar', p['pubmedID']['stringValue'], results)
    db.updateById('pubmedJoined', p['pubmedID']['stringValue'], {'google_scholar': results})

def nlp():
    db = get_db()
    articles: List[PubmedArticle] = []
    for r in db.find('pubmedJoined'):
        a = r.data
        # try:
        #     a = PubmedArticle(**r.data)
        # except TypeError:
        #     print(f'failed to parse {r.data}')
        #     continue
        try:
            if a['pubmed']['abstract'] and not a['nlp']:
                articles.append(a)
        except KeyError:
            print(f'failed to parse {a}')
    if len(articles):
        n = get_nlp() # Don't load the heavy models unless we know there is work to do.
        for a in articles:
            nlp_doc = asdict(n.nlpDocument(a['pubmed']['abstract']))
            db.replaceById('nlp', a['pubmed']['pubmedID'], nlp_doc)
            db.updateById('pubmedJoined', a['pubmed']['pubmedID'], {'nlp': nlp_doc})


def umls():
    db = get_db()
    umlsSearch = get_umls()
    for r in db.find('nlp'):
        snomed = [umlsSearch.find(e['text']) for e in r.data['ents']]
        db.replaceById('umls', r.id, {'snomed': snomed})
        db.updateById('pubmedJoined', r.id, {'snomed': snomed})

def _combine_all_pubmed_search_terms():
    pubmed = get_pubmed()
    index = {}
    for t in PUBMED_SEARCH_TERMS:
        articles = pubmed.find(t)
        for a in articles:
            index[a.pubmedID] = a
    return index.values()

def _search_string_for_article(a: dict) -> str:
    terms = [a['title']['stringValue']]
    if a['fullAuthor']:
        last, first = a['fullAuthor']['arrayValue']['values'][0]['stringValue'].split(', ')
        terms.append(f'{first} {last}')
    return ' '.join(terms)