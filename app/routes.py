from flask import Flask, g,  redirect, render_template, request, session
from flask_session import Session
from app import app
from helpers import (apology, clean_name, get_all_donations, get_mp_name, get_mp_details, donor_etl, 
get_all_donations, get_mp_donations, donor_summary)
from db_helpers import df_query_db, find_donees, highest_mp_donations, highest_mp_donors


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

    return render_template("index.html")


# Test page to fetch the donor data
@app.route("/fetch", methods = ["GET", "POST"])
def fetch():

    # STEP 1: Source the MP name to search for, from one of 3 input routes

    # a) We use a GET request if the MP name was provided via a link.
    if request.method == "GET":
        mp_name = clean_name(request.args.get('mpname'))

    # TODO: remove punctuation, etc. Regex would probably be ideal for cleaning the input.    
    else:
        # b) If the user is searching by postcode we need an extra step to identify the MP
        postcode = request.form.get("postcode")
        if postcode:
            mp_name = get_mp_name(postcode)
            if not mp_name:
                return apology("No MP found for that postcode")
        else:
            # c) Otherwise the MP name has been entered manually in the search form.
            mp_name = request.form.get("mpname")
            if not mp_name:
                return apology("Invalid name entered")

    # STEP 2: Once the MP name is defined, we can get their ID and thumbnail image
    print("The MP name to search is: " + mp_name)
    mp_display_name, mp_id, mp_const, mp_thumb = get_mp_details(mp_name)

    # If the ID was returned successfully, create an object to supply to the results page.
    if not mp_id:
        return apology(mp_name + " is not a current MP")

    # STEP 3: Now that we have all required details for the MP, we can search for their donors
    query = """SELECT * FROM donations WHERE entity_name like '{}'""".format('%%'+ mp_display_name + '%%')
    mp_donors = df_query_db(query)
    
    # Organise the donations by year and size, then group by donor.
    if not mp_donors.empty:
        final_donors, year_list, total = donor_etl(mp_donors)
    else:
        final_donors = None
        year_list = None
        total = 0

    mp = {'name':mp_display_name, 'const':mp_const, 'total':total, 'thumbnail': mp_thumb}

    # Supply this subset of the returned JSON to the html page
    return render_template("/donors.html", mp = mp, years = year_list, donors = final_donors)

@app.route("/summary")
def summary():

    # TODO: You know there's an 'Attempted Concealment' flag, right?
    # Prime data for a summary chart!!! :-)

    # SUMMARY 1: MPs with highest value donations received.
    top_mps = highest_mp_donations()

    if not top_mps:
        return apology("No MP data available")

    # Get the MP details for the highest donations received
    search_name = clean_name(top_mps[0]['entity_name'])

    total = top_mps[0]['total']
    mp_display_name, mp_id, mp_const, mp_thumb = get_mp_details(search_name)

    mp = {'name':mp_display_name, 'const':mp_const, 'total':total, 'thumbnail': mp_thumb}

    # SUMMARY 2: Donors who donated the most to MPs and who they donated to

    donors = highest_mp_donors()
    if not donors:
        return apology("No donor data available")

    donees = find_donees(donors, mps_only=True)

    # SUMMARY 3: Donors who donated the most, including to political parties, and who they donated to



    return render_template("/summary.html", mp=mp, summ=top_mps, donors=donors, donees=donees)


@app.route('/redirect_to')
def redirect_to():
    link = 'http://google.com/search?q='
    name = request.args.get('link', 'Boris Johnson')
    new_link = link + name.replace(' ','+') + "+UK+political+donations"
    return redirect(new_link), 301