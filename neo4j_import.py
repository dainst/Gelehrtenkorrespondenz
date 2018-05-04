import sys
import re

from neo4j.v1 import GraphDatabase

PAGE_COUNT_PATTERN = re.compile('.*(\d+)\s*Seiten.*')


def _extract_locations(line_values):
    result = {
        'from': {'name': line_values[5].rstrip('.'), 'gazetteer_id': line_values[6]},
        'to': {'name': line_values[15].rstrip('.'), 'gazetteer_id': line_values[16]}
    }

    return result


def _extract_date(line_values):
    return line_values[7]


def _extract_persons(line_values):
    author_indices = [(0, 1), (2, 3)]
    recipient_indices = [(9, 10), (11, 12), (13, 14)]
    result = {
        'authors': [
            {'name': line_values[i].rstrip(','), 'gnd_id': line_values[j]}
            for (i, j) in author_indices if line_values[i] != ''
        ],
        'recipients': [
            {'name': line_values[i].rstrip(','), 'gnd_id': line_values[j]}
            for (i, j) in recipient_indices if line_values[i] != ''
        ]
    }

    return result


def _extract_letter(line_values):
    result = {
        'title': line_values[4],
        'date': line_values[7],
        'quantity_description': line_values[8],
        'quantity_page_count': _parse_page_count(line_values[8]),
        'summary': line_values[17]
    }

    return result


def _parse_page_count( value):
    match = PAGE_COUNT_PATTERN.match(value)
    if match is not None:
        return match.group(1)
    else:
        return -1


def import_data(tsv_path, uri, user, password, ignore_first_line):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session, open(tsv_path, 'r') as input_file:

        counter = 0
        for line in input_file:
            if ignore_first_line:
                ignore_first_line = False
                continue

            line_values = line.split('\t')

            locations = _extract_locations(line_values)
            persons = _extract_persons(line_values)
            letter = _extract_letter(line_values)

            localisation_statement = \
                'MERGE (location:Location {name:{name}, gazetteer_id:{gazetteer_id}})' \
                'MERGE (date:Date{date:{date}})' \
                'MERGE (location)-[:DEFINES]->(l:Localisation)<-[:DEFINES]-(date)' \
                'MERGE (date)<-[:IS_DEFINED_BY_DATE]-(l)-[:IS_DEFINED_BY_LOCATION]->(location)'

            letter_statement = \
                'MATCH (date:Date{date:{date}})' \
                'CREATE (letter:Letter{title:{title}, desc:{desc}, quant:{quant}, summ:{summ}, id:{id}})' \
                'CREATE (date)-[:DATES]->(letter)-[:WAS_WRITTEN_DATE]->(date)'

            person_statement = \
                'MATCH (location:Location {name:{location_name}, gazetteer_id:{gazetteer_id}})' \
                'MATCH (date:Date{date:{date}})' \
                'MATCH (location)-[:DEFINES]->(l:Localisation)<-[DEFINES]-(date)' \
                'MERGE (person:Person {name:{name}, gnd_id:{gnd_id}})' \
                'MERGE (l)-[:LOCALIZES]->(person)-[:IS_LOCALIZED_BY]->(l)' \

            link_author_statement \
                = 'MATCH (letter:Letter{title:{title}, desc:{desc}, quant:{quant}, summ:{summ}, id:{id}})' \
                  'MATCH (person:Person {name:{name}, gnd_id:{gnd_id}})' \
                  'CREATE (person)-[:IS_AUTHOR]->(letter)-[:IS_AUTHERED_BY]->(person)'

            link_recipient_statement \
                = 'MATCH (letter:Letter{title:{title}, desc:{desc}, quant:{quant}, summ:{summ}, id:{id}})' \
                  'MATCH (person:Person {name:{name}, gnd_id:{gnd_id}})' \
                  'CREATE (person)-[:IS_RECIPIENT_OF]->(letter)-[:IS_RECEIVED_BY]->(person)'

            with session.begin_transaction() as tx:
                tx.run(localisation_statement,
                       {
                           'date': line_values[7],
                           'name': locations['from']['name'],
                           'gazetteer_id': locations['from']['gazetteer_id']
                       })
                tx.run(localisation_statement,
                       {
                           'date': line_values[7],
                           'name': locations['to']['name'],
                           'gazetteer_id': locations['to']['gazetteer_id']
                       })

                tx.run(letter_statement,
                       {
                           'title': letter['title'],
                           'date': letter['date'],
                           'desc': letter['quantity_description'],
                           'quant': letter['quantity_page_count'],
                           'summ': letter['summary'],
                           'id': counter
                       })

                for person in persons['authors']:
                    tx.run(person_statement,
                           {
                               'date': line_values[7],
                               'location_name': locations['from']['name'],
                               'gazetteer_id': locations['from']['gazetteer_id'],
                               'name': person['name'],
                               'gnd_id': person['gnd_id']
                           })

                    tx.run(link_author_statement,
                           {
                               'title': letter['title'],
                               'date': letter['date'],
                               'desc': letter['quantity_description'],
                               'quant': letter['quantity_page_count'],
                               'summ': letter['summary'],
                               'name': person['name'],
                               'gnd_id': person['gnd_id'],
                               'id': counter
                           })

                for person in persons['recipients']:
                    tx.run(person_statement,
                           {
                               'date': line_values[7],
                               'location_name': locations['to']['name'],
                               'gazetteer_id': locations['to']['gazetteer_id'],
                               'name': person['name'],
                               'gnd_id': person['gnd_id']
                           })

                    tx.run(link_recipient_statement,
                           {
                               'title': letter['title'],
                               'date': letter['date'],
                               'desc': letter['quantity_description'],
                               'quant': letter['quantity_page_count'],
                               'summ': letter['summary'],
                               'name': person['name'],
                               'gnd_id': person['gnd_id'],
                               'id': counter
                           })
            counter += 1

    driver.close()


if __name__ == '__main__':
    import_data(
        tsv_path=sys.argv[1],
        ignore_first_line=True,
        uri=sys.argv[2],
        user=sys.argv[3],
        password=sys.argv[4]
    )
