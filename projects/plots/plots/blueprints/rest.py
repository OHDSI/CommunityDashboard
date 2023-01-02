from flask import Blueprint

from plots.services import db

bp = Blueprint('rest', __name__)

@bp.route('/publications', methods = ['GET'])
def publications():
    return db.get_publications().to_dict('records')

@bp.route('/youtube', methods = ['GET'])
def youtube():
    df, _ = db.get_youtube()
    return df.to_dict('records')

@bp.route('/course-stats', methods = ['GET'])
def courseStats():
    return db.get_course_stats().to_dict('records')