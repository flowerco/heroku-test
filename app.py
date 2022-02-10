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

        # Identify the current date as the maximum date to query.
        run_dt = datetime.date.today().strftime("%Y-%m-%d")
        
        donor_url = 'http://search.electoralcommission.org.uk/api/search/Donations?' +\
            '&query=' + mp_first + '%20' + mp_last +\
                '&sort=AcceptedDate&order=desc&tab=1&open=filter&closed=common&et=pp&et=ppm&et=tp&et=perpar&et=rd&isIrishSourceYes=true&isIrishSourceNo=true&date=Received' +\
                    '&from=2017-01-01&to=' + run_dt +\
                        '&prePoll=false&postPoll=true&donorStatus=individual&donorStatus=tradeunion&donorStatus=company&donorStatus=unincorporatedassociation&donorStatus=publicfund&donorStatus=other&donorStatus=registeredpoliticalparty' +\
                            '&donorStatus=friendlysociety&donorStatus=trust&donorStatus=limitedliabilitypartnership&donorStatus=impermissibledonor&donorStatus=na&donorStatus=unidentifiabledonor&donorStatus=buildingsociety&register=gb' +\
                                '&register=ni&register=none&optCols=Register&optCols=CampaigningName&optCols=AccountingUnitsAsCentralParty&optCols=IsSponsorship&optCols=IsIrishSource&optCols=RegulatedDoneeType&optCols=CompanyRegistrationNumber' +\
                                    '&optCols=Postcode&optCols=NatureOfDonation&optCols=PurposeOfVisit&optCols=DonationAction&optCols=ReportedDate&optCols=IsReportedPrePoll&optCols=ReportingPeriodName&optCols=IsBequest&optCols=IsAggregation'

        # donor_url = 'http://search.electoralcommission.org.uk/api/search/Donations?&query=Hilary%20Benn&sort=AcceptedDate&order=desc&tab=1&open=filter&closed=common&et=pp&et=ppm&et=tp&et=perpar&et=rd&isIrishSourceYes=true&isIrishSourceNo=true&date=Received&from=2017-01-01&to=2022-02-28&prePoll=false&postPoll=true&donorStatus=individual&donorStatus=tradeunion&donorStatus=company&donorStatus=unincorporatedassociation&donorStatus=publicfund&donorStatus=other&donorStatus=registeredpoliticalparty&donorStatus=friendlysociety&donorStatus=trust&donorStatus=limitedliabilitypartnership&donorStatus=impermissibledonor&donorStatus=na&donorStatus=unidentifiabledonor&donorStatus=buildingsociety&register=gb&register=ni&register=none&optCols=Register&optCols=CampaigningName&optCols=AccountingUnitsAsCentralParty&optCols=IsSponsorship&optCols=IsIrishSource&optCols=RegulatedDoneeType&optCols=CompanyRegistrationNumber&optCols=Postcode&optCols=NatureOfDonation&optCols=PurposeOfVisit&optCols=DonationAction&optCols=ReportedDate&optCols=IsReportedPrePoll&optCols=ReportingPeriodName&optCols=IsBequest&optCols=IsAggregation'

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


@app.route("/test")
def test():

    return render_template("/test.html")