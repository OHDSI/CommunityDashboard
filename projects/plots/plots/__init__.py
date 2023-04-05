from typing import Type
from flask import Flask
import os
from logging.config import dictConfig
from dotenv import load_dotenv

from plots.services.db import Db, SqliteDb
from plots.services.pubmed import Pubmed, PubmedBioPython
from plots.services.google_scholar import GoogleScholarBase, GoogleScholar
from plots.services.nlp import Nlp, NlpSpacy
from plots.services.umls import Umls, UmlsNih

_dash_app = None
def create_app(
    DbClass:Type[Db]=SqliteDb,
    PubmedClass:Type[Pubmed]=PubmedBioPython,
    GoogleScholarClass:Type[GoogleScholarBase]=GoogleScholar,
    NlpClass:Type[Nlp]=NlpSpacy,
    UmlsClass:Type[Umls]=UmlsNih
):
    global _dash_app
    
    app = Flask(__name__)

    app.config['Db'] = DbClass
    app.config['Pubmed'] = PubmedClass
    app.config['GoogleScholar'] = GoogleScholarClass
    app.config['Nlp'] = NlpClass
    app.config['Umls'] = UmlsClass
    load_dotenv()
    app.config['ENTREZ_EMAIL'] = os.environ.get('ENTREZ_EMAIL')
    app.config['SERPAPI_KEY'] = os.environ.get('SERPAPI_KEY')
    app.config['UMLS_API'] = os.environ.get('UMLS_API')
    app.config['LOG_LEVEL'] = os.environ.get('LOG_LEVEL', 'INFO')
    app.config['USE_SPACY'] = os.environ.get('USE_SPACY', False) != False

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

    from flask_cors import CORS
    CORS(app)

    from plots.blueprints import youtube_routes, ehden_routes
    app.register_blueprint(youtube_routes.bp)
    app.register_blueprint(ehden_routes.bp)

    import dash_bootstrap_components as dbc
    from dash import Dash, html
    import dash
    _dash_app = Dash(
        __name__,
        use_pages=True, server=app, 
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        # apparent bug with dash
        suppress_callback_exceptions=True,
    )
    _dash_app.layout = html.Div([dash.page_container])

    return app

def get_dash_app():
    return _dash_app