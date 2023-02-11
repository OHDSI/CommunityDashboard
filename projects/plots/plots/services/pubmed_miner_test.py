import pandas as pd
import pickle

from . import pubmed_miner

def test_getTimeOfLastUpdate_whenNoDataShouldBe2022(app):
    d = pubmed_miner.getTimeOfLastUpdate()
    assert d == '01-01-2022'

# def test_getPMArticles_searchAll(app):
#     searchAll = ['ohdsi', 'omop', 'Observational Medical Outcomes Partnership Common Data Model', \
#              '"Observational Medical Outcomes Partnership"', '"Observational Health Data Sciences and Informatics"'] 
#     a = pubmed_miner.getPMArticles(searchAll)
#     assert a == []


def test_update_data(app, monkeypatch):

    def mockGetPmArticles(query):
        return pd.read_pickle('plots/test/getPMArticles_searchAll.pkl').head(300)

    serpApiFixture = None
    with open('plots/test/serpApi.pkl', 'rb') as fd:
        serpApiFixture = pickle.load(fd)
    def mockSerpAPI(query, key):
        return serpApiFixture[query]

    monkeypatch.setattr(pubmed_miner, 'getPMArticles', mockGetPmArticles)
    monkeypatch.setattr(pubmed_miner, 'serpAPI', mockSerpAPI)

    a = pubmed_miner.update_data()
    assert a == []