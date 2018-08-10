import logging

from neo4j.v1 import GraphDatabase
from data_structures import *
from typing import Set

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _import_place_nodes(session, data: List[Letter]):
    logger.info('Importing place nodes.')
    places: Set[Place] = set()

    for letter in data:
        origin_place = letter.origin_place
        reception_place = letter.reception_place

        if origin_place is not None and origin_place not in places:
            places.add(origin_place)

        if reception_place is not None and reception_place not in places:
            places.add(reception_place)

    parameters = dict({'place_list': []})
    for place in places:
        parameters['place_list'].append(
            {
                'name': place.name,
                'auth_source': place.auth_source,
                'auth_id': place.auth_id,
                'auth_name': place.auth_name,
                'auth_lat': place.auth_lat,
                'auth_lng': place.auth_lng
            }
        )

    statement = """
        UNWIND {place_list} as place
        CREATE (n:Place)
        SET n = place
        """

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_person_nodes(session, data: List[Letter]):
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
        parameters['person_list'].append({
            'name': person.name,
            'is_corporation': person.is_corporation,
            'auth_source': person.auth_source,
            'auth_id': person.auth_id,
            'auth_first_name': person.auth_first_name,
            'auth_last_name': person.auth_last_name
        })

    statement = """
        UNWIND {person_list} AS person
        CREATE (n:Person)
        SET n = person
    """

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_letter_nodes(session, data: List[Letter]):
    logger.info('Importing letter nodes.')

    parameters = {'letter_list': []}

    for letter in data:
        parameters['letter_list'].append({
            'kalliope_id': letter.kalliope_id,
            'title': letter.title,
            'language_codes': ', '.join(letter.language_codes),
            'origin_date_from': str(letter.origin_date_from),
            'origin_date_till': str(letter.origin_date_till),
            'origin_date_presumed': letter.origin_date_presumed,
            'extent': letter.extent,
            'summary_paragraphs': ' | '.join(letter.summary_paragraphs)
        })

    statement = """
        UNWIND {letter_list} as letter
        CREATE (n:Letter)
        SET n = letter
    """

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_send_from_relationships(session, data: List[Letter]):
    logger.info('Importing send_from relationships.')

    parameters = {'place_of_origin': []}

    for letter in data:
        if letter.origin_place is not None:
            parameters['place_of_origin'].append({
                    'letter_id': letter.kalliope_id,
                    'name': letter.origin_place.name,
                    'name_presumed': letter.origin_place.name_presumed,
                    'auth_source': letter.origin_place.auth_source,
                    'auth_id': letter.origin_place.auth_id
                })

    statement = """
        UNWIND {place_of_origin} as place_of_origin
        MATCH (letter:Letter { kalliope_id: place_of_origin.letter_id })
        MATCH (place:Place {
                    name: place_of_origin.name,
                    auth_source: place_of_origin.auth_source,
                    auth_id: place_of_origin.auth_id
                    }
              )
        CREATE (letter) -[:SEND_FROM { presumed: place_of_origin.name_presumed }]-> (place)
    """

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_send_to_relationships(session, data: List[Letter]):
    logger.info('Importing send_to relationships.')

    parameters = {'place_of_reception': []}

    for letter in data:
        if letter.reception_place is not None:
            parameters['place_of_reception'].append({
                'letter_id': letter.kalliope_id,
                'name': letter.reception_place.name,
                'name_presumed': letter.reception_place.name_presumed,
                'auth_source': letter.reception_place.auth_source,
                'auth_id': letter.reception_place.auth_id
            })

    statement = """
        UNWIND {place_of_reception} as place_of_reception
        MATCH (letter:Letter { kalliope_id: place_of_reception.letter_id })
        MATCH (place:Place {
                    name: place_of_reception.name,
                    auth_source: place_of_reception.auth_source,
                    auth_id: place_of_reception.auth_id
                    }
              )
        CREATE (letter) -[:SEND_TO { presumed: place_of_reception.name_presumed }]-> (place)
    """

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_is_author_relationships(session, data: List[Letter]):
    logger.info('Importing is_author relationships.')

    parameters = {'is_author_list': []}

    for letter in data:
        for author in letter.authors:
            parameters['is_author_list'].append({
                'letter_id': letter.kalliope_id,
                'name': author.name,
                'name_presumed': author.name_presumed,
                'auth_source': author.auth_source,
                'auth_id': author.auth_id
            })

    statement = """
        UNWIND {is_author_list} as is_author
        MATCH (letter:Letter { kalliope_id: is_author.letter_id })
        MATCH (person:Person {
                        name: is_author.name,
                        auth_source: is_author.auth_source,
                        auth_id: is_author.auth_id
                        }
              )
        CREATE (person) -[:IS_AUTHOR { presumed: is_author.name_presumed }]-> (letter)
    """

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def _import_is_recipient_relationships(session, data: List[Letter]):
    logger.info('Importing is_recipient relationships.')

    parameters = {'is_recipient_list': []}

    for letter in data:
        for recipient in letter.recipients:
            parameters['is_recipient_list'].append({
                'letter_id': letter.kalliope_id,
                'name': recipient.name,
                'name_presumed': recipient.name_presumed,
                'auth_source': recipient.auth_source,
                'auth_id': recipient.auth_id
            })

    statement = """
        UNWIND {is_recipient_list} as is_recipient
        MATCH (letter:Letter { kalliope_id: is_recipient.letter_id })
        MATCH (person:Person {
                        name: is_recipient.name,
                        auth_source: is_recipient.auth_source,
                        auth_id: is_recipient.auth_id
                        }
              )
        CREATE (person) -[:IS_RECIPIENT { presumed: is_recipient.name_presumed }]-> (letter)
    """

    with session.begin_transaction() as tx:
        tx.run(statement, parameters)


def import_data(data, url, port, username, password):
    logger.info('-----')
    logger.info('Starting import ...')
    logger.info('-----')

    driver = GraphDatabase.driver('bolt://%s:%i ' % (url, port), auth=(username, password))

    with driver.session() as session:
        with session.begin_transaction() as tx:
            tx.run('CREATE INDEX ON :Place(name)')
            tx.run('CREATE INDEX ON :Person(name)')
            tx.run('CREATE CONSTRAINT ON (letter:Letter) ASSERT letter.kalliope_id IS UNIQUE')

        _import_place_nodes(session, data)
        _import_person_nodes(session, data)
        _import_letter_nodes(session, data)
        _import_send_from_relationships(session, data)
        _import_send_to_relationships(session, data)
        _import_is_author_relationships(session, data)
        _import_is_recipient_relationships(session, data)

    logger.info('=====')
    logger.info('Import done.')
    logger.info('=====')
