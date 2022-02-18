import pandas as pd
import numpy as np
import requests
import json

from datetime import date
from flask import render_template
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

def get_mp_details(search_name):
    """ Search for the ID and thumbnail image of the MP by name. """

    # If the MP name contains spaces, replace with '%20' for the search URL
    search_string = search_name.replace(" ", "%20")

    print(search_string)

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


def get_all_donations():
    # Pull the full history of donations.
    run_dt = date.today().strftime("%Y-%m-%d")

    donor_url = 'http://search.electoralcommission.org.uk/api/search/Donations?' +\
            '&sort=AcceptedDate&order=desc&tab=1&open=filter&closed=common&et=pp&et=ppm&et=tp&et=perpar&et=rd&isIrishSourceYes=true&isIrishSourceNo=true&date=Received' +\
                '&from=2015-01-01&to=' + run_dt +\
                    '&prePoll=false&postPoll=true&donorStatus=individual&donorStatus=tradeunion&donorStatus=company&donorStatus=unincorporatedassociation&donorStatus=publicfund&donorStatus=other&donorStatus=registeredpoliticalparty' +\
                        '&donorStatus=friendlysociety&donorStatus=trust&donorStatus=limitedliabilitypartnership&donorStatus=impermissibledonor&donorStatus=na&donorStatus=unidentifiabledonor&donorStatus=buildingsociety&register=gb' +\
                            '&register=ni&register=none&optCols=Register&optCols=CampaigningName&optCols=AccountingUnitsAsCentralParty&optCols=IsSponsorship&optCols=IsIrishSource&optCols=RegulatedDoneeType&optCols=CompanyRegistrationNumber' +\
                                '&optCols=Postcode&optCols=NatureOfDonation&optCols=PurposeOfVisit&optCols=DonationAction&optCols=ReportedDate&optCols=IsReportedPrePoll&optCols=ReportingPeriodName&optCols=IsBequest&optCols=IsAggregation'
    
    # donor_url = 'http://search.electoralcommission.org.uk/api/search/Donations?&query=&sort=Value&order=desc&et=pp&et=ppm&et=tp&et=perpar&et=rd&date=Received&from=2015-01-01&to=2022-02-02&rptPd=&prePoll=false&postPoll=true&register=gb&register=ni&register=none&donorStatus=individual&donorStatus=tradeunion&donorStatus=company&donorStatus=unincorporatedassociation&donorStatus=publicfund&donorStatus=other&donorStatus=registeredpoliticalparty&donorStatus=friendlysociety&donorStatus=trust&donorStatus=limitedliabilitypartnership&donorStatus=impermissibledonor&donorStatus=na&donorStatus=unidentifiabledonor&donorStatus=buildingsociety&isIrishSourceYes=true&isIrishSourceNo=true&includeOutsideSection75=true'
    # Request the URL and parse the JSON
    response = requests.get(donor_url)
    response.raise_for_status() # raise exception if invalid response
    all_donors = response.json()['Result']

    if not all_donors:
        return None

    return all_donors


def donor_summary(all_donors):

    df = pd.json_normalize(all_donors)

    # Select MP donations only
    # TODO: Should this be for the MP tables only?
    # For the top donors it might be worth seeing donors who contributed to specific parties...
    df = df[df['RegulatedDoneeType'] == "MP - Member of Parliament"]

    # Correct some of the field formatting:
    # 1. The date is an awful Unix timestamp. Extract the substr containing datetime in seconds.
    df['DateNum'] = df['AcceptedDate'].str[6:19].astype(int)/1000.
    df['Date'] = pd.to_datetime(df['DateNum'], unit='s')
    df['Year'] = df['Date'].dt.year

    # 2. Add a flag for whether the donation was returned
    df['Returned?'] = ~df['ReturnedDate'].isna()

    # 3. Fix the name format
    df['Name'] = df['RegulatedEntityName'].str.replace('The Rt Hon | MP', '')

    # The total value of donations per MP
    df = df[['Returned?','Name','Value','DonorName']]
    df_mp = df[~df['Returned?']].groupby('Name').agg({'Value':'sum'})
    df_mp.sort_values(by='Value', inplace=True, ascending=False)
    df_mp.reset_index(inplace=True)
    df_mp = df_mp.head(10)
    json_mp = json.loads(df_mp.to_json(orient='records'))

    print(json_mp)

    # The total value of donations per donor
    # df_donor = df[~df['Returned?']].groupby('DonorName').agg({'Value':'sum'})
    # df_donor.sort_values(by=['Value'], inplace=True, ascending=False)
    # df_donor.reset_index(inplace=True)
    # json_donor = json.loads(df_donor.to_json(orient='records'))

    # The top 5 donors per year
    # df_year = df[~df['Returned?']].groupby(['Year','DonorName']).agg({'Value':'sum'})
    # df_year.sort_values(by=['Year','Value'], inplace=True, ascending=False)
    # df_year.reset_index(inplace=True)
    # df_year = df_year.assign(rnk=df_year.groupby(['Year'])['Value']
    #                                  .rank(method='min', ascending=False))
    # df_year = df_year[df_year['rnk']<=5]
    # json_year = json.loads(df_year.to_json(orient='records'))

    return json_mp


def get_mp_donations(mp_name):

    name_string = mp_name.replace(" ", "%20")

    # Identify the current date as the maximum date to query.
    run_dt = date.today().strftime("%Y-%m-%d")

    # Extract the latest date from the SQL db.

        
    donor_url = 'http://search.electoralcommission.org.uk/api/search/Donations?' +\
        '&query=' + name_string +\
            '&sort=AcceptedDate&order=desc&tab=1&open=filter&closed=common&et=pp&et=ppm&et=tp&et=perpar&et=rd&isIrishSourceYes=true&isIrishSourceNo=true&date=Received' +\
                '&from=2015-01-01&to=' + run_dt +\
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

    df = donors.copy()

    # Correct some of the field formatting:
    # 1. The date and value are currently strings.
    df['date'] = pd.to_datetime(df['receivedDate'], format='%d/%m/%Y')
    df['year'] = df['date'].dt.year
    df['value'] = df['value'].astype(np.double)

    # 2. Add a flag for whether the donation was returned
    df['returned'] = df['acceptedDate'].isna()

    # 3. Group by year and donor, then sort output
    df2 = df.groupby(['year','donorName','donationType','donorStatus']).agg({'returned': 'any', 'value': 'sum'})
    df2.sort_values(by=['year','value'], inplace=True, ascending=False)
    df2.reset_index(inplace=True)
    df2['returned'] = np.where(df2['returned'], 'Y','N')

    df_out = df2[['year', 'returned', 'value', 'donorName', 'donorStatus', 'donationType']].copy()

    total = df_out['value'].sum()

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
    key_list = ['value','donorName','donorStatus','donationType','returned']
    for d in json_out:
        dict1[d["year"]].append({key: d[key] for key in key_list })
    # Make a final list of all the annual dictionaries
    json_final = [dict1]

    return json_final, year_list, total


def gbp(value):
    """Format value as GBP."""
    return f"£{float(value):,.0f}"
