import pandas as pd
import numpy as np
import requests
import json
from datetime import date, datetime

from flask import redirect, render_template, request, session
from functools import wraps


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

def get_mp_details(name):
    """ Search for the ID and thumbnail image of the MP by name. """
    # If the postcode contains spaces, replace with '%20' for the search URL
    search_string = name.replace(" ", "%20")

    post_url = 'https://members-api.parliament.uk/api/Members/' +\
        'Search?Name=' + search_string + '&skip=0&take=20'

    # Request the URL and parse the JSON for the returned constituency
    details = requests.get(post_url)
    details.raise_for_status() # raise exception if invalid response
    mp_data = details.json()['items']

    if mp_data:
        mp_id = mp_data[0]['value']['id']
        mp_const = mp_data[0]['value']['latestHouseMembership']['membershipFrom']
        mp_thumb = mp_data[0]['value']['thumbnailUrl']
    else:
        mp_id = None
        mp_const = None
        mp_thumb = None

    return mp_id, mp_const, mp_thumb

def get_donations(mp_name):

    name_string = mp_name.replace(" ", "%20")

    # Identify the current date as the maximum date to query.
    run_dt = date.today().strftime("%Y-%m-%d")
        
    donor_url = 'http://search.electoralcommission.org.uk/api/search/Donations?' +\
        '&query=' + name_string +\
            '&sort=AcceptedDate&order=desc&tab=1&open=filter&closed=common&et=pp&et=ppm&et=tp&et=perpar&et=rd&isIrishSourceYes=true&isIrishSourceNo=true&date=Received' +\
                '&from=2017-01-01&to=' + run_dt +\
                    '&prePoll=false&postPoll=true&donorStatus=individual&donorStatus=tradeunion&donorStatus=company&donorStatus=unincorporatedassociation&donorStatus=publicfund&donorStatus=other&donorStatus=registeredpoliticalparty' +\
                        '&donorStatus=friendlysociety&donorStatus=trust&donorStatus=limitedliabilitypartnership&donorStatus=impermissibledonor&donorStatus=na&donorStatus=unidentifiabledonor&donorStatus=buildingsociety&register=gb' +\
                            '&register=ni&register=none&optCols=Register&optCols=CampaigningName&optCols=AccountingUnitsAsCentralParty&optCols=IsSponsorship&optCols=IsIrishSource&optCols=RegulatedDoneeType&optCols=CompanyRegistrationNumber' +\
                                '&optCols=Postcode&optCols=NatureOfDonation&optCols=PurposeOfVisit&optCols=DonationAction&optCols=ReportedDate&optCols=IsReportedPrePoll&optCols=ReportingPeriodName&optCols=IsBequest&optCols=IsAggregation'

    # Request the URL and parse the JSON
    response = requests.get(donor_url)
    response.raise_for_status() # raise exception if invalid response
    all_donors = response.json()['Result']

    if not all_donors:
        return None

    # Specify the attributes we want to keep
    donor_cols = [
        'AcceptedDate', 'ReturnedDate', 'AttemptedConcealment', 'CashValue', 'NonCashValue',
        'IsAnonymous', 'Value', 'DonorName', 'DonorStatus', 'DonationType'
    ]

    # For each row extracted from the JSON, add only the required attributes to a smaller list of dictionaries
    my_donors = []
    for row in all_donors:
        # Check for the selected MP name when adding rows to the output
        if mp_name in row['RegulatedEntityName']:
            temp_dict = {}
            for col in donor_cols:
                temp_dict[col] = row[col]
            my_donors.append(temp_dict)
    
    return my_donors

def donor_etl(donors):
    """ Organise the list of donations by year, group by donor and limit by size. """

    # We can probably use various reduce functions, iterating through items, etc
    # but let's go to town and convert to a pandas dataframe. Go with what you know!

    df = pd.json_normalize(donors)

    # Correct some of the field formatting:
    # 1. The date is an awful Unix timestamp. Extract the substr containing datetime in seconds.
    df['DateNum'] = df['AcceptedDate'].str[6:19].astype(int)/1000.
    df['Date'] = pd.to_datetime(df['DateNum'], unit='s')
    df['Year'] = df['Date'].dt.year

    # 2. Add a flag for whether the donation was returned
    df['Returned?'] = ~df['ReturnedDate'].isna()

    # 3. Group by year and donor, then sort output
    df2 = df.groupby(['Year','DonorName','DonationType','DonorStatus']).agg({'Returned?': 'any', 'Value': 'sum'})
    df2.sort_values(by=['Year','Value'], inplace=True, ascending=False)
    df2.reset_index(inplace=True)
    df2['Returned?'] = np.where(df2['Returned?'], 'Y','N')

    df_out = df2[['Year', 'Returned?', 'Value', 'DonorName', 'DonorStatus', 'DonationType']].copy()

    # Note we have to convert the dataframe to a JSON string, then load it as an object.
    json_out = json.loads(df_out.to_json(orient='records'))

    return json_out


def gbp(value):
    """Format value as GBP."""
    return f"£{value:,.2f}"
