from flask import Flask
import dash_bootstrap_components as dbc
from dash import Dash, html
import dash
import os
from logging.config import dictConfig
from plots.services import db
from plots.test.mock_init_cosmos import mock_init_cosmos
from dotenv import load_dotenv

ENVIRONMENTS = {
    'production': {
        # 'init_cosmos': db.init_cosmos,
        'init_cosmos': mock_init_cosmos,
        'log_level': 'INFO',
        'cors': False,
    },
    'development': {
        'init_cosmos': mock_init_cosmos,
        'log_level': 'INFO',
        'cors': True,
    },
}

env = ENVIRONMENTS[os.environ.get('PLOTS_ENV', 'production')]

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
        'level': env['log_level'],
        'blueprints': ['wsgi']
    }
})

db.init_cosmos = env['init_cosmos']

_dash_app = None
def create_app():
    global _dash_app
    
    app = Flask(__name__)

    load_dotenv()
    app.config['ENTREZ_EMAIL'] = 'nathan@natb1.com'
    app.config['DATABASE'] = 'plots/test/test.db'
    app.config['SERPAPI_KEY'] = os.environ.get('SERPAPI_KEY')

    from . import db
    db.init_app(app)

    if env['cors']:
        from flask_cors import CORS
        CORS(app)

    from plots.blueprints import user_routes, youtube_routes, pubmed_routes, ehden_routes, rest
    app.register_blueprint(user_routes.bp)
    app.register_blueprint(youtube_routes.bp)
    app.register_blueprint(pubmed_routes.bp)
    app.register_blueprint(ehden_routes.bp)
    app.register_blueprint(rest.bp)

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