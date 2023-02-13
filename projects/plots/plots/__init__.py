from flask import Flask
import dash_bootstrap_components as dbc
from dash import Dash, html
import dash
import os
from logging.config import dictConfig
from dotenv import load_dotenv

TEST_DIR = os.path.join(os.path.dirname(__file__), 'test')

_dash_app = None
def create_app():
    global _dash_app
    
    app = Flask(__name__)

    load_dotenv()
    app.config['ENTREZ_EMAIL'] = os.environ.get('ENTREZ_EMAIL')
    app.config['DATABASE'] = os.path.join(TEST_DIR, 'test.db')
    app.config['SERPAPI_KEY'] = os.environ.get('SERPAPI_KEY')
    app.config['LOG_LEVEL'] = os.environ.get('LOG_LEVEL', 'INFO')

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

    from plots.blueprints import user_routes, youtube_routes, pubmed_routes, ehden_routes
    app.register_blueprint(user_routes.bp)
    app.register_blueprint(youtube_routes.bp)
    app.register_blueprint(pubmed_routes.bp)
    app.register_blueprint(ehden_routes.bp)

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