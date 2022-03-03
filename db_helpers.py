import pandas as pd
from sqlalchemy import create_engine
from datetime import date, datetime, timedelta
from app.models import Donations
from app import db

def get_latest_date():
    """ Returns the last date at which donation data was added to the database."""
    # TODO: Ideally this would be the latest date searched, to prevent multiple searches on the 
    # same day, but Heroku doesn't have persistent storage, so we'd need a separate Postgres table...
    # Maybe that's a better option though, as it would be much faster to query.
    return Donations.query.order_by(Donations.addedDate.desc()).first().addedDate + timedelta(days=1)

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


# TODO: We will need some way of keeping the local DB updated... 
# Ideally a function which checks whether the date in the local DB is larger than today,
# and pulls the extra donations if it is.
# Let's hope this isn't limited to 10 donations, or that we can find a way to show 30 (or more!) at a time.

# NOTE: We'll need:
# df['DateNum'] = df['acceptedDate'].str[6:19].astype(int)/1000.
# df['Date'] = pd.to_datetime(df['DateNum'], unit='s')