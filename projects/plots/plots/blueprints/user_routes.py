from flask import render_template, request, Blueprint
import json

from plots.services import pubmed_miner, ehden_miner, youtube_miner
from plots.services.db import get_db, getTimeOfLastUpdate

def numberFormatter(number):
    number = int(number)
    if(number > 999999):
        number = str(int(number/1000000)) + "M"
    elif(number > 9999):
        number = str(int(number/1000)) + "K"
    elif(number > 999):
        number = "{:,}".format(number)
    return number

bp = Blueprint('user', __name__)

@bp.route('/update_all', methods=['GET'])
def update_all():
    """Run the miners to update data sources"""
    if Keys.PASS_KEY!=request.args.get('pass_key'):
        return "Not authorized to access this page"
    pubmed_miner.update_data()
    ehden_miner.update_data()
    youtube_miner.update_data()
    return render_template('home.html')