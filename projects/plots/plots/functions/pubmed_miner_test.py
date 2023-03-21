import pytest
from plots.services.db import get_db

from plots.functions.events import DatabaseTrigger
from plots.services.pubmed import PubmedArticle
from . import pubmed_miner

@pytest.mark.skip('Integration test. Run to regenerate test fixture.')
def test_pubmed_create_fixture(app):
    db = get_db()
    db.init_db()

    pubmed_miner.created_pubmed_scan()
    assert len(list(db.find('pubmed'))) > 0

    db.export_fixture('pubmed', 'pubmed.json')

@pytest.mark.skip('Integration test. Run to regenerate test fixture.')
def test_google_scholar_create_fixture(app):
    db = get_db()
    db.init_db()
    db.load_fixture('pubmed.json')

    for r in db.find('pubmed'):
        e = DatabaseTrigger(None, None, PubmedArticle(**r.data))
        pubmed_miner.updated_pubmed_google_scholar(e)
    assert len(list(db.find('google_scholar'))) > 0

    db.export_fixture('google_scholar', 'google_scholar.json')

@pytest.mark.skip('Integration test. Run to regenerate test fixture.')
def test_nlp_create_fixture(app):
    db = get_db()
    db.init_db()
    db.load_fixture('pubmed.json')

    pubmed_miner.nlp()
    assert len(list(db.find('nlp'))) > 0

    db.export_fixture('nlp', 'nlp.json')