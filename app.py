import os
import re
import datetime
import requests
import sys

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
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

uri = os.getenv("DATABASE_URL")  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
# rest of connection code using the connection string `uri`
app.config['SQLALCHEMY_DATABASE_URI'] = uri


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

        user = request.form.get("username")
        user_check = User.query.filter_by(name=user).first()

        # Input validation
        if not user:
            return apology("Please enter a username")
        if user_check:
            return apology("Username already exists")

        # If all valid, we add the new data to the SQL db and submit to /register.
        else:
            # New PostgreSQL implementation 
            new_user = User(user)
            db.session.add(new_user)
            db.session.commit()

            return redirect("/")

    # A method other than POST indicated the user was redirected.
    # Submitting the form will use a POST method.
    else:
        return render_template("/register.html")


# Test page to fetch the donor data
@app.route("/fetch", methods = ["GET","POST"])
def fetch():

    if request.method=="POST":

        # Create an array of names to identify the first and surname.
        # TODO: remove punctuation, etc. Regex would probably be ideal for cleaning the input.
        name_arr = request.form.get("mpname").split()

        if not name_arr:
            return apology("Invalid name entered")

        mp_first = name_arr[0]
        mp_last = name_arr[len(name_arr)-1]

        donor_url = 'http://search.electoralcommission.org.uk/api/search/Donations?start=0&rows=10&query=&sort=AcceptedDate&order=desc&et=pp&et=ppm&et=tp&et=perpar&et=rd&date=Reported' + \
            '&from=&to=&rptPd=&prePoll=false&postPoll=true&quarters=2022Q1234&register=gb&register=ni&register=none&period=3765&period=3767&period=3718&period=3720&period=3714&period=3716' + \
                '&period=3710&period=3712&period=3706&period=3708&period=3702&period=3704&period=3698&period=3700&period=3676&period=3695&period=3604&period=3602&period=3600&period=3598' +\
                    '&period=3594&period=3596&period=3578&period=3580&period=3574&period=3576&period=3570&period=3572&period=3559&period=3524&period=3567&period=3522&period=3520&period=3518' + \
                        '&period=2513&period=2507&period=2509&period=2511&period=1485&period=1487&period=1480&period=1481&period=1477&period=1478&period=1476&period=1474&period=1471&period=1473' +\
                            '&period=1466&period=463&period=1465&period=460&period=447&period=444&period=442&period=438&period=434&period=409&period=427&period=403&period=288&period=302&period=304' +\
                                '&period=300&period=280&period=218&period=206&period=208&period=137&period=138&period=128&period=73&period=69&period=61&period=63&period=50&period=40&period=39&period=5' +\
                                    '&isIrishSourceYes=true&isIrishSourceNo=true&includeOutsideSection75=true'

        # Request the URL and parse the JSON
        response = requests.get(donor_url)
        response.raise_for_status() # raise exception if invalid response
        all_donors = response.json()['Result']

        if not all_donors:
            return apology("No Donors Found")

        # Specify the attributes we want to keep
        donor_cols = [
            'AcceptedDate', 'ReturnedDate', 'AttemptedConcealment',
            'CashValue', 'NonCashValue', 'IsAnonymous', 'RegulatedEntityId', 'RegulatedEntityName',
            'Value', 'DonorName', 'DonorStatus','RegulatedDoneeType'
        ]

        # For each row extracted from the JSON, add only the required attributes to a smaller list of dictionaries
        my_donors = []
        for row in all_donors:
            # Check for the selected MP name when adding rows to the output
            if mp_first in row['RegulatedEntityName'] and mp_last in row['RegulatedEntityName']:
                temp_dict = {}
                for col in donor_cols:
                    temp_dict[col] = row[col]
                my_donors.append(temp_dict)

        # Supply this subset of the returned JSON to the html page
        if my_donors:
            return render_template("/donors.html", donors = my_donors)
        else:
            return apology("No Donations Found")

    else:
        return render_template("/fetch.html")