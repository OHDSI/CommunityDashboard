import base64
import re
from plots.services.db import get_db, asdict
from plots.services.github import get_github

REGEX = {
    'status': re.compile(r'<img src="https://img\.shields\.io/badge/Study%20Status-.*\.svg" alt="Study Status: (.*)">'),
    'useCases': re.compile(r'- Analytics use case\(s\): *\**([^*\n]*)\**'),
    'studyType': re.compile(r'- Study type: *\**([^*\n]*)\**'),
    'tags': re.compile(r'- Tags: *\**([^*\n]*)\**'),
    'studyLead': re.compile(r'- Study lead: *\**([^*\n]*)\**'),
    'startDate': re.compile(r'- Study start date: *\**([^*\n]*)\**'),
    'endDate': re.compile(r'- Study end date: *\**([^*\n]*)\**'),
    'protocol': re.compile(r'- Protocol: *\**([^*\n]*)\**'),
    'publications': re.compile(r'- Publications: *\**([^*\n]*)\**'),
    'results': re.compile(r'- Results explorer: *\**([^*\n]*)\**'),
}
REGEX_TITLE = re.compile(r'=+')
CSV_FIELDS = ['studyLead', 'useCases', 'tags', 'studyType']

def github_repos_cron():
    db = get_db()
    summaries = _summaries_for_all_repos_commits()
    for repo, commit, summary in summaries:
        commitData = asdict(commit)
        commitData['denormRepo'] = asdict(repo)
        commitData['summary'] = summary
        db.replaceById('communityDashboardRepoReadmeSummaries', commit.sha, commitData)

def _summaries_for_all_repos_commits():
    github = get_github()
    for r in github.repos_list_for_org():
        for c in github.repos_list_commits_for_readme(r.name):
            readme = github.repos_get_readme(r.name, c.sha)
            summary = _summarize(readme)
            yield (r, c, summary)

def _summarize(readme: str):
    summary = {
        'title': None,
        'status': None,
        'useCases': None,
        'studyType': None,
        'tags': None,
        'studyLeads': None,
        'startDate': None,
        'endDate': None,
        'protocol': None,
        'publications': None,
        'results': None,  
    }
    if not readme:
        return summary
    decoded = base64.b64decode(readme).decode('utf-8')
    lines = decoded.split('\n')
    if len(lines) >= 2 and REGEX_TITLE.fullmatch(lines[1]):
        summary['title'] = lines[0]
    for k, r in REGEX.items():
        ms = r.search(decoded)
        if not ms:
            continue
        if k in CSV_FIELDS:
            summary[k] = [s.strip() for s in ms.group(1).split(',')]
        else:
            summary[k] = ms.group(1).strip()
    return summary