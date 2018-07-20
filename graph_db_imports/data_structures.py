import re
import uuid

from typing import List


PAGE_COUNT_PATTERN = re.compile('.*(\d+)\s*Seiten.*')


class Place:

    def __init__(self, label: str, gnd_id: str, lat: str = None, lng: str = None):
        self.uuid = str(uuid.uuid4())
        self.label = label
        self.gnd_id = gnd_id
        #self.gaz_id = gaz_id
        self.lat = lat
        self.lng = lng

    def __hash__(self):
        return hash((self.label, self.gnd_id, self.id, self.lat, self.lng))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.label == other.label and self.gnd_id == other.gnd_id and self.id == other.id \
               and self.lat == other.lat and self.lng == other.lng

    def __str__(self):
        return str(dict(
            {'uuid': self.uuid, 'label': self.label, 'gnd_id': self.gnd_id, 'lat': self.lat, 'lng': self.lng}
        ))


class Person:

    def __init__(self, name: str, name_presumed: bool, gnd_id: str, gnd_first_name: str = '', gnd_last_name: str = ''):
        self.uuid = str(uuid.uuid4())
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
        return str(dict(
            {'uuid': self.uuid, 'name': self.name, 'name_presumed': self.name_presumed, 'gnd_id': self.gnd_id,
             'gnd_first_name': self.gnd_first_name, 'gnd_last_name': self.gnd_last_name}
        ))


class Letter:

    def __init__(self, letter_id: str, authors: List[Person], recipients: List[Person], date: str = '',
                 title: str = '', summary: str = '', quantity_description: str = '', quantity_page_count: int = None,
                 place_of_origin: Place = None, place_of_reception: Place = None):
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
        return str(dict(
            {'authors': self.authors, 'recipients': self.recipients, 'date': self.date, 'title': self.title,
             'summary': self.summary, 'id': self.id, 'quantity_description': self.quantity_description,
             'quantity_page_count': self.quantity_page_count, 'place_of_origin': self.place_of_origin,
             'place_of_reception': self.place_of_reception}
        ))

    @staticmethod
    def parse_page_count(value):
        match = PAGE_COUNT_PATTERN.match(value)
        if match is not None:
            return match.group(1)
        else:
            return -1
