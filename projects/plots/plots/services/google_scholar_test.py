import json
import pytest

from plots.services.db import get_db, asdict
from plots.functions.pubmed_miner import _search_string_for_article
from plots.services.pubmed import PubmedArticle
from . import google_scholar


@pytest.mark.skip('Integration test. Run to regenerate test fixture.')
def test_GoogleScholar_create_fixture(app):
    db = get_db()
    g = google_scholar.GoogleScholar()
    results = {}
    for r in db.find('pubmed'):
        a = PubmedArticle(**r.data)
        s = _search_string_for_article(a)
        results[a.pubmedID] = asdict(g.find(s))
    fixture = {
        'google_scholar': results
    }
    with open('../../test/exports/google_scholar.json', 'w') as fd:
        json.dump(fixture, fd, indent=2)
