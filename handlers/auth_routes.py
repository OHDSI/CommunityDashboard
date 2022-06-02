from ms_identity_web import IdentityWebPython
from ms_identity_web.adapters import FlaskContextAdapter
from ms_identity_web.configuration import AADConfig
import logging
from flask import Flask, current_app, flash, jsonify, make_response, redirect, request, render_template, send_file, Blueprint, url_for, redirect


def configure_routes(app):
    secure_client_credential=None
    aad_configuration = AADConfig.parse_json('aadconfig.json')
    AADConfig.sanity_check_configs(aad_configuration)
    adapter = FlaskContextAdapter(app)
    ms_identity_web = IdentityWebPython(aad_configuration, adapter)
    app.logger.level=logging.INFO # can set to DEBUG for verbose logs
    if app.config.get('ENV') == 'production':
        # The following is required to run on Azure App Service or any other host with reverse proxy:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
        # Use client credential from outside the config file, if available.
        if secure_client_credential: aad_configuration.client.client_credential = secure_client_credential

    @app.route('/token_details')
    @ms_identity_web.login_required # <-- developer only needs to hook up login-required endpoint like this
    def token_details():
        current_app.logger.info("token_details: user is authenticated, will display token details")
        return render_template('auth/token.html')

    @app.route('/not_found')
    def not_found():
        return jsonify(message = 'That resource was not found'), 404

    @app.route('/login', methods = ['POST'])
    def login():
        email = request.form['email']
        password = request.form['password']

        if((email == "sliu197@jhmi.edu") and (password == "1111")):
            test = True
        else: 
            test = False
        if test:
            return jsonify(message = "True")
        else:
            return jsonify(message = 'Login unsuccessful. Bad email or password'), 401
    return app