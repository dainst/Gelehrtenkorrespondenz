import sys
import logging
import re

from neo4j.v1 import GraphDatabase

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PAGE_COUNT_PATTERN = re.compile('.*(\d+)\s*Seiten.*')
DATE_PATTERN = re.compile('\d{4}-\d{2}-\d{2}')


def _extract_locations(line_values):
    result = dict()
    if line_values[5] != '' or line_values[6] != '':
        result['from'] = {'name': line_values[5].rstrip('.'), 'gazetteer_id': line_values[6]}
    else:
        result['from'] = None
    if line_values[15] != '' or line_values[16]:
        result['to'] = {'name': line_values[15].rstrip('.'), 'gazetteer_id': line_values[16]}
    else:
        result['to'] = None
    return result


def _compare_locations(a, b):
    if a is None and b is not None:
        return False
    elif a is not None and b is None:
        return False
    elif a is None and b is None:
        return True

    if a['name'] == b['name']:
        return True
        # TODO: gazetteer IDs are wrong for current (dummy) metadata, for now they are being ignored when comparing
        # if 'gazetteer_id' in a and 'gazetteer_id' in b:
        #     if a['gazetteer_id'] == b['gazetteer_id']:
        #         return True
        #     else:
        #         return False
        # elif 'gazetteer_id' not in a and 'gazetteer_id' not in b:
        #     return True
        # else:
        #     return False
    else:
        return False


def _extract_date(line_values):
    match = DATE_PATTERN.match(line_values[7])
    if match is not None:
        return match.group(0)
    else:
        return ''


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


def _create_localization(date, location):

    localisations = [{
        'location': location,
        'from': date,
        'until': date
    }]
    return localisations


def _import_persons(session, lines):
    persons = dict()
    localizations = dict()
    space_time_points = dict()

    for line_values in lines:

        date = _extract_date(line_values)
        locations = _extract_locations(line_values)

        extracted_data = _extract_persons(line_values)

        if locations['from'] is not None:
            for person in extracted_data['authors']:
                values = tuple(person.values())
                if values not in space_time_points:
                    space_time_points[values] = [(date, locations['from']['name'], locations['from']['gazetteer_id'])]
                else:
                    space_time_points[values] += [(date, locations['from']['name'], locations['from']['gazetteer_id'])]

        if locations['to'] is not None:
            for person in extracted_data['recipients']:
                values = tuple(person.values())
                if values not in space_time_points:
                    space_time_points[values] = [(date, locations['to']['name'], locations['to']['gazetteer_id'])]
                else:
                    space_time_points[values] += [(date, locations['to']['name'], locations['to']['gazetteer_id'])]

    for person_index in space_time_points:
        space_time_points[person_index] = set(space_time_points[person_index])
        space_time_points[person_index] = sorted(space_time_points[person_index], key=lambda x: (x[0], x[1]))
        space_time_points[person_index] = [{'date': x[0], 'location':{'name': x[1], 'gazetteer_id': x[2]}} for x in space_time_points[person_index]]

        current_localization = []
        current_location = None
        current_from_time = None
        current_until_time = None
        for current_point in space_time_points[person_index]:
            if not _compare_locations(current_location, current_point['location']):

                if current_location is not None:
                    current_localization.append({
                        'location': current_location,
                        'from': current_from_time,
                        'to': current_until_time
                    })

                current_location = current_point['location']
                current_from_time = current_point['date']
                current_until_time = current_point['date']
            else:
                current_until_time = current_point['date']

        current_localization.append({
            'location': current_location,
            'from': current_from_time,
            'to': current_until_time
        })

        localizations[person_index] = current_localization

    for line_values in lines:
        extracted_data = _extract_persons(line_values)
        for person in extracted_data['authors']:
            values = tuple(person.values())

            if values in localizations:
                person['localization'] = localizations[values]

            if values not in persons:
                persons[values] = person

        for person in extracted_data['recipients']:
            values = tuple(person.values())

            if values in localizations:
                person['localization'] = localizations[values]

            if values not in persons:
                persons[values] = person

    with session.begin_transaction() as tx:
        for person in list(persons.values()):
            if 'localization' in person:
                previous_localization = None
                for localization in person['localization']:
                    create_statement = ''

                    values = {
                        'place_name': localization['location']['name'],
                        'gazetteer_id': localization['location']['gazetteer_id'],
                        'from': localization['from'],
                        'until': localization['to'],
                        'person': person
                    }

                    if previous_localization is not None:

                        values['prev_place_name'] = previous_localization['location']['name']
                        values['prev_gaz_id'] = previous_localization['location']['gazetteer_id']
                        values['prev_from'] = previous_localization['from']
                        values['prev_until'] = previous_localization['to']

                        create_statement += \
                            'MATCH (prev_place:Place {name: {prev_place_name}, gazetteer_id:{prev_gaz_id}}) ' \
                            'MATCH (prev_loc:Localisation {from: {prev_from}, until:{prev_until}})' \
                            '-[:HAS_PLACE]->(prev_place) ' \

                    create_statement += \
                        'MERGE (location:Place {name:{place_name}, gazetteer_id:{gazetteer_id}}) ' \
                        'MERGE (l:Localisation{from: {from}, until: {until}}) ' \
                        '-[:HAS_PLACE]->(location) ' \
                        'MERGE (p:Person{name:{person}.name, gnd_id:{person}.gnd_id}) ' \
                        'MERGE (p)-[:RESIDES]->(l) '

                    if previous_localization is not None:
                        create_statement += \
                            'MERGE (l)-[:FOLLOWS]->(prev_loc) '

                    tx.run(create_statement, values)

                    previous_localization = localization
            else:
                create_statement = \
                    'MERGE (p:Person{name:{person}.name, gnd_id:{person}.gnd_id})'

                tx.run(create_statement,
                       {
                           'person': person
                       })


def _import_letters(session, lines):
    counter = 0

    for line_values in lines:
        persons = _extract_persons(line_values)
        letter = _extract_letter(line_values)

        letter_statement = \
            'CREATE (letter:Letter{' \
            'title:{title}, quantity_desc:{desc}, page_count:{quant}, summ:{summ}, id:{id}, date:{date}})'

        link_author_statement \
            = 'MATCH (letter:Letter{id:{id}})' \
              'MATCH (person:Person {name:{name}, gnd_id:{gnd_id}})' \
              'CREATE (letter)-[:HAS_AUTHOR]->(person)'

        link_recipient_statement \
            = 'MATCH (letter:Letter{id:{id}})' \
              'MATCH (person:Person {name:{name}, gnd_id:{gnd_id}})' \
              'CREATE (letter)-[:HAS_RECIPIENT]->(person)'

        with session.begin_transaction() as tx:

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


def import_data(tsv_path, url, port, username, password, ignore_first_line):
    driver = GraphDatabase.driver('bolt://%s:%i ' % (url, port), auth=(username, password))

    with driver.session() as session, open(tsv_path, 'r') as input_file:
        lines = []
        for line in input_file:
            if ignore_first_line:
                ignore_first_line = False
                continue

            line_values = line.split('\t')
            lines.append(line_values)

        logger.info('Importing persons...')
        _import_persons(session, lines)
        logger.info('Importing letters...')
        _import_letters(session, lines)
        logger.info('Done.')

    driver.close()


if __name__ == '__main__':

    if len(sys.argv) != 6:
        logger.info('Please provide as arguments: ')

        logger.info('1) The TSV file containing metadata.')
        logger.info('2) Neo4j URL')
        logger.info('3) Neo4j port')
        logger.info('4) Neo4j username')
        logger.info('5) Neo4j user password')

        sys.exit()

    import_data(
        tsv_path=sys.argv[1],
        ignore_first_line=True,
        url=sys.argv[2],
        port=int(sys.argv[3]),
        username=sys.argv[4],
        password=sys.argv[5]
    )
