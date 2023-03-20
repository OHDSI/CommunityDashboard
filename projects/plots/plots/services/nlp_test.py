import json

import pytest
from plots.services.db import asdict, get_db
from plots.services.pubmed import PubmedArticle
from . import nlp

@pytest.mark.skip('Integration test. Run to regenerate test fixture.')
def test_NlpSpacy_create_fixture(app):
    db = get_db()
    n = nlp.NlpSpacy()
    results = {}
    for r in db.find('pubmed'):
        a = PubmedArticle(**r.data)
        if a.abstract:
            results[a.pubmedID] = asdict(n.nlpDocument(a.abstract))
    fixture = {
        'nlp': results
    }
    with open('../../test/exports/nlp.json', 'w') as fd:
        json.dump(fixture, fd, indent=2)