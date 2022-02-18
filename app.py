from flask import Flask, g, flash, redirect, render_template, request, session
from flask_session import Session

from helpers import (apology, get_all_donations, get_mp_name, get_mp_details, donor_etl, 
get_all_donations, get_mp_donations, donor_summary, gbp)
from db_helpers import df_query_db, get_db, highest_mp_donations, highest_paying_donors, query_db

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


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


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
    mp_display_name, mp_id, mp_const, mp_thumb = get_mp_details(mp_name)

    # If the ID was returned successfully, create an object to supply to the results page.
    if not mp_id:
        return apology(mp_name + " is not a current MP")

    # Now that we have all required details for the MP, we can search for their donors
    mp_donors = df_query_db("SELECT * FROM donations WHERE entityName like ?", ['%'+ mp_display_name + '%'])
    
    # Organise the donations by year and size, group by donor, and limit to the biggest 10 per year.
    if not mp_donors.empty:
        final_donors, year_list, total = donor_etl(mp_donors)
    else:
        final_donors = None
        year_list = None
        total = 0

    mp = {'name':mp_display_name, 'const':mp_const, 'total':total, 'thumbnail': mp_thumb}
    
    # print("First row of donors: " + str(final_donors[0]))

    # Supply this subset of the returned JSON to the html page
    return render_template("/donors.html", mp = mp, years = year_list, donors = final_donors)

@app.route("/summary")
def summary():

    top_mps = highest_mp_donations()

    if not top_mps:
        return apology("No donor data available")

    # Get the MP details for the highest donations received
    search_name = top_mps[0]['entityName']

    for rep in (("The Rt Hon ",""), ("Sir",""), (' MP',''), ('Dr ',''),('Mr ',''), ('Mrs ',''), ('Ms ','')):
        search_name = search_name.replace(*rep)

    total = top_mps[0]['total']
    mp_display_name, mp_id, mp_const, mp_thumb = get_mp_details(search_name)

    mp = {'name':mp_display_name, 'const':mp_const, 'total':total, 'thumbnail': mp_thumb}

    return render_template("/summary.html", mp = mp, summ = top_mps)


@app.route('/redirect_to')
def redirect_to():
    link = 'http://google.com/search?q='
    name = request.args.get('link', 'Boris Johnson')
    new_link = link + name.replace(' ','+')
    return redirect(new_link), 301