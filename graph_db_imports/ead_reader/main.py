import logging
import sys
import ead_reader.places as places

from config import DF, NS
from data_structures import *
from lxml import etree

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON = []


def _extract_persons(person_nodes) -> List[Person]:
    global AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON
    persons: List[Person] = []

    for node in person_nodes:
        name_normal = node.xpath('./@normal')[0]
        name_input = node.xpath('./text()')[0]

        if name_input != name_normal and (name_normal, name_input) not in AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON:
            AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON.append((name_normal, name_input))

        split_name = node.xpath('./@normal')[0].split(',', 1)

        if len(split_name) == 2:
            [last_name, first_name] = split_name
        else:
            last_name = ''
            first_name = ''

        gnd_id = node.xpath('./@authfilenumber')[0]
        name = node.text

        if '[vermutlich]' in name.lower():
            name_presumed = True
        else:
            name_presumed = False

        person = Person(name, name_presumed, gnd_id, gnd_first_name=first_name, gnd_last_name=last_name)
        persons.append(person)

    return persons


def _extract_letter(item, authors, recipients, place_of_origin, place_of_reception) -> Letter:
    letter_id = item.xpath(f'./@id')
    letter_date = item.xpath(f'./{DF}:did/{DF}:unitdate[@label="Entstehungsdatum"]/@normal', namespaces=NS)

    if len(letter_date) == 1:
        letter_date = letter_date[0]
    else:
        letter_date = ''

    summary = item.xpath(f'./{DF}:scopecontent/{DF}:head[text()="Inhaltsangabe"]/following-sibling::{DF}:p',
                         namespaces=NS)

    if len(summary) == 1:
        summary = summary[0].text
    else:
        summary = ''

    quantity = item.xpath(f'./{DF}:did/{DF}:physdesc[@label="Angaben zum Material"]/{DF}:extend[@label="Umfang"]',
                          namespaces=NS)

    if len(quantity) == 1:
        quantity = quantity[0].text
    else:
        quantity = ''

    title = item.xpath(f'./{DF}:did/{DF}:unittitle', namespaces=NS)[0].text

    return Letter(letter_id, authors, recipients, date=letter_date, summary=summary, title=title,
                  quantity_description=quantity, quantity_page_count=Letter.parse_page_count(quantity),
                  place_of_origin=place_of_origin, place_of_reception=place_of_reception)


def enhance_data(letter_list: List[Letter]) -> List[Letter]:

    return letter_list


def process_ead_files(file_paths) -> List[Letter]:
    result: List[Letter] = []

    for file_path in file_paths:
        result += process_ead_file(file_path)

    return result


def process_ead_file(ead_file) -> List[Letter]:
    global AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON
    result: List[Letter] = []

    logger.info(f'Parsing input file {ead_file} ...')
    parser = etree.XMLParser()

    tree = etree.parse(ead_file, parser)

    items = tree.xpath(
        f'//{DF}:c[@level="item"]',
        namespaces=NS
    )

    places.UNHANDLED_PLACE_AUTHORITY_SOURCES = []
    places.AUTH_NAME_DIFFERENT_FROM_VALUE = []
    AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON = []

    for item in items:
        authors: List[Person] = \
            _extract_persons(item.xpath(f'./{DF}:controlaccess/{DF}:persname[@role="Verfasser"]', namespaces=NS))
        recipients: List[Person] = \
            _extract_persons(item.xpath(f'./{DF}:controlaccess/{DF}:persname[@role="Adressat"]', namespaces=NS))

        origin_place: Place = places.extract_place_of_origin(item)
        recipient_place: Place = places.extract_place_of_reception(item)

        letter: Letter = _extract_letter(item, authors, recipients, origin_place, recipient_place)

        result.append(letter)

    if len(places.UNHANDLED_PLACE_AUTHORITY_SOURCES) > 0:
        logger.info('-----')
        logger.info('Unhandled place authority sources:')
        logger.info('-----')
        for place in places.UNHANDLED_PLACE_AUTHORITY_SOURCES:
            logger.info(f'{place}')

    if len(places.AUTH_NAME_DIFFERENT_FROM_VALUE) > 0:
        logger.info('-----')
        logger.info('Places where the name given in the GND authority file differs from our input:')
        logger.info('-----')
        for (a, b) in places.AUTH_NAME_DIFFERENT_FROM_VALUE:
            logger.info(f'{a},{b}')

    if len(AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON) > 0:
        logger.info('-----')
        logger.info('Persons where the name given in the GND authority file differs from our input:')
        logger.info('-----')
        for (a, b) in AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON:
            logger.info(f'{a},{b}')

    logger.info('=====')
    logger.info('Parsing done.')
    logger.info('=====')

    return result


if __name__ == '__main__':

    if len(sys.argv) != 2:
        logger.info('Please provide as arguments: ')

        logger.info('1) The EAD file containing metadata.')
        sys.exit()

    process_ead_file(sys.argv[1])
