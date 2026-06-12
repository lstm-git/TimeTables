"""Production entry point.

Run on the VM with:  waitress-serve --host 0.0.0.0 --port 8000 wsgi:app
(or put gunicorn/nginx in front on Linux).
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
