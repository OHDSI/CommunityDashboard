import pytest

from plots.services.db import get_db
from . import github_miner

# @pytest.mark.skip('Integration test. Run to regenerate test fixture.')
def test_pubmed_create_fixture(app):
    db = get_db()
    db.init_db()

    github_miner.github_repos_cron()
    assert len(list(db.find('communityDashboardRepoReadmeSummaries'))) > 0

    db.export_fixture('communityDashboardRepoReadmeSummaries', 'communityDashboardRepoReadmeSummaries.json')