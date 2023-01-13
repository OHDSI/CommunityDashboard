from flask import render_template, Blueprint

bp = Blueprint('ehden', __name__)

@bp.route('/ehden_dashboard/', methods = ['POST', 'GET'])
def dashboard_ehden():
    return render_template("ehden_dashboard.html")

# def configure_routes(app,ehden_dashApp):

#     @app.route('/ehden_dashboard/', methods = ['GET'])
#     def dashboard_ehden():
#         return render_template("ehden_dashboard.html")
        
#     @app.route('/ehden_dash', methods = ['POST', 'GET'])
#     def dash_app_ehden():
#         return ehden_dashApp.index()
        
#     return app