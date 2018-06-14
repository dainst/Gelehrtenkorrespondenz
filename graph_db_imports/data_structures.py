from typing import List


class Location:

    def __init__(self, label: str, gazetteer_id: int):
        self.label = label
        self.gazetteer_id = gazetteer_id
        self.id = label


class LocalizationPoint:

    def __init__(self, location: Location, date: str):
        self.date = date
        self.location = location


class Localization:

    def __init__(self, location: Location, date_from: str = None, date_to: str = None):
        self.location = location
        self.date_from = date_from
        self.date_to = date_to


class PersonData:

    def __init__(self, name: str, gnd_id: int, localizations: List[Localization],
                 first_name: str = None, last_name: str = None):
        self.label = name
        self.gnd_id = gnd_id
        self.first_name = first_name
        self.last_name = last_name
        self.localizations = localizations

        self.id = self.label


class LetterData:

    def __init__(self, authors: List[PersonData], recipients: List[PersonData], date: str = None, title: str = None,
                 summary: str = None, quantity_description: str = None, quantity_page_count: int = None):
        self.authors = authors
        self.recipients = recipients
        self.date = date
        self.title = title
        self.summary = summary
        self.quantity_description = quantity_description
        self.quantity_page_count = quantity_page_count
