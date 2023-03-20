import json
import pytest

from plots.functions.pubmed_miner import _combine_all_pubmed_search_terms

@pytest.mark.skip('Integration test. Run to regenerate test fixture.')
def test_PubmedBioPython_create_fixture(app):
    fixture = {
        'pubmed': {a.pubmedID: a._asdict() for a in _combine_all_pubmed_search_terms()}
    }
    with open('../../test/exports/pubmed.json', 'w') as fd:
        json.dump(fixture, fd, indent=2)