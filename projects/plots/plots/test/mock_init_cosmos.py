from datetime import datetime
import json
import pandas as pd


class MockCosmos:

    def __init__(self, container_name):
        self.container_name = container_name

    def query_items(self, **kwargs):
        if (self.container_name == 'pubmed'):
            return MockCosmos.pubmed_as_cosmos(**kwargs)
        elif (self.container_name == 'youtube'):
            return MockCosmos.youtube_as_cosmos()
        elif (self.container_name == 'dashboard'):
            if 'youtube' in kwargs['query']:
                return MockCosmos.youtube_dashboard_as_cosmos()
            elif 'ehden' in kwargs['query']:
                return MockCosmos.ehden_dashboard_as_cosmos()
            elif 'pubmed_authors' in kwargs['query']:
                return MockCosmos.pubmed_authors_as_cosmos()
            elif kwargs['parameters'][0]['value'] == 'pubmed_authors':
                return MockCosmos.pubmed_authors_as_cosmos()
            elif kwargs['parameters'][0]['value'] == 'pubmed_articles':
                return MockCosmos.pubmed_articles_as_cosmos()
            elif kwargs['parameters'][0]['value'] == 'youtube_annual':
                return MockCosmos.youtube_annual_as_cosmos()
            elif kwargs['parameters'][0]['value'] == 'ehden':
                return MockCosmos.ehden_dashboard_as_cosmos()   
            else:
                raise NotImplementedError()
        else:
            raise NotImplementedError()

    @staticmethod
    def pubmed_as_cosmos(**kwargs):
        id = None
        if 'parameters' in kwargs:
            for p in kwargs['parameters']:
                if p['name'] == '@id':
                    id = p['value']
                    break
        fixture = 'plots/test/pub_med_fixture.json'
        for r in json.load(open(fixture)):
            if id and r['PubMed ID'] != id:
                continue
            d = {}
            d['id'] = r['PubMed ID']
            d['trackingChanges'] = [{'t': 1, 'numCitations': r["Citation Count"], 'datePulled':r["Creation Date"]}]
            d['pubmedID'] = r['PubMed ID']
            d['creationDate'] = r['Creation Date']
            d['firstAuthor'] = r['First Authors']
            d['fullAuthor'] = json.dumps(r['Authors'].split(', '))
            d['title'] = r['Title']
            d['journalTitle'] = r['Journal']
            d['grantNum'] = 'None'
            d['pubYear'] = r['Publication Year']
            n = r['SNOMED Terms (n)']
            d['termFreq'] = n[n.find("[")+1:n.find("]")]
            yield {'data': d}

    @staticmethod
    def youtube_as_cosmos():
        fixture = 'plots/test/you_tube_fixture.json'
        for r in json.load(open(fixture)):
            d = {}
            d['id'] = r['id']
            n = r['Title']
            d['title'] = n[n.find("[")+1:n.find("]")]
            # duration = r['Duration'].split(' ')[2]
            duration = '1H1M1S'
            d['duration'] = f'  {duration}'
            d['publishedAt'] = r['Date Published']
            d['channelTitle'] = r['channelTitle']
            n = r['SNOMED Terms (n)']
            d['termFreq'] = n[n.find("[")+1:n.find("]")]
            d['lastChecked'] = datetime.now().isoformat()
            d['counts'] = [
                {
                    'checkedOn': 0,
                    'viewCount': r["Total Views"] - r["Recent Views"]
                },
                {
                    'checkedOn': 1,
                    'viewCount': r["Total Views"]
                },
            ]
            yield d

    @staticmethod
    def youtube_dashboard_as_cosmos():
        fixture = 'plots/test/you_tube_dashboard_fixture.json'
        r = json.load(open(fixture))
        df = pd.DataFrame(list(zip(r["x"], r["y"])), index=range(len(r["x"])), columns=['Date', 'Count'])
        return [{'data': df.to_json() }]

    @staticmethod
    def ehden_dashboard_as_cosmos():

        def teachers(a):
            for t in a:
                s = t.split(' ')
                yield {
                    "firstname": s[0],
                    "lastname": s[1],
                }

        def course_stats():
            fixture = 'plots/test/ehden_fixture.json'
            rows = json.load(open(fixture))
            for i, r in zip(range(len(rows)), rows):
                n = r['course_fullname']
                yield {
                    'course_id': i,
                    'teachers': teachers(list(r['authors'].split(', '))),
                    'course_started': r['course_started'],
                    'course_fullname': n[n.find("[")+1:n.find("]")],
                    'course_shortname': r['course_shortname'],
                    'category': r['category'],
                    'completions': r['completions'],
                    'started': r['started'],
                    'course_started': r['course_started']
                }

        return [{
            "data": [
                {
                    "courses": [{"number_of_courses": 19}]
                },
                {
                    "users": [
                        {"year": 2020, "number_of_users": 686},
                        {"year": 2021, "number_of_users": 1390},
                        {"year": 2022, "number_of_users": 2305},
                    ]
                },
                { "none": None },
                {
                    "completions": [
                        {"year": 2020, "completions": 403},
                        {"year": 2021, "completions": 1250},
                        {"year": 2022, "completions": 1493},                        
                    ]
                },
                {
                    "course_stats": list(course_stats())
                }
            ]
        }]

    @staticmethod
    def pubmed_authors_as_cosmos():
        cumulative = json.load(open('plots/test/pub_med_cumulative_authors.json'))
        new = json.load(open('plots/test/pub_med_new_authors.json'))
        data = list(zip(cumulative["x"], new["y"], cumulative["y"], new["y"], cumulative["y"]))
        df = pd.DataFrame(data, index=range(len(cumulative["x"])), columns=['pubYear', 'numberNewFirstAuthors', 'cumulativeFirstAuthors', 'numberNewAuthors', 'cumulativeAuthors'])
        return [{
            "data": df.to_json()
        }]

    
    def pubmed_articles_as_cosmos():
        return [{"data": json.dumps({"pubmedID":list(range(508))})}]

    @staticmethod
    def youtube_annual_as_cosmos():
        return [{"data": {"hrsWatched": {"0": 208001}}}]

    


def mock_init_cosmos(container_name):
        return MockCosmos(container_name)