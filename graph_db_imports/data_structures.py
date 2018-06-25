from typing import List
import re

PAGE_COUNT_PATTERN = re.compile('.*(\d+)\s*Seiten.*')


class Location:

    def __init__(self, label: str, gnd_id: str):
        self.label = label
        self.gnd_id = gnd_id
        self.id = self.gnd_id

    def __hash__(self):
        return hash((self.label, self.gnd_id, self.id))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.label == other.label and self.gnd_id == other.gnd_id and self.id == other.id

    def __str__(self):
        return str(dict({'label': self.label, 'gnd_id': self.gnd_id, 'id': self.id}))


class LocalizationPoint:

    def __init__(self, location: Location, date: str):
        self.date = date
        self.location = location

    def __str__(self):
        return str(dict({'date': self.date, 'location': self.location}))


class LocalizationTimeSpan:

    def __init__(self, location: Location, date_from: str = '', date_to: str = ''):
        self.location = location
        self.date_from = date_from
        self.date_to = date_to

    def __hash__(self):
        return hash((self.location, self.date_from, self.date_to))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.location == other.location and self.date_from == other.date_from and self.date_to == other.date_to

    def __str__(self):
        return str(dict({'date_from': self.date_from, 'date_to': self.date_to, 'location': self.location}))

    @staticmethod
    def aggregate_localization_points_to_timespan(localization_points: List[LocalizationPoint]):
        localization_points = sorted(localization_points, key=lambda x: (x.date, x.location.label))

        persons_localizations_list = []

        current_location = localization_points[0].location
        current_date_from = localization_points[0].date
        current_date_to = localization_points[0].date

        for current_point in localization_points:

            if current_location.id != current_point.location.id:
                persons_localizations_list.append(
                    LocalizationTimeSpan(current_location, current_date_from, current_date_to)
                )

                current_location = current_point.location
                current_date_from = current_point.date
                current_date_to = current_point.date
            else:
                current_date_to = current_point.date

        persons_localizations_list.append(LocalizationTimeSpan(current_location, current_date_from, current_date_to))

        return persons_localizations_list


class PersonData:

    def __init__(self, name: str, gnd_id: str, localizations: List[LocalizationTimeSpan],
                 first_name: str = '', last_name: str = ''):
        self.label = name
        self.gnd_id = gnd_id
        self.first_name = first_name
        self.last_name = last_name
        self.localizations = localizations

        self.id = self.gnd_id

    def __hash__(self):
        return hash((self.label, self.gnd_id, self.first_name, self.last_name))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.label == other.label and self.gnd_id == other.gnd_id and self.first_name == other.first_name and \
            self.last_name == other.last_name

    def __str__(self):
        return str(dict({'label': self.label, 'gnd_id': self.gnd_id, 'first_name': self.first_name,
                         'last_name': self.last_name, 'localizations': self.localizations, 'id': self.id}))


class LetterData:

    def __init__(self, letter_id: str, authors: List[PersonData], recipients: List[PersonData], date: str = '',
                 title: str = '', summary: str = '', quantity_description: str = '', quantity_page_count: int = None):
        self.id = letter_id
        self.authors = authors
        self.recipients = recipients
        self.date = date
        self.title = title
        self.summary = summary
        self.quantity_description = quantity_description
        self.quantity_page_count = quantity_page_count

    def __str__(self):
        return str(dict({'authors': self.authors, 'recipients': self.recipients, 'date': self.date,
                         'title': self.title, 'summary': self.summary, 'id': self.id,
                         'quantity_description': self.quantity_description,
                         'quantity_page_count': self.quantity_page_count}))

    @staticmethod
    def parse_page_count(value):
        match = PAGE_COUNT_PATTERN.match(value)
        if match is not None:
            return match.group(1)
        else:
            return -1
