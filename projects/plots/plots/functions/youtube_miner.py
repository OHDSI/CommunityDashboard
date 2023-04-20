from datetime import datetime
from time import sleep

from plots.services.db import get_db, asdict
from plots.services.youtube import get_youtube
from plots.services.youtube_transcript import get_youtube_transcript
from plots.services.nlp import get_nlp
from plots.services.umls import get_umls

def youtube_details_cron():
    db = get_db()
    youtube = get_youtube()
    now = datetime.now().isoformat()
    for y in youtube.ohdsi_video_details():
        db.updateById('youTubeJoined', y.id, asdict(y))
        db.updateById(f'youTubeLogs/{y.id}/stats', now, {
            'id': y.id,
            'timestamp': now,
            'viewCount': y.viewCount
        })

def youtube_details_created_transcript(u):
    db = get_db()
    youtube_transcript = get_youtube_transcript()
    video_id = u['value']['fields']['id']['stringValue']
    ts = youtube_transcript.transcript(video_id)
    if ts:
        transcript = [{'text': t.text, 'start': t.start, 'duration': t.duration} for t in ts]
        db.updateById('youTubeTranscript', video_id, {
            'id': video_id,
            'transcript': transcript
        })

def youtube_nlp_cron():
    db = get_db()
    print('loading model')
    nlp = get_nlp()
    print('model loaded')
    complete = False
    while not complete:
        try:
            complete = _retry_scan(db, nlp)
        except Exception as e: # Catches db timeout error.
            print(f'retrying {e}')
            sleep(2)

def _retry_scan(db, nlp):
    for y in db.find('youTubeTranscript'):
        if not 'umls' in y.data:
            print(f'parsing {y.id}')
            try:
                c = ' '.join(t['text'] for t in y.data['transcript'])
                nlp_doc = asdict(nlp.nlpDocument(c))
                nlp_doc['id'] = y.id
                db.replaceById('youTubeUmls', y.id, nlp_doc)
                db.updateById('youTubeTranscript', y.id, {
                    'umls': nlp_doc
                })
            except Exception as e:
                print(f'failed to parse umls {y.id} {e}')
    return True
            
def youtube_umls_created_snomed(u):
    db = get_db()
    umlsSearch = get_umls()
    video_id = u['value']['fields']['id']['stringValue']
    ents = []
    try:
        umls_ents = u['value']['fields']['ents']['arrayValue']
        if 'values' in umls_ents:
            ents = [
                {
                    'text': e['mapValue']['fields']['text']['stringValue'], 
                    'start_char': e['mapValue']['fields']['start_char']['integerValue'], 
                    'end_char': e['mapValue']['fields']['end_char']['integerValue']
                } for e in umls_ents['values']
            ]
    except KeyError as e:
        print(f'Failed to parse {video_id} {e} {u}')
        return
    snomed = [{'text': umlsSearch.find(e['text']), 'start_char': e['start_char'], 'end_char': e['end_char']} for e in ents]
    db.updateById('youTubeJoined', video_id, {'snomed': {'ents': snomed}})