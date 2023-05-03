import json
import logging
import os
import sqlite3
from typing import NamedTuple, TypeVar, Union
import click
from flask import g, current_app
from abc import ABC, abstractmethod
from collections.abc import Iterable

PROJECT_TEST_DIR = os.path.join(os.path.dirname(__file__), '../test')
DATA_TEST_DIR = os.path.join(os.path.dirname(__file__), '../../../../test/exports')

class Row(NamedTuple):
    id: str
    data: dict

class Db(ABC):

    @abstractmethod
    def close(self):
        ...

    @abstractmethod
    def init_db(self):
        ...

    @abstractmethod
    def find(self, path: str, filter={}) -> Iterable[Row]: 
        ...

    @abstractmethod
    def findById(self, path: str, id) -> Union[Row, None]:
        ...

    @abstractmethod
    def replaceById(self, path: str, id, data):
        ...

    @abstractmethod
    def updateById(self, path: str, id, data):
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

def asdict(n):
    """ Utility for converting NamedTuples to dict for json serialization.
    """
    if not hasattr(n, '_asdict'):
        return n
    d = n._asdict()
    for k, v in d.items():
        if isinstance(v, list):
            d[k] = [asdict(i) for i in v]
        else:
            d[k] = asdict(v)
    return d

class SqliteDb(Db):

    def __init__(self):
        self.session = sqlite3.connect(
            # os.path.join(PROJECT_TEST_DIR, 'test.db'),
            ":memory:",
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.session.row_factory = sqlite3.Row

    def close(self):
        self.session.close()

    def init_db(self):
        self._init_table('pubmed')
        self._init_table('google_scholar')
        self._init_table('nlp')
        self._init_table('umls')
        self._init_table('pubmedJoined')
        self._init_table('youTubeJoined')
        self._init_table('youTubeTranscript')
        self._init_table('communityDashboardRepoReadmeSummaries')

    def _init_table(self, path):
        self.session.execute(f'DROP TABLE IF EXISTS {path};')
        self.session.execute(f'''
            CREATE TABLE {path} (
                id TEXT PRIMARY KEY,
                json JSON NOT NULL
            )
        ''')
        self.session.commit()

    def load_fixture(self, data_file):
        with open(os.path.join(DATA_TEST_DIR, data_file)) as fd:
            for path, index in json.load(fd).items():
                self._init_table(path)
                for id, data in index.items():
                    self.replaceById(path, id, data)
        self.session.commit()

    def export_fixture(self, path, data_file):
        with open(os.path.join(DATA_TEST_DIR, data_file), 'w') as fd:
            json.dump({path: {r.id: r.data for r in self.find(path)}}, fd, indent=2)

    def find(self, path: str, filter={}) -> Iterable[Row]:
        where = ''
        if ('where' in filter):
            where = ' WHERE ' + ' AND '.join([f"{k} = '{v}'" for k, v in filter['where'].items()])
        sql = f'SELECT * FROM {path}{where}'
        logging.info(sql)
        rows = self.session.execute(sql).fetchall()
        return [Row(r['id'], json.loads(r['json'])) for r in rows]

    def findById(self, path: str, id) -> Union[Row, None]:
        row = self.session.execute(f'SELECT * FROM {path} WHERE id = ?', [id]).fetchone()
        if not row:
            return None
        return Row(row['id'], json.loads(row))

    def replaceById(self, path: str, id, data):
        if '/' in path:
            c, d, s = path.split('/')
            path = f'{c}_{s}'
            self._init_table(path)
        self.session.execute(
            f'INSERT INTO {path} (id, json) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET json=excluded.json;',
            [id, json.dumps(data)]
        )
        self.session.commit()

    def updateById(self, path: str, id, data):
        self.replaceById(path, id, data) # Not implemented.

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