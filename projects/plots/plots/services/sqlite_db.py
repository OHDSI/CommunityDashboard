import json
import logging
import os
import sqlite3

from flask import current_app

from plots.services.db import Db

TEST_DIR = os.path.join(os.path.dirname(__file__), '../test')

class SqliteDb(Db):

    def __init__(self):
        self.session = sqlite3.connect(
            os.path.join(TEST_DIR, 'test.db'),
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
                id TEXT PRIMARY KEY,
                json JSON NOT NULL
            )
        ''')
        # with open(os.path.join(TEST_DIR, f'{path}.json')) as fd:
        #     json_data = json.load(fd)
        #     for r in json_data:
        #         self.create(path, r)
        self.session.commit()

    def find(self, path: str, filter={}):
        where = ''
        if ('where' in filter):
            where = ' WHERE ' + ' AND '.join([f"{k} = '{v}'" for k, v in filter['where'].items()])
        sql = f'SELECT * FROM {path}{where}'
        logging.info(sql)
        rows = self.session.execute(sql).fetchall()
        return [{"id": r['id'], "data": json.loads(r['json'])} for r in rows]

    def findById(self, path: str, id):
        row = self.session.execute(f'SELECT * FROM {path} WHERE id = ?', [id]).fetchone()
        return {"id": row['id'], "data": json.loads(row)}

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