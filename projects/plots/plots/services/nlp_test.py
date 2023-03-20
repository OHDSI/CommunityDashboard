import json

import pytest
from plots.services.db import get_db
from plots.services.pubmed import PubmedArticle
from . import nlp

@pytest.mark.focus
def test_NlpSpacy_create_fixture(app):
    db = get_db()
    n = nlp.NlpSpacy()
    results = {}
    for r in db.find('pubmed'):
        a = PubmedArticle(**r.data)
        results[a.pubmedID] = n.nlp(a.abstract)._asdict()
    fixture = {
        'nlp': results
    }
    with open('../../test/exports/nlp.json', 'w') as fd:
        json.dump(fixture, fd, indent=2)