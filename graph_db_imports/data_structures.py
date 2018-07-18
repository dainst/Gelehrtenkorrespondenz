from typing import List
import re

PAGE_COUNT_PATTERN = re.compile('.*(\d+)\s*Seiten.*')


class Place:

    def __init__(self, label: str, gnd_id: str, lat: str = None, lng: str = None):
        self.label = label
        self.gnd_id = gnd_id
        self.lat = lat
        self.lng = lng
        self.id = self.label

    def __hash__(self):
        return hash((self.label, self.gnd_id, self.id, self.lat, self.lng))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.label == other.label and self.gnd_id == other.gnd_id and self.id == other.id \
            and self.lat == other.lat and self.lng == other.lng

    def __str__(self):
        return str(dict({'label': self.label, 'gnd_id': self.gnd_id, 'id': self.id, 'lat': self.lat, 'lng': self.lng}))


class LocalizationPoint:

    def __init__(self, place: Place, date: str):
        self.date = date
        self.place = place

    def __str__(self):
        return str(dict({'date': self.date, 'place': self.place}))


class LocalizationTimeSpan:

    def __init__(self, place: Place, date_from: str = '', date_to: str = ''):
        self.place = place
        self.date_from = date_from
        self.date_to = date_to

    def __hash__(self):
        return hash((self.place, self.date_from, self.date_to))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.place == other.place and self.date_from == other.date_from and self.date_to == other.date_to

    def __str__(self):
        return str(dict({'date_from': self.date_from, 'date_to': self.date_to, 'place': self.place}))

    @staticmethod
    def aggregate_localization_points_to_timespan(localization_points: List[LocalizationPoint]):
        localization_points = sorted(localization_points, key=lambda x: (x.date, x.place.label))

        persons_localizations_list = []

        current_place = localization_points[0].place
        current_date_from = localization_points[0].date
        current_date_to = localization_points[0].date

        for current_point in localization_points:

            if current_place.id != current_point.place.id:
                persons_localizations_list.append(
                    LocalizationTimeSpan(current_place, current_date_from, current_date_to)
                )

                current_place = current_point.place
                current_date_from = current_point.date
                current_date_to = current_point.date
            else:
                current_date_to = current_point.date

        persons_localizations_list.append(LocalizationTimeSpan(current_place, current_date_from, current_date_to))

        return persons_localizations_list


class PersonData:

    def __init__(self, name: str, name_presumed: bool, gnd_id: str, localizations: List[LocalizationTimeSpan],
                 first_name: str = '', last_name: str = ''):
        self.name = name
        self.name_presumed = name_presumed
        self.gnd_id = gnd_id
        self.gnd_first_name = first_name
        self.gnd_last_name = last_name
        self.localizations = localizations

        self.id = self.gnd_id

    def __hash__(self):
        return hash((self.gnd_id,))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.gnd_id == other.gnd_id

    def __str__(self):
        return str(dict({'name': self.name, 'name_presumed': self.name_presumed, 'gnd_id': self.gnd_id,
                         'gnd_first_name': self.gnd_first_name, 'gnd_last_name': self.gnd_last_name,
                         'localizations': self.localizations, 'id': self.id}))


class LetterData:

    def __init__(self, letter_id: str, authors: List[PersonData], recipients: List[PersonData], date: str = '',
                 title: str = '', summary: str = '', quantity_description: str = '', quantity_page_count: int = None,
                 place_of_origin: Place = None, place_of_reception: Place = None):
        self.id = letter_id
        self.authors = authors
        self.recipients = recipients
        self.date = date
        self.title = title
        self.summary = summary
        self.quantity_description = quantity_description
        self.quantity_page_count = quantity_page_count
        self.place_of_origin = place_of_origin
        self.place_of_reception = place_of_reception

    def __str__(self):
        return str(dict({'authors': self.authors, 'recipients': self.recipients, 'date': self.date,
                         'title': self.title, 'summary': self.summary, 'id': self.id,
                         'quantity_description': self.quantity_description,
                         'quantity_page_count': self.quantity_page_count, 'place_of_origin': self.place_of_origin,
                         'place_of_reception': self.place_of_reception}))

    @staticmethod
    def parse_page_count(value):
        match = PAGE_COUNT_PATTERN.match(value)
        if match is not None:
            return match.group(1)
        else:
            return -1
