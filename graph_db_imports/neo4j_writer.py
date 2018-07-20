import logging

from neo4j.v1 import GraphDatabase
from data_structures import *
from typing import Set

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


"""def _import_places(session, data: List[LetterData]):
    logger.info('Importing place nodes.')
    places = dict()

    for letter in data:
        for person in letter.authors:
            for localization in person.localizations:
                if localization.place.label not in places:
                    places[localization.place.label] = localization.place
                elif places[localization.place.label].gnd_id == '-1' and localization.place.gnd_id != '-1':
                    places[localization.place.label] = localization.place

        for person in letter.recipients:
            for localization in person.localizations:
                if localization.place.label not in places:
                    places[localization.place.label] = localization.place
                elif places[localization.place.label].gnd_id == '-1' and localization.place.gnd_id != '-1':
                    places[localization.place.label] = localization.place

    parameters = dict({'place_list': []})
    for key in places:
        parameters['place_list'].append({
            'label': places[key].label, 'gnd_id': places[key].gnd_id, 'lat': places[key].lat, 'lng': places[key].lng
        })

    statement = \
        'UNWIND {place_list} as data ' \
        'CREATE (n:Place) ' \
        'SET n = data'

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_localisations(session, data: List[LetterData]):
    logger.info('Importing localization nodes.')
    localisations: Set[LocalizationTimeSpan] = set()

    for letter in data:
        for person in letter.authors:
            for localization in person.localizations:
                if localization not in localisations:
                    localisations.add(localization)
        for person in letter.recipients:
            for localization in person.localizations:
                if localization not in localisations:
                    localisations.add(localization)

    parameters = dict({'localization_list': []})
    for localization in localisations:
        parameters['localization_list'].append({
            'from': localization.date_from,
            'to': localization.date_to,
            'label': localization.place.label
        })

    statement = \
        'UNWIND {localization_list} as data ' \
        'MATCH (place:Place {label: data.label}) ' \
        'CREATE (localization:Localization{from: data.from, to: data.to})-[:HAS_PLACE]->(place)'

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_persons(session, data: List[LetterData]):
    logger.info('Importing person nodes.')
    persons: Set[PersonData] = set()

    for letter in data:
        for person in letter.authors:
            if person not in persons:
                persons.add(person)
        for person in letter.recipients:
            if person not in persons:
                persons.add(person)

    parameters = dict({'person_list': []})

    for person in persons:
        data = {
            'uuid': person.uuid,
            'label': person.name,
            'gnd_id': person.gnd_id,
            'gnd_first_name': person.gnd_first_name,
            'gnd_last_name': person.gnd_last_name,
            'localizations': []
        }

        for localization in person.localizations:
            data['localizations'].append({
                'label_place': localization.place.label,
                'from': localization.date_from,
                'to': localization.date_to
            })

        parameters['person_list'].append(data)

    statement = \
        'UNWIND {person_list} AS data ' \
        'CREATE (person:Person{uuid: data.uuid, label: data.label, gnd_id: data.gnd_id, gnd_first_name: data.gnd_first_name, gnd_last_name: data.gnd_last_name})' \
        'WITH person, data ' \
        'UNWIND data.localizations AS local_data ' \
        'MATCH (place:Place{label: local_data.label_place}) ' \
        'MATCH (localization:Localization{from: local_data.from, to: local_data.to})' \
        'MATCH (localization)-[:HAS_PLACE]->(place) ' \
        'CREATE (person)-[:RESIDES]->(localization)'

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_letters(session, data: List[LetterData]):
    logger.info('Importing letter nodes.')

    parameters = {
        'letter_list': []
    }
    for letter in data:
        data = {
            'id': letter.id,
            'date': letter.date,
            'title': letter.title,
            'summary': letter.summary,
            'quantity_description': letter.quantity_description,
            'quantity_page_count': letter.quantity_page_count,
            'place_of_origin_label': letter.place_of_origin.label,
            'place_of_reception_label': letter.place_of_reception.label,
            'authors': [],
            'recipients': []
        }

        for author in letter.authors:
            data['authors'].append(
                {'name': author.name, 'gnd_id': author.gnd_id, 'name_presumed': author.name_presumed}
            )
        for recipient in letter.recipients:
            data['recipients'].append(
                {'name': recipient.name, 'gnd_id': recipient.gnd_id, 'name_presumed': recipient.name_presumed}
            )

        parameters['letter_list'].append(data)

    statement = \
        'UNWIND {letter_list} as data ' \
        'MATCH (poo:Place{label: data.place_of_origin_label}) ' \
        'MATCH (por:Place{label: data.place_of_reception_label}) ' \
        'CREATE (letter:Letter{id: data.id, date: data.date, title: data.title, summary: data.summary, quantity_description: data.quantity_description, quantity_page_count: data.quantity_page_count}) ' \
        'CREATE (letter)-[:SEND_FROM]->(poo)' \
        'CREATE (letter)-[:SEND_TO]->(por)' \
        'WITH letter, data ' \
        'UNWIND data.authors as person_data ' \
        'MATCH (person:Person {label: person_data.name, gnd_id: person_data.gnd_id}) ' \
        'CREATE (person) -[:IS_AUTHOR { presumed: person_data.name_presumed }]-> (letter) ' \
        'WITH letter, data ' \
        'UNWIND data.recipients as person_data ' \
        'MATCH (person:Person{label: person_data.name, gnd_id: person_data.gnd_id}) ' \
        'CREATE (person) -[:IS_RECIPIENT { presumed: person_data.name_presumed }]-> (letter)'

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def write_data(data, url, port, username, password):
    driver = GraphDatabase.driver('bolt://%s:%i ' % (url, port), auth=(username, password))

    with driver.session() as session:
        with session.begin_transaction() as tx:
            tx.run('CREATE INDEX ON :Place(gnd_id)')
            tx.run('CREATE INDEX ON :Localization(from, to)')
            tx.run('CREATE INDEX ON :Person(gnd_id)')
            tx.run('CREATE CONSTRAINT ON (letter:Letter) ASSERT letter.id IS UNIQUE')

        _import_places(session, data)
        _import_localisations(session, data)
        _import_persons(session, data)
        _import_letters(session, data)

    logger.info('Done.')"""


def _import_place_list(session, data: List[Letter]):
    logger.info('Importing place nodes.')
    places = dict()

    for letter in data:
        if letter.place_of_origin is not None and letter.place_of_origin.label is not None:
            if letter.place_of_origin.label not in places:
                places[letter.place_of_origin.label] = letter.place_of_origin
            elif places[letter.place_of_origin.label].gnd_id == '-1' and letter.place_of_origin.gnd_id != '-1':
                places[letter.place_of_origin.label] = letter.place_of_origin

        if letter.place_of_reception is not None and letter.place_of_reception.label is not None:
            if letter.place_of_reception.label not in places:
                places[letter.place_of_reception.label] = letter.place_of_reception
            elif places[letter.place_of_reception.label].gnd_id == '-1' and letter.place_of_reception.gnd_id != '-1':
                places[letter.place_of_reception.label] = letter.place_of_reception

    parameters = dict({'place_list': []})
    for key in places:
        parameters['place_list'].append({
            'label': places[key].label, 'gnd_id': places[key].gnd_id, 'lat': places[key].lat, 'lng': places[key].lng
        })

    statement = \
        'UNWIND {place_list} as data ' \
        'CREATE (n:Place) ' \
        'SET n = data'

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_person_list(session, data: List[Letter]):
    logger.info('Importing person nodes.')
    persons: Set[Person] = set()

    for letter in data:
        for person in letter.authors:
            if person not in persons:
                persons.add(person)
        for person in letter.recipients:
            if person not in persons:
                persons.add(person)

    parameters = dict({'person_list': []})

    for person in persons:
        data = {
            'uuid': person.uuid,
            'label': person.name,
            'gnd_id': person.gnd_id,
            'gnd_first_name': person.gnd_first_name,
            'gnd_last_name': person.gnd_last_name
        }

        parameters['person_list'].append(data)

    statement = \
        'UNWIND {person_list} AS data ' \
        'CREATE (person:Person{uuid: data.uuid, label: data.label, gnd_id: data.gnd_id, gnd_first_name: data.gnd_first_name, gnd_last_name: data.gnd_last_name})' \

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_letter_list(session, data: List[Letter]):
    logger.info('Importing letter nodes.')

    parameters = {
        'letter_list': []
    }
    for letter in data:
        data = {
            'id': letter.id,
            'date': letter.date,
            'title': letter.title,
            'summary': letter.summary,
            'quantity_description': letter.quantity_description,
            'quantity_page_count': letter.quantity_page_count,
            'place_of_origin_label': letter.place_of_origin.label,
            'place_of_reception_label': letter.place_of_reception.label,
            'authors': [],
            'recipients': []
        }

        for author in letter.authors:
            data['authors'].append(
                {'name': author.name, 'gnd_id': author.gnd_id, 'name_presumed': author.name_presumed}
            )
        for recipient in letter.recipients:
            data['recipients'].append(
                {'name': recipient.name, 'gnd_id': recipient.gnd_id, 'name_presumed': recipient.name_presumed}
            )

        parameters['letter_list'].append(data)

    statement = \
        'UNWIND {letter_list} as data ' \
        'MATCH (poo:Place{label: data.place_of_origin_label}) ' \
        'MATCH (por:Place{label: data.place_of_reception_label}) ' \
        'CREATE (letter:Letter{id: data.id, date: data.date, title: data.title, summary: data.summary, quantity_description: data.quantity_description, quantity_page_count: data.quantity_page_count}) ' \
        'CREATE (letter)-[:SEND_FROM]->(poo)' \
        'CREATE (letter)-[:SEND_TO]->(por)' \
        'WITH letter, data ' \
        'UNWIND data.authors as person_data ' \
        'MATCH (person:Person {label: person_data.name, gnd_id: person_data.gnd_id}) ' \
        'CREATE (person) -[:IS_AUTHOR { presumed: person_data.name_presumed }]-> (letter) ' \
        'WITH letter, data ' \
        'UNWIND data.recipients as person_data ' \
        'MATCH (person:Person{label: person_data.name, gnd_id: person_data.gnd_id}) ' \
        'CREATE (person) -[:IS_RECIPIENT { presumed: person_data.name_presumed }]-> (letter)'

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def import_data(data, url, port, username, password):
    logger.info('-----')
    logger.info('Starting import ...')
    logger.info('-----')

    driver = GraphDatabase.driver('bolt://%s:%i ' % (url, port), auth=(username, password))

    with driver.session() as session:
        with session.begin_transaction() as tx:
            tx.run('CREATE INDEX ON :Place(gnd_id)')
            tx.run('CREATE INDEX ON :Person(gnd_id)')
            tx.run('CREATE CONSTRAINT ON (letter:Letter) ASSERT letter.id IS UNIQUE')

        _import_place_list(session, data)
        _import_person_list(session, data)
        _import_letter_list(session, data)

    logger.info('=====')
    logger.info('Import done.')
    logger.info('=====')
