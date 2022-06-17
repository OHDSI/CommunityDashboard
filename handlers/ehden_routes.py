import pandas as pd 
from flask import Flask
from flask_session import Session
from flask import Flask, jsonify, render_template, request
from . import pubmed_miner, key_vault as kv, ehden_miner



def configure_routes(app,ehden_dashApp):

    @app.route('/ehden_dashboard/', methods = ['GET'])
    def dashboard_ehden():
        data = ehden_miner.update_data()
        return render_template("ehden_dashboard.html")
        
    return app