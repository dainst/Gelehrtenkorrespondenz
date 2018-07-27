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

        self.name = name
        self.name_presumed = name_presumed
        self.auth_source = auth_source
        self.auth_id = auth_id
        self.auth_name = auth_name
        self.auth_lat = auth_lat
        self.auth_lng = auth_lng

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
                 gnd_id: str,
                 gnd_first_name: str = '',
                 gnd_last_name: str = ''):

        self.name = name
        self.name_presumed = name_presumed
        self.gnd_id = gnd_id
        self.gnd_first_name = gnd_first_name
        self.gnd_last_name = gnd_last_name

    def __hash__(self):
        return hash((self.name, self.gnd_id))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name == other.name and self.gnd_id == other.gnd_id

    def __str__(self):
        return str(dict({
            'name': self.name,
            'name_presumed': self.name_presumed,
            'gnd_id': self.gnd_id,
            'gnd_first_name': self.gnd_first_name,
            'gnd_last_name': self.gnd_last_name
        }))


class Letter:

    def __init__(self,
                 kalliope_id: str,
                 title: str,
                 language_codes: List[str],
                 origin_date_from: str = '',
                 origin_date_till: str = '',
                 origin_date_presumed: bool = False,
                 extent: str = '',
                 authors: List[Person] = None,
                 recipients: List[Person] = None,
                 origin_place: Place = None,
                 reception_place: Place = None,
                 summary_paragraphs: List[str] = None):

        self.kalliope_id = kalliope_id
        self.title = title
        self.language_codes: List[str] = language_codes
        self.origin_date_from = origin_date_from
        self.origin_date_till = origin_date_till
        self.origin_date_presumed = origin_date_presumed
        self.extent = extent
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
