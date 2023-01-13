from flask import render_template, request, Blueprint
import json

from plots.services import db, pubmed_miner, ehden_miner, youtube_miner

try:
    from plots.config import Keys
except ImportError:
    pass

def numberFormatter(number):
    number = int(number)
    if(number > 999999):
        number = str(int(number/1000000)) + "M"
    elif(number > 9999):
        number = str(int(number/1000)) + "K"
    elif(number > 999):
        number = "{:,}".format(number)
    return number

bp = Blueprint('user', __name__)

@bp.route('/')
def index():
    """Main route for the application"""
    totalAuthors = 0
    totalArticles = 0
    totalHoursWatched = 0
    totalVideos = 0
    totalCourses = 0
    totalCompletions = 0
    container_dashboard = db.init_cosmos('dashboard')
    container_youtube = db.init_cosmos('youtube')
    for item in container_dashboard.query_items(query='SELECT * FROM dashboard WHERE dashboard.id=@id',
                parameters = [{ "name":"@id", "value": "pubmed_authors" }], 
                enable_cross_partition_query=True):
        totalAuthors = json.loads(item['data'])['cumulativeAuthors']['' + str(len(json.loads(item['data'])['cumulativeAuthors']) - 1)]
        totalAuthors = numberFormatter(totalAuthors)

    for item in container_dashboard.query_items(query='SELECT * FROM dashboard WHERE dashboard.id=@id',
                parameters = [{ "name":"@id", "value": "pubmed_articles" }], 
                enable_cross_partition_query=True):
        totalArticles = len(json.loads(item['data'])['pubmedID'])
        totalArticles = numberFormatter(totalArticles)

    for item in container_dashboard.query_items(query='SELECT * FROM dashboard WHERE dashboard.id=@id',
                parameters = [{ "name":"@id", "value": "youtube_annual" }], 
                enable_cross_partition_query=True):
        yearlyCounts = item['data']['hrsWatched']
        totalHoursWatched = sum(yearlyCounts.values())
        totalHoursWatched = numberFormatter(totalHoursWatched)

    videoIDs = []
    for item in container_youtube.query_items( query='SELECT * FROM youtube', enable_cross_partition_query=True):
    #     print(json.dumps(item['data'][0]['meshIDs'], indent = True))
        videoIDs.append(item['id'])
    totalVideos = len(videoIDs)
    totalVideos = numberFormatter(totalVideos)

    for item in container_dashboard.query_items(query='SELECT * FROM dashboard WHERE dashboard.id=@id',
                parameters = [{ "name":"@id", "value": "ehden" }], 
                enable_cross_partition_query=True):
    #     print(item['data'][0])
        for i in range(len(item['data'])):
    #         print(list(item['data'][i].keys())[0])
            if(list(item['data'][i].keys())[0] == "courses"):
                courses = item['data'][i]['courses']
                for i in range(len(courses)):
                    totalCourses += int(courses[i]['number_of_courses'])
    #             print(item['data'][i]['courses'])
            elif(list(item['data'][i].keys())[0] == "completions"):
                completions = item['data'][i]['completions']
                for i in range(len(completions)):
    #                 print(completions[i])
                    if(isinstance(completions[i]['year'], type(None)) == False):
                        totalCompletions += int(completions[i]['completions'])
        totalCourses = numberFormatter(totalCourses)
        totalCompletions = numberFormatter(totalCompletions)

    liveTable = {'totalAuthors': totalAuthors, 
                'totalArticles': totalArticles,
                'totalHoursWatched': totalHoursWatched,
                'totalVideos': totalVideos,
                'totalCourses': totalCourses,
                'totalCompletions': totalCompletions}

    #data as of
    dateCheckedOn = db.getTimeOfLastUpdate()

    return render_template('home.html', liveTable = liveTable, dateCheckedOn = dateCheckedOn)

@bp.route('/update_all', methods=['GET'])
def update_all():
    """Run the miners to update data sources"""
    if Keys.PASS_KEY!=request.args.get('pass_key'):
        return "Not authorized to access this page"
    pubmed_miner.update_data()
    ehden_miner.update_data()
    youtube_miner.update_data()
    return render_template('home.html')