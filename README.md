# UK MP DONORS.com
### Video Demo: https://youtu.be/eJrMCdyzDoo
### Description:

UKMPDonors.com is a web app deployed on the Heroku platform. It is coded in Python, HTML and CSS, with a PostgreSQL database for storing all donations to UK Members of Parliament (MPs) since 2015. It allows users to access various summaries of the biggest political donors and donations, as well as to search for MPs and the donations they received by name or UK postal code.

There are 3 primary uses for the web app from the home page:

1. View a summary of the top 10 MPs by value of donations received since 2015, as well as a summary of the top 10 donors and which MPs in particular they donated to.
2. Search for an MP, and their donations received, by name.
3. Search for an MP, and their donations received, by constituency location using a postcode.

Donations to UK MPs must be reported to the Electoral Commission under the UK Political Parties Elections and Referendums Act 2000 (PPERA). The list of donations is accessible to the public via a web search API, which is queried to populate and refresh the database used in this app.

A second public API is provided by the UK Parliament, and is used to search for an MP by name or postcode. This returns the MP name (as well as their constituency and a thumbnail image) in a format which can then be searched in the Heroku Postgres donations database.

When an MP is returned, their donors are listed by year in descending order of the amount donated. Each donor is provided as a link to a Google search of the donor's name and 'UK political donations'. This allows the user to see additional context relating to the donor (including any resulting scandals that have been reported!).

There is an additional process in the background of the app which runs prior to querying the database and compares the current date to the last date at which the Heroku database was updated (where this date is stored in a separate table in the SQL databse as Heroku does not seem to have any simpler permanent data storage options under their free tier). If the database is out-of-date then multiple API calls are run (50 rows at a time) to pull and store any additional donations.

Details of the primary files used to deploy the web app are provided below:
### app/\_\_init\_\_.py
* Provides configuration details for the app, including the flask session and SQL database.
### app/routes.py
Provides 3 routes (plus the homepage '/') for requests to the app, in particular:
* /fetch: a route which accepts POST requests from form inputs or GET requests from links to MPs' names in the summary tables. It then uses various helper functions to return the details and donors for the specific MP.
* /summary: a route which queries the donations database to select the top 10 donors and donees by £ amount, and displays them via render_template, with links to search each MP on ukmpdonors.com, or each donor on Google.
* /redirect_to: allows creation of a search link in Google by accepting a name via an \<a> link in HTML and redirecting to a Google search of that name plus the text 'UK Political Donations'.
### helpers.py
Provides helper functions unrelated to the internal database, such as:
* A function to query the API used to search for MP details.
* A query to perform summaries of returned data using Pandas dataframes. 
* Some additional reformatting functions to remove titles like 'Rt Hon' and 'Sir' from MP names for more reliable API queries, and to format £ amounts as '£XXX.XX'.
### db_helpers.py
Provides helper functions to pull donor and donation data from the internal database on Heroku. 
* SQL queries are submitted to the Postgres donations table via SQLAlchemy. After some investigation, I chose to use direct SQL queries due to the complexity of the queries required. These would have prohibitively longwinded using the ORM/Model query formats in flask-SQLAlchemy.
* Once the records are selected, they are manipulated and reformatted for display to the user using Pandas dataframe operations.
* Additional functions are provided in order to call the Electoral Commision API and update the Heroku database. These functions are called if the current date is later than the date at which the database was last updated (stored as a single value in a separate SQL table - the Heroku free tier has limited permanent storage options).