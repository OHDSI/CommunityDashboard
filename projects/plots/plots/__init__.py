from typing import Type
from flask import Flask
import os
from logging.config import dictConfig
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    pass

from plots.services.db import Db, SqliteDb
from plots.services.pubmed import Pubmed, PubmedBioPython
from plots.services.google_scholar import GoogleScholarBase, GoogleScholar
from plots.services.nlp import Nlp, NlpSpacy
from plots.services.umls import Umls, UmlsNih
from plots.services.youtube import YouTube, YouTubeGapi
from plots.services.youtube_transcript import YouTubeTranscript, YouTubeTranscriptPyPi
from plots.services.github import GitHub, GitHubGhApi

def create_app(
    DbClass:Type[Db]=SqliteDb,
    PubmedClass:Type[Pubmed]=PubmedBioPython,
    GoogleScholarClass:Type[GoogleScholarBase]=GoogleScholar,
    NlpClass:Type[Nlp]=NlpSpacy,
    UmlsClass:Type[Umls]=UmlsNih,
    YouTubeClass:Type[YouTube]=YouTubeGapi,
    YouTubeTranscriptClass:Type[YouTubeTranscript]=YouTubeTranscriptPyPi,
    GitHubClass:Type[GitHub]=GitHubGhApi
):
    
    app = Flask(__name__)

    app.config['Db'] = DbClass
    app.config['Pubmed'] = PubmedClass
    app.config['GoogleScholar'] = GoogleScholarClass
    app.config['Nlp'] = NlpClass
    app.config['Umls'] = UmlsClass
    app.config['YouTube'] = YouTubeClass
    app.config['YouTubeTranscript'] = YouTubeTranscriptClass
    app.config['GitHub'] = GitHubClass
    load_dotenv()
    app.config['ENTREZ_EMAIL'] = os.environ.get('ENTREZ_EMAIL')
    app.config['SERPAPI_KEY'] = os.environ.get('SERPAPI_KEY')
    app.config['UMLS_API'] = os.environ.get('UMLS_API')
    app.config['LOG_LEVEL'] = os.environ.get('LOG_LEVEL', 'INFO')
    app.config['USE_SPACY'] = os.environ.get('USE_SPACY', False) != False
    app.config['YOUTUBE_API_KEY'] = os.environ.get('YOUTUBE_API_KEY')
    app.config['GH_PAT'] = os.environ.get('GH_PAT')

    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'blueprints': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }},
        'root': {
            'level': app.config.get('LOG_LEVEL'),
            'blueprints': ['wsgi']
        }
    })

    from plots.services import db
    db.init_app(app)

    return app