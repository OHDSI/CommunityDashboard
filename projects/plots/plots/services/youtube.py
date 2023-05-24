from abc import ABC, abstractmethod
from typing import List, NamedTuple, Union, Iterable
from flask import current_app, g
import googleapiclient.discovery

CHANNEL_ID = 'UC2RFIQnptl-nk8GbjFfqztw'
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
PAGE_SIZE = 50

class YouTubeDetails(NamedTuple):
    id: str
    title: str
    duration: str
    channelId: str
    channelTitle: str
    categoryId: str
    viewCount: int
    publishedAt: str

class YouTube(ABC):

    @abstractmethod
    def ohdsi_video_details(self) -> Iterable[YouTubeDetails]:
        ...

def get_youtube() -> YouTube:
    if 'youtube' not in g:
        g.youtube = current_app.config['YouTube']()
    return g.youtube

class YouTubeGapi(YouTube):

    def __init__(self):
        self.youtube = googleapiclient.discovery.build(
            API_SERVICE_NAME, 
            API_VERSION,
            developerKey=current_app.config['YOUTUBE_API_KEY']
        )
    
    def ohdsi_video_details(self) -> Iterable[YouTubeDetails]:
        for p in self._search_pages():
            request = self.youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=','.join(p)
            )
            for v in request.execute().get('items', []):
                yield YouTubeDetails(
                    v['id'],
                    v['snippet']['title'],
                    v['contentDetails']['duration'],
                    v['snippet']['channelId'],
                    v['snippet']['channelTitle'],
                    v['snippet']['categoryId'],
                    v['statistics']['viewCount'],
                    v['snippet']['publishedAt'],
                )

    def _search_pages(self): 
        request = self.youtube.search().list(
            part="id",
            channelId=CHANNEL_ID,
            maxResults=50
        )
        while request is not None:
            page = request.execute()
            yield [
                i['id']['videoId'] 
                for i in page.get('items', [])
                if i["id"]["kind"] == "youtube#video"
            ]
            request = self.youtube.search().list_next(request, page)

    def videoStats(self, id: str) -> Iterable[List[str]]:
        pass