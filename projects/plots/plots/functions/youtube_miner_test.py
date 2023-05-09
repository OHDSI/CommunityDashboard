from collections import namedtuple
import pytest

from plots.services.db import get_db
from . import youtube_miner

@pytest.mark.skip('Integration test. Run to regenerate test fixture.')
def test_youtube_details_fixture(app):
    db = get_db()
    db.init_db()

    youtube_miner.youtube_details_cron()
    assert len(list(db.find('youTubeJoined'))) > 0

    db.export_fixture('youTubeJoined', 'youTubeJoined.json')

@pytest.mark.skip('Integration test. Run to regenerate test fixture.')
def test_youtube_transcript_fixture(app):
    db = get_db()
    db.init_db()
    db.load_fixture('youTubeJoined.json')

    for r in db.find('youTubeJoined'):
        youtube_miner.youtube_details_created_transcript(namedtuple('Update', ['value'])({
            'fields': {
                'id': {
                    'stringValue': r.data['id']
                }
            }
        }))
    assert len(list(db.find('youTubeTranscript'))) > 0

    db.export_fixture('youTubeTranscript', 'youTubeTranscript.json')