import logging
import sys
import ead_reader.places as places

from config import DF, NS
from data_structures import *
from lxml import etree
from typing import Tuple

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


def _extract_letter_origin_dates(origin_date) -> Tuple[str, str, bool]:
    origin_date_from: str = ''
    origin_date_till: str = ''
    origin_date_presumed: bool = False

    if len(origin_date) != 8 and len(origin_date) != 17:
        origin_date_presumed = True

    origin_date_list = origin_date.split('/')
    if len(origin_date_list) > 2:
        exit(-1)
    elif len(origin_date_list) == 2:
        origin_date_from = origin_date_list[0]
        origin_date_till = origin_date_list[1]
    elif len(origin_date_list) == 1:
        origin_date_from = origin_date_list[0]
        origin_date_till = origin_date_list[0]

    origin_dates: Tuple[str, str, bool] = (origin_date_from, origin_date_till, origin_date_presumed)

    return origin_dates


def _extract_letter(item, authors, recipients, place_of_origin, place_of_reception) -> Letter:
    # required elements
    xml_element_id = item.xpath('./@id')
    xml_element_unittitle = item.xpath(f'./{DF}:did/{DF}:unittitle', namespaces=NS)
    xml_elements_langcode = item.xpath(f'./{DF}:did/{DF}:langmaterial/{DF}:language/@langcode', namespaces=NS)

    # optional elements
    xml_element_unitdate = item.xpath(f'./{DF}:did/{DF}:unitdate[@label="Entstehungsdatum"]/@normal', namespaces=NS)
    xml_element_extend = \
        item.xpath(f'./{DF}:did/{DF}:physdesc[@label="Angaben zum Material"]/{DF}:extend[@label="Umfang"]',
                   namespaces=NS)
    xml_elements_scopecontent =\
        item.xpath(f'./{DF}:scopecontent/{DF}:head[text()="Inhaltsangabe"]/following-sibling::{DF}:p', namespaces=NS)

    # required letter attributes
    kalliope_id = str(xml_element_id[0])
    title = xml_element_unittitle[0].text

    language_code_list: List[str] = []
    for xml_element_langcode in xml_elements_langcode:
        language_code_list.append(xml_element_langcode)

    # optional letter attributes
    origin_date_from = ''
    origin_date_till = ''
    origin_date_presumed = False
    if len(xml_element_unitdate) == 1:
        origin_date = xml_element_unitdate[0]
        origin_dates: Tuple[str, str, bool] = _extract_letter_origin_dates(origin_date)
        origin_date_from = origin_dates[0]
        origin_date_till = origin_dates[1]
        origin_date_presumed = origin_dates[2]

    extent = ''
    if len(xml_element_extend) == 1:
        extent = xml_element_extend[0].text

    summary_paragraph_list = []
    for p_tag in xml_elements_scopecontent:
        summary_paragraph_list.append(p_tag.text)

    return Letter(
        kalliope_id=kalliope_id,
        title=title,
        language_codes=language_code_list,
        origin_date_from=origin_date_from,
        origin_date_till=origin_date_till,
        origin_date_presumed=origin_date_presumed,
        extent=extent,
        authors=authors,
        recipients=recipients,
        origin_place=place_of_origin,
        reception_place=place_of_reception,
        summary_paragraphs=summary_paragraph_list)


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
    items = tree.xpath(f'//{DF}:c[@level="item"]', namespaces=NS)

    places.UNHANDLED_PLACE_AUTHORITY_SOURCES = []
    places.AUTH_NAME_DIFFERENT_FROM_VALUE = []
    AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON = []

    for item in items:
        # TODO: authors and recipients can be public bodies: element name `corpname` needs to be included, see ead_DE-2490_67562.xml
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
    logger.info('=====\n')

    return result


if __name__ == '__main__':

    if len(sys.argv) != 2:
        logger.info('Please provide as arguments: ')

        logger.info('1) The EAD file containing metadata.')
        sys.exit()

    process_ead_file(sys.argv[1])
