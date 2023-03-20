from plots.services.db import get_db

from plots.functions.events import DatabaseTrigger
from plots.services.pubmed import PubmedArticle
from . import pubmed_miner

def test_pubmed_miner_emulate_scheduler(app):
    db = get_db()
    
    pubmed_miner.created_pubmed_scan()

    for r in db.find('pubmed'):
        e = DatabaseTrigger(None, None, PubmedArticle(**r.data))
        pubmed_miner.updated_pubmed_google_scholar(e)

    pubmed_miner.nlp()