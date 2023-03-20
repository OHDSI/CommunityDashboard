from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import NamedTuple

from flask import current_app, g

class NlpDocument(NamedTuple):
    ents: Iterable[str]

class Nlp(ABC):

    @abstractmethod
    def nlp(self, text: str) -> NlpDocument:
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

    def nlp(self, text: str) -> NlpDocument:
        doc = self.nlp(text)
        return NlpDocument(doc.ents)