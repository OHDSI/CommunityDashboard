import json

def parse_string(s):
    if s == 'nan' or s == 'None':
        return None
    return s

def parse_list(s):
    s = parse_string(s)
    if not s:
        return None
    csv = s[2: -2]
    return csv.split("', '")

def tx(legacy):
    assert len(legacy.keys()) == 1
    k = next(legacy.keys().__iter__())
    d = legacy[k]['data']
    v = {
        'fullAuthor': parse_list(d['fullAuthor']),
        'grantNum': parse_list(d['grantNum']),
        'meshT': parse_list(d['meshT']),
        'language': parse_list(d['language']),
        'nlmID': parse_string(d['nlmID']),
        'abstract': parse_string(d['abstract']),
        'source': parse_string(d['source']),
        'creationDate': parse_string(d['creationDate']),
        'title': parse_string(d['title']),
        'pubmedID': k,
        'affiliation': parse_list(d['affiliation']),
        'countryOfPub': parse_string(d['countryOfPub']),
        'pmcID': parse_string(d['pmcID']),
        'journalTitle': parse_string(d['journalTitle']),
        'locID': parse_string(d['locID'])
    }
    # if v['pubmed']['grantNum'] and v['pubmed']['grantNum'][0] == '':
    #     print(v)
    return (k, v)

collections = None
with open('test/missingpubs.txt') as fd:
    collections = {
        'pubmed': dict(tx(json.loads(l)) for l in fd)
    }
with open('test/migrate_pubmed.json', 'w') as fd:
    json.dump(collections, fd, indent=2)