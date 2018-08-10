from datetime import date
from typing import List


class Place:

    def __init__(self,
                 name: str,
                 name_presumed: bool,
                 auth_source: str,
                 auth_id: str,
                 auth_name: str,
                 auth_lat: str = None,
                 auth_lng: str = None):

        self.name: str = name
        self.name_presumed: bool = name_presumed
        self.auth_source: str = auth_source
        self.auth_id: str = auth_id
        self.auth_name: str = auth_name
        self.auth_lat: str = auth_lat
        self.auth_lng: str = auth_lng

    def __hash__(self):
        return hash((self.name, self.auth_source, self.auth_id))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name == other.name and self.auth_source == other.auth_source and self.auth_id == other.auth_id

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
                 auth_first_name: str = None,
                 auth_last_name: str = None):

        self.name: str = name
        self.name_presumed: bool = name_presumed
        self.is_corporation: bool = is_corporation
        self.auth_source: str = auth_source
        self.auth_id: str = auth_id
        self.auth_first_name: str = auth_first_name
        self.auth_last_name: str = auth_last_name

    def __hash__(self):
        return hash((self.name, self.auth_source, self.auth_id))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name == other.name and self.auth_source == other.auth_source and self.auth_id == other.auth_id

    def __str__(self):
        return str(dict({
            'name': self.name,
            'name_presumed': self.name_presumed,
            'is_corporation': self.is_corporation,
            'auth_source': self.auth_source,
            'auth_id': self.auth_id,
            'auth_first_name': self.auth_first_name,
            'auth_last_name': self.auth_last_name
        }))


class Letter:

    def __init__(self,
                 kalliope_id: str,
                 title: str,
                 language_codes: List[str],
                 origin_date_from: date = None,
                 origin_date_till: date = None,
                 origin_date_presumed: bool = False,
                 extent: str = None,
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
            'authors': self.authors,
            'recipients': self.recipients,
            'origin_place': self.origin_place,
            'reception_place': self.reception_place,
            'summary': self.summary_paragraphs
        }))
