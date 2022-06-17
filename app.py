from dash import Dash, dcc, html, Input, Output, State
from flask import Flask
from flask_session import Session
from flask import Flask, render_template, request, jsonify
from handlers import key_vault as kv, pubmed_dash, pubmed_miner, pubmed_routes, youtube_miner, youtube_dash, youtube_routes, ehden_routes, ehden_miner,ehden_dash
from dash.dash_table.Format import Format, Group
import dash_bootstrap_components as dbc

def create_app(app):
    #Dash Apps
    external_stylesheets = [dbc.themes.BOOTSTRAP]
    pubmedDashApp = Dash(__name__, server=app, url_base_pathname='/pub_dashboard/', external_stylesheets=external_stylesheets)
    pubmedDashApp.layout= pubmed_dash.build_pubs_dash
    youtubeDashApp = Dash(__name__, server=app, url_base_pathname='/educ_dashboard/', external_stylesheets=external_stylesheets)
    youtubeDashApp.layout= youtube_dash.build_education_dash
    ehdenDashApp = Dash(__name__, server=app, url_base_pathname='/ehden_dashboard/', external_stylesheets=external_stylesheets)
    ehdenDashApp.layout= ehden_dash.build_ehden_dash

    pubmed_routes.configure_routes(app, pubmedDashApp)
    youtube_routes.configure_routes(app, youtubeDashApp)
    ehden_routes.configure_routes(app,ehdenDashApp)

    @app.route('/')
    def index():
        """Main route for the application"""
        return render_template('home.html')

    @app.route('/update_all', methods=['GET'])
    def update_all():
        """Run the miners to update data sources"""
        if kv.key['PASS_KEY']!=request.args.get('pass_key'):
            return "Not authorized to access this page"
        youtube_miner.update_data()
        pubmed_miner.update_data()
        ehden_miner.update_data()
        return render_template('home.html')
    return app
app = Flask(__name__)
app=create_app(app)

