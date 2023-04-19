from abc import ABC, abstractmethod
from typing import List, NamedTuple, Union
from flask import current_app, g
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

class Transcript(NamedTuple):
    text: str
    start: float
    duration: float

class YouTubeTranscript(ABC):

    @abstractmethod
    def transcript(self, video_id) -> Union[List[Transcript], None]:
        ...

def get_youtube_transcript() -> YouTubeTranscript:
    if 'youtube_transcript' not in g:
        g.youtube_transcript = current_app.config['YouTubeTranscript']()
    return g.youtube_transcript

class YouTubeTranscriptPyPi(YouTubeTranscript):

    def __init__(self):
        pass
    
    def transcript(self, video_id) -> Union[List[Transcript], None]:
        try:
            return [Transcript(t['text'], t['start'], t['duration']) for t in YouTubeTranscriptApi.get_transcript(video_id)]
        except (TranscriptsDisabled, NoTranscriptFound):
            return None