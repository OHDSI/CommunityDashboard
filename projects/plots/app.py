from plots import create_app, get_dash_app

if __name__ == '__main__':
    create_app()
    get_dash_app().run(debug=True, port=5001)