from app import get_flask_app

app = get_flask_app()

if __name__ == '__main__':
    app.run(debug=True, port=9000, host="0.0.0.0")
