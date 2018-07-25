import re

from typing import List


PAGE_COUNT_PATTERN = re.compile('.*(\d+)\s*Seiten.*')


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
                 letter_id: str,
                 authors: List[Person],
                 recipients: List[Person],
                 date: str = '',
                 title: str = '',
                 summary: str = '',
                 quantity_description: str = '',
                 quantity_page_count: int = None,
                 place_of_origin: Place = None,
                 place_of_reception: Place = None):

        self.id = letter_id
        self.authors: List[Person] = authors
        self.recipients: List[Person] = recipients
        self.date = date
        self.title = title
        self.summary = summary
        self.quantity_description = quantity_description
        self.quantity_page_count = quantity_page_count
        self.place_of_origin: Place = place_of_origin
        self.place_of_reception: Place = place_of_reception

    def __str__(self):
        return str(dict({
            'authors': self.authors,
            'recipients': self.recipients,
            'date': self.date,
            'title': self.title,
            'summary': self.summary,
            'id': self.id,
            'quantity_description': self.quantity_description,
            'quantity_page_count': self.quantity_page_count,
            'place_of_origin': self.place_of_origin,
            'place_of_reception': self.place_of_reception
        }))

    @staticmethod
    def parse_page_count(value):
        match = PAGE_COUNT_PATTERN.match(value)
        if match is not None:
            return match.group(1)
        else:
            return -1
