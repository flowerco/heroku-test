import os
import datetime
from flask_sqlalchemy import SQLAlchemy

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure Flask to use SQLAlchemy database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Show list of users"""

    users = User.query.order_by(User.id).all()

    if len(users) == 0:
        return apology("No users")

    return render_template("/index.html", users = users)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        username = request.form.get("username")

        user_check = db.execute("SELECT * FROM users WHERE username = ?", username)
        user_check = User.query.filter_by(username=username).first()

        # Input validation
        if not username:
            return apology("Please enter a username")
        if len(user_check) != 0:
            return apology("Username already exists")

        # If all valid, we add the new data to the SQL db and submit to /register.
        else:
            # New PostgreSQL implementation 
            new_user = User(username)
            db.session.add(new_user)
            db.session.commit()

            return render_template("/index.html")

    # A method other than POST indicated the user was redirected.
    # Submitting the form will use a POST method.
    else:
        return render_template("/register.html")