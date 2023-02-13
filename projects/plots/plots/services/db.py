import json
import time
from azure.cosmos import CosmosClient, PartitionKey
import pandas as pd
import ast
import re
import click
from flask import g, current_app
import sqlite3
import logging
import os.path

from plots.services import youtube_miner

TEST_DIR = os.path.join(os.path.dirname(__file__), '../test')

class DbSession:

    def __init__(self):
        self.session = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.session.row_factory = sqlite3.Row

    def close(self):
        self.session.close()

    def init_db(self):
        with current_app.open_resource('test/schema.sql') as f:
            self.session.executescript(f.read().decode('utf8'))
        self._load_dashboard_fixture('pubmed_authors')
        self._load_fixture('ehden_course_completions')
        self._load_fixture('ehden_users')
        self._load_fixture('youtube_monthly')
        self._load_fixture('youtube')
        self._load_fixture('researchers')
        self._load_fixture('pubmed')

    def _load_dashboard_fixture(self, id):
        with open(os.path.join(TEST_DIR, f'{id}.json')) as fd:
            json_data = json.load(fd)
            self.replaceById('dashboard', id, json_data)

    def _load_fixture(self, path):
        self.session.execute(f'DROP TABLE IF EXISTS {path};')
        self.session.execute(f'''
            CREATE TABLE {path} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                json JSON NOT NULL
            )
        ''')
        with open(os.path.join(TEST_DIR, f'{path}.json')) as fd:
            json_data = json.load(fd)
            for r in json_data:
                self.create(path, r)
            self.session.commit()

    def find(self, path: str, filter={}):
        where = ''
        if ('where' in filter):
            where = ' WHERE ' + ' AND '.join([f"{k} = '{v}'" for k, v in filter['where'].items()])
        sql = f'SELECT * FROM {path}{where}'
        logging.info(sql)
        rows = self.session.execute(sql).fetchall()
        return [json.loads(r['json']) for r in rows]

    def findById(self, path: str, id):
        row = self.session.execute(f'SELECT * FROM {path} WHERE id = ?', [id]).fetchone()
        return json.loads(row)

    def replaceById(self, path: str, id, data):
        self.session.execute(
            f'INSERT INTO {path} (id, json) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET json=excluded.json;',
            [id, json.dumps(data)]
        )
        self.session.commit()

    def create(self, path: str, data):
        self.session.execute(
            f'INSERT INTO {path} (json) VALUES (?)',
            [json.dumps(data)]
        )
        self.session.commit()

    def deleteById(self, path: str, id):
        self.session.execute(
            f'DELETE FROM {path} WHERE id = ?',
            [id]
        )
        self.session.commit()


def get_db() -> DbSession:
    if 'db' not in g:
        g.db = DbSession()
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