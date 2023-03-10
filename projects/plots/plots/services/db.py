import pandas as pd
import click
from flask import g, current_app
from abc import ABC, abstractmethod

class Db(ABC):

    @abstractmethod
    def close(self):
        ...

    @abstractmethod
    def init_db(self):
        ...

    @abstractmethod
    def find(self, path: str, filter={}): # -> {id: string, data: {}}[]
        ...

    @abstractmethod
    def findById(self, path: str, id): # -> {id: string, data: {}}
        ...

    @abstractmethod
    def replaceById(self, path: str, id, data):
        ...

    @abstractmethod
    def create(self, path: str, data):
        ...

    @abstractmethod
    def deleteById(self, path: str, id):
        ...

def get_db() -> Db:
    if 'db' not in g:
        g.db = current_app.config['Db']()
    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.init_db()

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def getTimeOfLastUpdate():
    """
    Called in main()
    Not every article has the same last date of update. Find the most recent among all articles. 
    """
    db = get_db()
    dateOfLastUpdate = "01-01-2022"
    for item in db.find('beta'):
        if(dateOfLastUpdate < item['data']['trackingChanges'][len(item['data']['trackingChanges'])-1]['datePulled']):
            dateOfLastUpdate = item['data']['trackingChanges'][len(item['data']['trackingChanges'])-1]['datePulled']
    return dateOfLastUpdate

def getExistingIDandSearchStr(containerName):
    """
    Called in main()
    Get a list of PMIDs and a list of title-author search strings
    Two outputs
    """
    db = get_db()
    result = []
    exisitingIDs = []
    exisitingTitleAuthorStr = []
    for item in db.find(containerName):
        exisitingIDs.append(item['data']['pubmedID'])
        exisitingTitleAuthorStr.append(item['data']['titleAuthorStr'])
    result = [exisitingIDs, exisitingTitleAuthorStr]

    return result

def _get_ehden():
    db = get_db()
    return db.find('dashboard', {'where': {'id': 'ehden'}})[0]

def get_ehden_users():
    items = _get_ehden()
    df = pd.DataFrame(items['data'][1]['users'])
    df['year']=pd.to_numeric(df.year)
    df=df[df.year!=1970]
    df['number_of_users']=pd.to_numeric(df.number_of_users)
    return df

def get_ehden_course_completions():
    items = _get_ehden()
    df=pd.DataFrame(items['data'][3]['completions'])
    df['year']=pd.to_numeric(df.year)
    df=df[df.year!=1970]
    df['completions']=pd.to_numeric(df.completions)
    return df

def get_course_stats():
    items = _get_ehden()
    df=pd.DataFrame(items['data'][4]['course_stats'])
    df2=df.groupby('course_id').max().reset_index()
    df2['authors']=df2.teachers.apply(_get_author_names)
    df2['course_started']=pd.to_datetime(df2.course_started)
    df2['course_fullname']=df2.apply(lambda row:"[{}](https://academy.ehden.eu/course/view.php?id={})".format(row.course_fullname,row.course_id),axis=1)
    df2['completions']=pd.to_numeric(df2.completions)
    df2['started']=pd.to_numeric(df2.started)
    df2['course_started']=df2.course_started.dt.strftime('%Y/%m/%d')
    df2=df2[df2.started!=0]
    df2.drop(['course_id','teachers'],axis=1,inplace=True)
    df2.sort_values('course_started',ascending=False,inplace=True)
    return df2

def _get_author_names(items):
    output=""
    for item in items:
        output +=", " + item['firstname'] + " " + item['lastname']
    return output[1:]