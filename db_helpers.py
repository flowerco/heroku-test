import re
import sqlite3
from flask import g
import pandas as pd

DATABASE = 'donations.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)

    # Docs say to 'place this in get_db'. Can't be that simple, can it?
    db.row_factory = sqlite3.Row
    # Wow, it IS that simple! And don't call me Shirley...

    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def df_query_db(query, args=(), one=False):

    conn = sqlite3.connect(DATABASE)
    
    df = pd.read_sql(query, conn, params = args)

    return (df.head(1) if df else None) if one else df




def highest_mp_donations():

    # Select the top 10 MPs by most donations received.
    results = query_db("SELECT entityName, sum(value) AS total FROM donations WHERE doneeType = 'MP - Member of Parliament' GROUP BY entityName ORDER BY total DESC LIMIT 10")

    return results

def highest_paying_donors():

    results = query_db("SELECT donorName, sum(value) AS total FROM donations WHERE doneeType = 'MP - Member of Parliament' GROUP BY donorName ORDER BY total DESC LIMIT 10")

    return results



# TODO: We will need some way of keeping the local DB updated... 
# Ideally a function which checks whether the date in the local DB is larger than today,
# and pulls the extra donations if it is.
# Let's hope this isn't limited to 10 donations, or that we can find a way to show 30 (or more!) at a time.

# NOTE: We'll need:
# df['DateNum'] = df['acceptedDate'].str[6:19].astype(int)/1000.
# df['Date'] = pd.to_datetime(df['DateNum'], unit='s')