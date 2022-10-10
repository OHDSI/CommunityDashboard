import pandas as pd 
from flask import Flask
from flask_session import Session
from flask import Flask, jsonify, render_template, request
from community_dashboard import app, ehdenDashApp

@app.route('/ehden_dashboard/', methods = ['POST', 'GET'])
def dashboard_ehden():
    return render_template("ehden_dashboard.html")


@app.route('/ehden_dash', methods = ['POST', 'GET'])
def dash_app_ehden():
    return ehdenDashApp.index()

# def configure_routes(app,ehden_dashApp):

#     @app.route('/ehden_dashboard/', methods = ['GET'])
#     def dashboard_ehden():
#         return render_template("ehden_dashboard.html")
        
#     @app.route('/ehden_dash', methods = ['POST', 'GET'])
#     def dash_app_ehden():
#         return ehden_dashApp.index()
        
#     return app