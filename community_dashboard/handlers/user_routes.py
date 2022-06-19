from community_dashboard import app
from community_dashboard.handlers import key_vault as kv, pubmed_miner, youtube_miner,ehden_miner
from flask import Flask, jsonify, render_template, request


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