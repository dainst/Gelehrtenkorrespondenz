import logging

from neo4j.v1 import GraphDatabase
from graph_db_imports.data_structures import *

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _import_locations(session, data: List[LetterData]):
    logger.info('Importing place nodes.')
    locations = set()

    for letter in data:
        for person in letter.authors:
            for localization in person.localizations:
                if localization.location not in locations:
                    locations.add(localization.location)
        for person in letter.recipients:
            for localization in person.localizations:
                if localization.location not in locations:
                    locations.add(localization.location)

    statement = \
        'CREATE (place:Place{label: {label}, gazetteer_id:{gazetteer_id}})'

    with session.begin_transaction() as tx:
        for location in locations:
            tx.run(statement, {'label': location.label, 'gazetteer_id': location.gazetteer_id})


def _import_localisations(session, data: List[LetterData]):
    logger.info('Importing localization nodes.')
    localisations = set()

    for letter in data:
        for person in letter.authors:
            for localization in person.localizations:
                if localization not in localisations:
                    localisations.add(localization)
        for person in letter.recipients:
            for localization in person.localizations:
                if localization not in localisations:
                    localisations.add(localization)

    statement = \
        'MATCH (place:Place{label: {place_label}})' \
        'CREATE (localization:Localization{from: {from}, to: {to}})-[:HAS_PLACE]->(place)'

    with session.begin_transaction() as tx:
        for localization in localisations:
            tx.run(statement,
                   {
                       'from': localization.date_from,
                       'to': localization.date_to,
                       'place_label': localization.location.label
                   })


def _import_persons(session, data: List[LetterData]):
    logger.info('Importing person nodes.')
    persons = set()

    for letter in data:
        for person in letter.authors:
            if person not in persons:
                persons.add(person)
        for person in letter.recipients:
            if person not in persons:
                persons.add(person)

    statement = \
        'CREATE (person:Person{label: {label}, gnd_id: {gnd_id}, first_name: {first_name}, last_name: {last_name}})'

    link_statement = \
        'MATCH (place:Place{label: {place_label}})' \
        'MATCH (localization: Localization{from: {from}, to: {to}})-[:HAS_PLACE]->(place)' \
        'MATCH (person:Person{label: {person_label}, gnd_id: {gnd_id}, first_name: {first_name}, last_name: {last_name}})' \
        'CREATE (person)-[:RESIDES]->(localization)'

    with session.begin_transaction() as tx:
        for person in persons:
            tx.run(statement,
                   {
                       'label': person.label,
                       'gnd_id': person.gnd_id,
                       'first_name': person.first_name,
                       'last_name': person.last_name
                   })
        for person in persons:
            for localization in person.localizations:

                input_data = {
                    'place_label': localization.location.label,
                    'from': localization.date_from,
                    'to': localization.date_to,
                    'person_label': person.label,
                    'gnd_id': person.gnd_id,
                    'first_name': person.first_name,
                    'last_name': person.last_name
                }

                tx.run(link_statement, input_data)


def _import_letters(session, data: List[LetterData]):
    logger.info('Importing letter nodes.')

    statement = \
        'CREATE (letter:Letter{date: {date}, title: {title}, summary: {summary}, quantity_description: {quantity_description}, quantity_page_count: {quantity_page_count}})'

    author_link_statement = \
        'MATCH (letter:Letter{date: {date}, title: {title}, summary: {summary}, quantity_description: {quantity_description}, quantity_page_count: {quantity_page_count}})' \
        'MATCH (person:Person{label: {label_person}})' \
        'CREATE (person)-[:IS_AUTHOR]->(letter)'

    recipient_link_statement = \
        'MATCH (letter:Letter{date: {date}, title: {title}, summary: {summary}, quantity_description: {quantity_description}, quantity_page_count: {quantity_page_count}})' \
        'MATCH (person:Person{label: {label_person}})' \
        'CREATE (person)-[:IS_RECIPIENT]->(letter)'

    with session.begin_transaction() as tx:
        for letter in data:

            input_data = {
                'date': letter.date,
                'title': letter.title,
                'summary': letter.summary,
                'quantity_description': letter.quantity_description,
                'quantity_page_count': letter.quantity_page_count
            }

            tx.run(statement, input_data)

            for author in letter.authors:
                author_link_input_data = {**input_data, **{'label_person': author.label}}
                tx.run(author_link_statement, author_link_input_data)

            for recipient in letter.recipients:
                recipient_link_input_data = {**input_data, **{'label_person': recipient.label}}
                tx.run(recipient_link_statement, recipient_link_input_data)


def write_data(data, url, port, username, password):
    driver = GraphDatabase.driver('bolt://%s:%i ' % (url, port), auth=(username, password))

    with driver.session() as session:
        _import_locations(session, data)
        _import_localisations(session, data)
        _import_persons(session, data)
        _import_letters(session, data)
