# CommunityDashboard
The Community Dashboard is a Flask app tracking and connecting the activities of the OHDSI community. The goal of the dashboard is help our community identify how members can see the OHDSI eco-system as an interconnected system to make a larger impact. 

# Technology
The CommunityDashboard is a Flask app with Dash interactive Dashboards with a CosmosDB backend.  There a collection of API miners.
- Youtube Data API to search and track statistics on OHDSI videos. The dashboard fetches new videos on a daily basis, and searches for new videos each time it runs.
- PubMed Entrez API to identify and track publications. You can view the articles that have been added to the database, as well as perform CRUD (create, read, update, delete) operations on them. 
- Serpapi Wrapper for Google Scholar to pull citation statistics.
- The application fetch new articles and videos on a daily basis. On the first day of every month it will also pull the entire data. Different search strategies for PubMed and YouTube. For articles, dashboard uses a group of keywords to search from the PubMed. For YouTube, since it pulls out random videos, so we only looks for new videos each time. 

# Getting Started

Clone the project to local environment. 
Create a virtural environemnt and install the dependencies from requirements list using: 'pip install -r requirements.txt'.
Run the project locally using 'flask run'.

## File Structure

Python codes are stored in handlers folder: for data fetching, callbacks and dash data visualization. In the folder you will see repeating naming, “dash” are dash app files for generating the graphs and texts in the dashboard. “miner” are the functions to fetch and update data on daily bases. “routes” are for managing all the pathways and urls. There are additional functions in the PubMed routes file that performs CRUD operations. You will need key and authorization code to add or delete articles from the database. 

Templates filter generates different HTML pages. The three dashboard pages HTML files are embedding iframe and using dash app to generate the whole page.


# Getting Involved

We use the GitHub issue tracker for all bugs/issues/enhancements

# License
Licensed under Apache License 2.ty
