from abc import ABC
from typing import Iterable, NamedTuple, Union
from urllib.error import HTTPError
from flask import current_app, g
from ghapi.all import GhApi

ORG = 'ohdsi-studies'

class Repo(NamedTuple):
    name: str
    watchers: int
    updatedAt: str

class Author(NamedTuple):
    name: str
    email: str
    date: str

class Commit(NamedTuple):
    sha: str
    author: Author

class GitHub(ABC):

    def repos_list_for_org() -> Iterable[Repo]:
        ...

    def repos_list_commits_for_readme() -> Iterable[Commit]:
        ...

    def repos_get_readme() -> str:
        ...

def get_github() -> GitHub:
    if 'github' not in g:
        g.github = current_app.config['GitHub']()
    return g.github

class GitHubGhApi(GitHub):

    def __init__(self, app=None):
        if not app:
            app = current_app
        self.api = GhApi(token=app.config['GH_PAT'])

    def repos_list_for_org(self) -> Iterable[Repo]:
        for r in self.api.repos.list_for_org(ORG):
            yield Repo(r['name'], r['watchers'], r['updated_at'])

    def repos_list_commits_for_readme(self, repo_name) -> Iterable[Commit]:
        for c in self.api.repos.list_commits(ORG, repo_name, path='README.md'):
            yield Commit(
                c['sha'], 
                Author(
                    c['commit']['author']['name'], 
                    c['commit']['author']['email'], 
                    c['commit']['author']['date']
                )
            )

    def repos_get_readme(self, repo_name: str, sha: str) -> Union[str, None]:
        try:
            return self.api.repos.get_readme(ORG, repo_name, sha)['content']
        except HTTPError as e:
            if e.code == 404: # No readme.
                return None
            raise e
