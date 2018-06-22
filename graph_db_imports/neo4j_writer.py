import logging

from neo4j.v1 import GraphDatabase
from data_structures import *

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

    props = dict({'props': []})
    for location in locations:
        props['props'].append({
            'label': location.label, 'gnd_id': location.gnd_id
        })

    statement = \
        'UNWIND {props} as props ' \
        'CREATE (n:Place) ' \
        'SET n = props'

    with session.begin_transaction() as tx:
        tx.run(statement, props)


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

    props = dict({'props': []})
    for localization in localisations:
        props['props'].append({
            'from': localization.date_from,
            'to': localization.date_to,
            'gnd_id': localization.location.gnd_id
        })

    statement = \
        'UNWIND {props} as props ' \
        'MATCH (place:Place {gnd_id: props.gnd_id}) ' \
        'CREATE (localization:Localization{from: props.from, to: props.to})-[:HAS_PLACE]->(place)'

    with session.begin_transaction() as tx:
        tx.run(statement, props)


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

    props = dict({'props': []})

    for person in persons:
        current_props = {
            'label': person.label,
            'gnd_id': person.gnd_id,
            'first_name': person.first_name,
            'last_name': person.last_name,
            'localizations': []
        }

        for localization in person.localizations:
            current_props['localizations'].append({
                'gnd_id_location': localization.location.gnd_id,
                'from': localization.date_from,
                'to': localization.date_to
            })

        props['props'].append(current_props)

    statement = \
        'UNWIND {props} AS props ' \
        'CREATE (person:Person{label: props.label, gnd_id: props.gnd_id, first_name: props.first_name, last_name: props.last_name})' \
        'WITH person, props ' \
        'UNWIND props.localizations AS local_props ' \
        'MATCH (place:Place{gnd_id: local_props.gnd_id_location}) ' \
        'MATCH (localization: Localization{from: local_props.from, to: local_props.to})-[:HAS_PLACE]->(place) ' \
        'CREATE (person)-[:RESIDES]->(localization)'

    with session.begin_transaction() as tx:
        tx.run(statement, props)


def _import_letters(session, data: List[LetterData]):
    logger.info('Importing letter nodes.')

    props = dict({'props': []})
    for letter in data:
        current_props = {
            'date': letter.date,
            'title': letter.title,
            'summary': letter.summary,
            'quantity_description': letter.quantity_description,
            'quantity_page_count': letter.quantity_page_count,
            'authors': [],
            'recipients': []
        }

        for author in letter.authors:
            current_props['authors'].append({'gnd_id': author.gnd_id})
        for recipient in letter.recipients:
            current_props['recipients'].append({'gnd_id': recipient.gnd_id})

        props['props'].append(current_props)

    statement = \
        'UNWIND {props} as props ' \
        'CREATE (letter:Letter{date: props.date, title: props.title, summary: props.summary, quantity_description: props.quantity_description, quantity_page_count: props.quantity_page_count}) ' \
        'WITH letter, props ' \
        'UNWIND props.authors as person_props ' \
        'MATCH (person:Person{gnd_id: person_props.gnd_id}) ' \
        'CREATE (person)-[:IS_AUTHOR]->(letter) ' \
        'WITH letter, props ' \
        'UNWIND props.recipients as person_props ' \
        'MATCH (person:Person{gnd_id: person_props.gnd_id}) ' \
        'CREATE (person)-[:IS_RECIPIENT]->(letter)'

    with session.begin_transaction() as tx:
        tx.run(statement, props)


def write_data(data, url, port, username, password):
    driver = GraphDatabase.driver('bolt://%s:%i ' % (url, port), auth=(username, password))

    with driver.session() as session:
        _import_locations(session, data)
        _import_localisations(session, data)
        _import_persons(session, data)
        _import_letters(session, data)
