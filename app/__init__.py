import os
from flask import Flask
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from helpers import gbp

# Configure application
app = Flask(__name__)

# Trigger SSLify via Talisman if the app is running on Heroku
if 'DYNO' in os.environ: 

    csp = {
        'default-src': [
            '\'self\'',
            '\'unsafe-inline\'',
            'code.jquery.com',
            'cdn.jsdelivr.net'
        ]
    }
    Talisman(app, content_security_policy=csp)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# uri = 'postgresql://postgres@localhost/olive'
uri = os.getenv("DATABASE_URL")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
db = SQLAlchemy(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["gbp"] = gbp

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

from app import routes, models