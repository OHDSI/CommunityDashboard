from datetime import datetime

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
        db.updateById('youTubeJoined', video_id, {
            'transcript': transcript
        })

def youtube_nlp_cron():
    db = get_db()
    nlp = None
    for r in db.find('youTubeJoined'):
        if not 'umls' in r.data:
            c = ' '.join(t['text'] for t in r.data['transcript'])
            if not nlp:
                print('loading model')
                nlp = get_nlp()
                print('model loaded')
            print(f'parsing {r.id}')
            nlp_doc = asdict(nlp.nlpDocument(c))
            db.updateById('youTubeJoined', r.id, {'umls': nlp_doc})
            nlp_doc['id'] = r.data['id']
            db.replaceById('youTubeUmls', r.id, nlp_doc)
            
def youtube_umls_created_snomed(u):
    db = get_db()
    umlsSearch = get_umls()
    video_id = u['value']['fields']['id']['stringValue']
    ents = [{'text': e['text']['stringValue'], 'start_char': e['start_char']['integerValue'], 'end_char': e['end_char']['integerValue']} for e in u['value']['fields']['ents']['arrayValue']['values']]
    snomed = [{'text': umlsSearch.find(e['text']), 'start_char': e['start_char'], 'end_char': e['end_char']} for e in ents]
    # db.replaceById('youTubeSnomed', video_id, {'ents': snomed})
    db.updateById('youTubeJoined', video_id, {'snomed': {'ents': snomed}})