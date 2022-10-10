from flask import Flask
from dash import Dash
import dash_bootstrap_components as dbc
from community_dashboard.handlers import pubmed_dash, ehden_dash, youtube_dash

app = Flask(__name__)

external_stylesheets = [dbc.themes.BOOTSTRAP]
pubmedDashApp = Dash(__name__, server=app, url_base_pathname='/pub_dashboard/', external_stylesheets=external_stylesheets)
pubmedDashApp.layout= pubmed_dash.build_pubs_dash
youtubeDashApp = Dash(__name__, server=app, url_base_pathname='/educ_dashboard/', external_stylesheets=external_stylesheets)
youtubeDashApp.layout= youtube_dash.build_education_dash
ehdenDashApp = Dash(__name__, server=app, url_base_pathname='/train_dashboard/', external_stylesheets=external_stylesheets)
ehdenDashApp.layout= ehden_dash.build_ehden_dash

from community_dashboard.handlers import ehden_routes,pubmed_routes,youtube_routes,user_routes