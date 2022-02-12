import os
import datetime
import requests

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy

from helpers import apology, get_mp_name, get_mp_details, get_donations, gbp

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["gbp"] = gbp

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Show homepage with search bars"""
    return render_template("/index.html")

# Test page to fetch the donor data
@app.route("/fetch", methods = ["POST"])
def fetch():

    # If the user is searching by postcode we need an extra step to identify the MP
    postcode = request.form.get("postcode")
    # Create an array of names to identify the first and surname.
    # TODO: remove punctuation, etc. Regex would probably be ideal for cleaning the input.    
    if postcode:
        mp_name = get_mp_name(postcode)
        if not mp_name:
            return apology("No MP found for that postcode")
    else:
        mp_name = request.form.get("mpname")
        if not mp_name:
            return apology("Invalid name entered")

    # Once the MP name is defined, we can get their ID and thumbnail image
    mp_id, mp_thumb = get_mp_details(mp_name)

    if not mp_id:
        return apology(mp_name + " is not a current MP")

    # Now that we have all required details for the MP, we can search for their donors
    my_donors = get_donations(mp_name)

    mp = {'name':mp_name, 'thumbnail': mp_thumb}

    # Supply this subset of the returned JSON to the html page
    return render_template("/donors.html", mp = mp, donors = my_donors)


@app.route('/redirect_to')
def redirect_to():
    link = 'http://google.com/search?q='
    name = request.args.get('link', 'Boris Johnson')
    new_link = link + name.replace(' ','+')
    return redirect(new_link), 301