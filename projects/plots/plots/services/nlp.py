from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import List, NamedTuple

from flask import current_app, g

class NlpEntity(NamedTuple):
    text: str
    start_char: int
    end_char: int
class NlpDocument(NamedTuple):
    ents: List[NlpEntity]

class Nlp(ABC):

    @abstractmethod
    def nlpDocument(self, text: str) -> NlpDocument:
        ...

def get_nlp() -> Nlp:
    if 'nlp' not in g:
        g.nlp = current_app.config['Nlp']()
    return g.nlp

class NlpSpacy(Nlp):

    def __init__(self):
        import scispacy
        import spacy
        from scispacy.linking import EntityLinker
        self.nlp = spacy.load("en_ner_bc5cdr_md")
        self.nlp.add_pipe("scispacy_linker", config={"resolve_abbreviations": True, "linker_name": "umls"})

    def nlpDocument(self, text: str) -> NlpDocument:
        doc = self.nlp(text)
        return asNlpDoc(doc)
    
def asNlpDoc(d: dict) -> NlpDocument:
    return NlpDocument(
        [NlpEntity(e.text, e.start_char, e.end_char) for e in d.ents]
    )