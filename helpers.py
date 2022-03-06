import pandas as pd
import numpy as np
import requests
import json

from flask import render_template


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def get_mp_name(postcode):
    """ Search for the name of the MP for a given postcode. """
    # If the postcode contains spaces, replace with '%20' for the search URL
    search_string = postcode.replace(" ", "%20")

    post_url = 'https://members-api.parliament.uk/api/Location/Constituency/Search?' +\
        'searchText=' + search_string + '&skip=0&take=20'

    # Request the URL and parse the JSON for the returned constituency
    constit = requests.get(post_url)
    constit.raise_for_status() # raise exception if invalid response
    details = constit.json()['items']
    if details:
        mp_data = details[0]['value']['currentRepresentation']['member']['value']
        mp_name = mp_data['nameDisplayAs']
    else:
        mp_name = None

    return mp_name

def get_mp_details(search_name):
    """ Search for the ID and thumbnail image of the MP by name. """

    # If the MP name contains spaces, replace with '%20' for the search URL
    search_string = search_name.replace(" ", "%20")

    post_url = 'https://members-api.parliament.uk/api/Members/' +\
        'Search?Name=' + search_string + '&skip=0&take=20'

    # Request the URL and parse the JSON for the returned constituency
    details = requests.get(post_url)
    details.raise_for_status() # raise exception if invalid response
    mp_data = details.json()['items']

    if mp_data:
        mp_name = mp_data[0]['value']['nameDisplayAs']
        mp_id = mp_data[0]['value']['id']
        mp_const = mp_data[0]['value']['latestHouseMembership']['membershipFrom']
        mp_thumb = mp_data[0]['value']['thumbnailUrl']
    else:
        mp_name = search_name
        mp_id = None
        mp_const = None
        mp_thumb = None

    return mp_name, mp_id, mp_const, mp_thumb


def donor_etl(donors):
    """ Organise the list of donations by year, group by donor and limit by size. """

    df = donors.copy()

    # Correct some of the field formatting:
    # 1. The date and value are currently strings.
    df['date'] = pd.to_datetime(df['received_date'], format='%Y-%m-%d')
    df['year'] = df['date'].dt.year
    df['value'] = df['value'].astype(np.double)

    # 2. Add a flag for whether the donation was returned
    df['returned'] = df['accepted_date'] == ""

    # 3. Group by year and donor, then sort output
    df2 = df.groupby(['year','donor_name','donation_type','donor_status']).agg({'returned': 'any', 'value': 'sum'})
    df2.sort_values(by=['year','value'], inplace=True, ascending=False)
    df2.reset_index(inplace=True)
    df2['returned'] = np.where(df2['returned'], 'Y','N')

    df_out = df2[['year', 'returned', 'value', 'donor_name', 'donor_status', 'donation_type']].copy()

    total = df_out[df_out['returned']!='Y']['value'].sum()

    # Note we have to convert the dataframe to a JSON string, then load it as an object.
    json_out = json.loads(df_out.to_json(orient='records'))

    # We want to show the annual records separately, so let's create a separate list of dicts for each.
    year_list = df_out.year.unique().tolist()
    year_list.sort(reverse=True)
    # Create a list for each year
    dict1 = {}
    for i in year_list:
        dict1[i] = []
    # Add the dicts we want to each list depending on the year
    key_list = ['value','donor_name','donor_status','donation_type','returned']
    for d in json_out:
        dict1[d["year"]].append({key: d[key] for key in key_list })
    # Make a final list of all the annual dictionaries
    json_final = [dict1]

    return json_final, year_list, total


def clean_name(name):
    """ Remove extra text from an MP name so that the donation search API can find them."""
    for replStr in (("The Rt Hon ",""), ("Sir",""), (' MP',''), ('Dr ',''),('Mr ',''), ('Mrs ',''), ('Ms ','')):
        name = name.replace(*replStr)
    return name


def gbp(value):
    """Format value as GBP."""
    return f"£{float(value):,.0f}"
