from dash import Dash, dcc, html, Input, Output, State
from flask import Flask
from flask_session import Session
from flask import Flask, current_app, flash, jsonify, make_response, redirect, request, render_template, send_file, Blueprint, url_for, redirect
from handlers import key_vault, pubmed_dash, pubmed_miner, pubmed_routes, youtube_miner, youtube_dash, youtube_routes, auth_routes
from dash.dash_table.Format import Format, Group
import dash_bootstrap_components as dbc

def create_app():
    app = Flask(__name__)
    Session(app) # init the serverside session for the app: this is required due to large cookie size
    SESSION_TYPE = "filesystem"
    SESSION_STATE = None
    
    #Dash Apps
    external_stylesheets = [dbc.themes.BOOTSTRAP]
    pubmedDashApp = Dash(__name__, server=app, url_base_pathname='/pub_dashboard/', external_stylesheets=external_stylesheets)
    pubmedDashApp.layout= pubmed_dash.build_pubs_dash
    youtubeDashApp = Dash(__name__, server=app, url_base_pathname='/educ_dashboard/', external_stylesheets=external_stylesheets)
    youtubeDashApp.layout= youtube_dash.build_education_dash
    auth_routes.configure_routes(app)
    pubmed_routes.configure_routes(app,pubmedDashApp)
    youtube_routes.configure_routes(app, youtubeDashApp)

    @app.route('/')
    @app.route('/sign_in_status')
    def index():
        return render_template('home.html')

    @app.route('/update_all', methods=['GET'])
    def update_all():
        youtube_miner.main()
        pubmed_miner.main()
        return 

    return app

if __name__ == '__main__':
    app=create_app()
    app.run(debug=True)