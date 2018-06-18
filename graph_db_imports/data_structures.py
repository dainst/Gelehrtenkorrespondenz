from typing import List


class Location:

    def __init__(self, label: str, gazetteer_id: int):
        self.label = label
        self.gazetteer_id = gazetteer_id
        self.id = label

    def __hash__(self):
        return hash((self.label, self.gazetteer_id, self.id))

    def __eq__(self, other):
        if not isinstance(other, type(self)): return NotImplemented
        return self.label == other.label and self.gazetteer_id == other.gazetteer_id and self.id == other.id


class LocalizationPoint:

    def __init__(self, location: Location, date: str):
        self.date = date
        self.location = location


class LocalizationTimespan:

    def __init__(self, location: Location, date_from: str = '', date_to: str = ''):
        self.location = location
        self.date_from = date_from
        self.date_to = date_to

    def __hash__(self):
        return hash((self.location, self.date_from, self.date_to))

    def __eq__(self, other):
        if not isinstance(other, type(self)): return NotImplemented
        return self.location == other.location and self.date_from == other.date_from and self.date_to == other.date_to

    @staticmethod
    def aggregate_localization_points_to_timespan(localization_points: List[LocalizationPoint]):
        localization_points = sorted(localization_points, key=lambda x: (x.date, x.location.label))

        persons_localizations_list = []

        current_location = localization_points[0].location
        current_date_from = localization_points[0].date
        current_date_to = localization_points[0].date

        for current_point in localization_points:

            if current_location.id != current_point.location.id:
                persons_localizations_list.append(LocalizationTimespan(current_location, current_date_from, current_date_to))

                current_location = current_point.location
                current_date_from = current_point.date
                current_date_to = current_point.date
            else:
                current_date_to = current_point.date

        persons_localizations_list.append(LocalizationTimespan(current_location, current_date_from, current_date_to))

        return persons_localizations_list


class PersonData:

    def __init__(self, name: str, gnd_id: int, localizations: List[LocalizationTimespan],
                 first_name: str = '', last_name: str = ''):
        self.label = name
        self.gnd_id = gnd_id
        self.first_name = first_name
        self.last_name = last_name
        self.localizations = localizations

        self.id = self.label

    def __hash__(self):
        return hash((self.label, self.gnd_id, self.first_name, self.last_name))

    def __eq__(self, other):
        if not isinstance(other, type(self)): return NotImplemented
        return self.label == other.label and self.gnd_id == other.gnd_id and self.first_name == other.first_name and \
            self.last_name == other.last_name


class LetterData:

    def __init__(self, authors: List[PersonData], recipients: List[PersonData], date: str = '', title: str = '',
                 summary: str = '', quantity_description: str = '', quantity_page_count: int = None):
        self.authors = authors
        self.recipients = recipients
        self.date = date
        self.title = title
        self.summary = summary
        self.quantity_description = quantity_description
        self.quantity_page_count = quantity_page_count
