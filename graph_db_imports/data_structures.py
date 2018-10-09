from datetime import date
from enum import Enum
from typing import List


class Place:

    def __init__(self,
                 name: str,
                 name_presumed: bool,
                 auth_source: str = None,
                 auth_id: str = None,
                 auth_name: str = None,
                 auth_lat: float = None,
                 auth_lng: float = None):

        self.name: str = name
        self.name_presumed: bool = name_presumed
        self.auth_source: str = auth_source
        self.auth_id: str = auth_id
        self.auth_name: str = auth_name
        self.auth_lat: float = auth_lat
        self.auth_lng: float = auth_lng

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name == other.name and self.auth_source == other.auth_source and self.auth_id == other.auth_id

    def __hash__(self):
        return hash((self.name, self.auth_source, self.auth_id))

    def __str__(self):
        return str(dict({
            'name': self.name,
            'name_presumed': self.name_presumed,
            'auth_source': self.auth_source,
            'auth_id': self.auth_id,
            'auth_name': self.auth_name,
            'auth_lat': self.auth_lat,
            'auth_lng': self.auth_lng
        }))


class Person:

    def __init__(self,
                 name: str,
                 name_presumed: bool,
                 is_corporation: bool,
                 auth_source: str = None,
                 auth_id: str = None,
                 auth_name: str = None,
                 auth_first_name: str = None,
                 auth_last_name: str = None,
                 date_of_birth: date = None,
                 date_of_death: date = None):

        self.name: str = name
        self.name_presumed: bool = name_presumed
        self.is_corporation: bool = is_corporation
        self.auth_source: str = auth_source
        self.auth_id: str = auth_id
        self.auth_name: str = auth_name
        self.auth_first_name: str = auth_first_name
        self.auth_last_name: str = auth_last_name
        self.date_of_birth: date = date_of_birth
        self.date_of_death: date = date_of_death

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name == other.name and self.auth_source == other.auth_source and self.auth_id == other.auth_id

    def __hash__(self):
        return hash((self.name, self.auth_source, self.auth_id))

    def __str__(self):
        return str(dict({
            'name': self.name,
            'name_presumed': self.name_presumed,
            'is_corporation': self.is_corporation,
            'auth_source': self.auth_source,
            'auth_id': self.auth_id,
            'auth_name': self.auth_name,
            'auth_first_name': self.auth_first_name,
            'auth_last_name': self.auth_last_name,
            'date_of_birth': self.date_of_birth,
            'date_of_death': self.date_of_death
        }))


class ContentType(Enum):
    LETTER = 1
    ATTACHMENT = 2
    UNDEFINED = 3


class DigitalArchivalObject:

    def __init__(self, url: str, content_type: ContentType, title: str):
        self.url: str = url
        self.content_type: ContentType = content_type
        self.title: str = title

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.url == other.url and self.content_type == other.content_type and self.title == other.title

    def __hash__(self):
        return hash((self.url, self.content_type, self.title))

    def __str__(self):
        return str(dict({'dao_url': self.url, 'content_type': self.content_type, 'dao_title': self.title}))


class Letter:

    def __init__(self,
                 kalliope_id: str,
                 title: str,
                 language_codes: List[str],
                 origin_date_from: date = None,
                 origin_date_till: date = None,
                 origin_date_presumed: bool = False,
                 extent: str = None,
                 digital_archival_objects: List[DigitalArchivalObject] = None,
                 authors: List[Person] = None,
                 recipients: List[Person] = None,
                 origin_place: Place = None,
                 reception_place: Place = None,
                 summary_paragraphs: List[str] = None):

        self.kalliope_id: str = kalliope_id
        self.title: str = title
        self.language_codes: List[str] = language_codes
        self.origin_date_from: date = origin_date_from
        self.origin_date_till: date = origin_date_till
        self.origin_date_presumed: bool = origin_date_presumed
        self.extent: str = extent
        self.digital_archival_objects: List[DigitalArchivalObject] = digital_archival_objects
        self.authors: List[Person] = authors
        self.recipients: List[Person] = recipients
        self.origin_place: Place = origin_place
        self.reception_place: Place = reception_place
        self.summary_paragraphs: List[str] = summary_paragraphs

    def __str__(self):
        return str(dict({
            'kalliope_id': self.kalliope_id,
            'title': self.title,
            'language_code': self.language_codes,
            'origin_date_from': self.origin_date_from,
            'origin_date_till': self.origin_date_till,
            'origin_date_presumed': self.origin_date_presumed,
            'extent': self.extent,
            'digital_archival_objects': self.digital_archival_objects,
            'authors': self.authors,
            'recipients': self.recipients,
            'origin_place': self.origin_place,
            'reception_place': self.reception_place,
            'summary': self.summary_paragraphs
        }))
