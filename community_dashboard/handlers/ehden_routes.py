import pandas as pd 
from flask import Flask
from flask_session import Session
from flask import Flask, jsonify, render_template, request
from community_dashboard import app, ehdenDashApp


def configure_routes(app,ehden_dashApp):

    @app.route('/ehden_dashboard/', methods = ['GET'])
    def dashboard_ehden():
        return render_template("ehden_dashboard.html")
        
    return app