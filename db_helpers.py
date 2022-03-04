import pandas as pd
import requests
import re
from datetime import date, datetime, timedelta
from app.models import Donations
from app import db

# TODO: Limit searches to last 5 years so they don't get outweighed by old higher donations...

def query_db(query, one=False):
    rv = db.engine.execute(query).fetchall()
    return (rv[0] if rv else None) if one else rv


def df_query_db(query, one=False):
    rv = pd.read_sql(query, con=db.engine)
    return (rv[0] if rv else None) if one else rv


def highest_mp_donations():
    """ Return the top 10 MPs by amount of donations received. """

    query = """ SELECT entity_name, sum(value) AS total 
    FROM donations WHERE donee_type = 'MP - Member of Parliament' 
    GROUP BY entity_name 
    ORDER BY total DESC LIMIT 10"""

    results = query_db(query)

    return results


def highest_paying_donors():
    """ Return the top 10 donors by £ amount and the total money donated, to political parties as well as MPs."""

    query = """ SELECT donor_name, donor_status, sum(value) AS total 
    FROM donations WHERE donor_status != 'Public Fund' 
    GROUP BY donor_name, donor_status 
    ORDER BY total DESC LIMIT 10"""

    results = query_db(query)

    return results


def highest_mp_donors():
    """ Return the top 10 donors by £ amount and the total money donated, to MPs only."""

    query = """SELECT donor_name, donor_status, sum(value) AS total 
    FROM donations WHERE donee_type = 'MP - Member of Parliament' 
    GROUP BY donor_name, donor_status 
    ORDER BY total DESC LIMIT 10"""

    results = query_db(query)

    return results


def find_donees(donor_list, mps_only=True):

    # We want to create a dictionary of {'donor1':[donees], 'donor2':[donees], etc} #
    results = {}
    for donor in donor_list:
        if mps_only:
            query = """SELECT entity_name, sum(value) as total 
            FROM donations WHERE donor_name = '{0}' AND donee_type = 'MP - Member of Parliament' 
            GROUP BY entity_name 
            ORDER BY total DESC LIMIT 10""".format(donor['donor_name'])
        else:
            query = """SELECT entity_name, sum(value) as total 
            FROM donations WHERE donor_name = '{0}'
            GROUP BY entity_name 
            ORDER BY total DESC LIMIT 10""".format(donor['donor_name'])

        results[donor['donor_name']] = query_db(query)
    
    return results


def update_database():
    ''' Check the database is up to date, and update the database if new donations are available '''

    # TODO: We need a session cookie here so that this check is only run once per session.

    last_update = get_date_of_last_update()

    new_rows = get_new_donations(last_update)

    # Once the check is run, replace the stored last_update value with the current date.
    df_new_date = pd.DataFrame([date.today()], columns=['last_updated'])
    df_new_date.to_sql("updated", db.engine, if_exists='replace', index=False)

    # If any new donations were returned, add them to the local database.
    if new_rows:
        print('New donations sourced from API. Updating local database.')

         # Convert the new rows into a dataframe for easier manipulation.
        df_new_rows = pd.json_normalize(new_rows)

        # Convert the field names to camel case to match the Postgres DB
        df_new_rows.columns = [to_snake_case(x.replace('Regulated','')) for x in df_new_rows.columns]
        df_out = (df_new_rows[df_new_rows['donee_type']=='MP - Member of Parliament']
          [['ecref','entity_name','value','accepted_date','donor_name','donor_status','donee_type',
              'donation_type','nature_of_donation','received_date','attempted_concealment']].copy())
        
        # Add and reformat columns in order to match the Postgres schema
        df_out.insert(1, 'added_date', date.today())
        df_out['attempt_conceal'] = df_out['attempted_concealment'].fillna('N')
        
        # Adjust the weird unix date format on the received and accepted date fields.
        df_out['date_num'] = df_out['accepted_date'].str[6:19].astype(int)/1000.
        df_out['accepted_date'] = pd.to_datetime(df_out['date_num'], unit='s')
        df_out['date_num2'] = df_out['received_date'].str[6:19].astype(int)/1000.
        df_out['received_date'] = pd.to_datetime(df_out['date_num2'], unit='s')

        # Drop the temporary fields
        df_out.drop(['attempted_concealment', 'date_num', 'date_num2'], axis=1, inplace=True)

        # Append the new data to the SQL database
        df_out.to_sql('donations', db.session.bind, if_exists='append', index=False)
    else:
        print('No new donations available')


def get_date_of_last_update():
    ''' Pull the stored date at which the local database was last updated. '''
    last_updated = db.engine.execute("SELECT * FROM updated").fetchone()

    return (last_updated[0] if last_updated else None)


def to_snake_case(txt):
    ''' Update the imported field names from the API to match the format of the local table.'''
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', txt).lower()


def api_rows(rows, curr_row, stdt, to_dt):
    ''' Return an API url to pull a specific number of donation rows, starting from curr_row.'''
    
    return (('http://search.electoralcommission.org.uk/api/search/Donations?'
              'start={}&rows={}'
              '&query=&sort=AcceptedDate&order=desc'
              '&et=pp&et=ppm&et=tp&et=perpar&et=rd&date=Received'
              '&from={}&to={}'
              '&rptPd=&prePoll=false&postPoll=true&register=gb&register=ni&register=none&donorStatus=individual&donorStatus=tradeunion&donorStatus=company&donorStatus=unincorporatedassociation&donorStatus=publicfund&donorStatus=other&donorStatus=registeredpoliticalparty&donorStatus=friendlysociety&donorStatus=trust&donorStatus=limitedliabilitypartnership&donorStatus=impermissibledonor&donorStatus=na&donorStatus=unidentifiabledonor&donorStatus=buildingsociety&isIrishSourceYes=true&isIrishSourceNo=true&includeOutsideSection75=true')
             .format(curr_row, rows, stdt.strftime('%Y-%m-%d'), to_dt.strftime('%Y-%m-%d')))


def get_new_donations(stdt):
    ''' Call the API to fetch new rows between a given start date and the current date'''
    
    # Identify whether any time has passed between the last datapull and today.
    to_dt = date.today()
    all_donors = []

    if to_dt <= stdt:
        print("Local donations database is already up to date.")
    else:
        i = 0
        n_rows = 50

        while True:

            # Pull 50 rows at at time (to minimise api calls) until there are no more rows returned for the date range.
            url = api_rows(n_rows, i, stdt, to_dt)

            try:
                response = requests.get(url)
                response.raise_for_status() # raise exception if invalid response
            except requests.exceptions.RequestException as e:  # This is the base class of exception, should catch all.
                print("Oops, request error!")
                break

            temp_donors = response.json()['Result']
            print(str(len(temp_donors)) + " rows pulled")

            if len(temp_donors) == 0:
                print("No more rows to pull")
                break

            all_donors += temp_donors
            i += n_rows
    
    return all_donors