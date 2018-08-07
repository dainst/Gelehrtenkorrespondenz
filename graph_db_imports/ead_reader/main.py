import calendar
import logging
import sys
import ead_reader.places as places

from config import DF, NS
from data_structures import *
from datetime import date
from lxml import etree
from typing import Tuple

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON: Tuple[str, str] = []
LETTER_DATE_VALUE_ERROR: Tuple[str, str] = []


def _extract_persons(person_nodes: List[etree.Element]) -> List[Person]:
    global AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON
    persons: List[Person] = []

    for node in person_nodes:
        name_normal: str = node.xpath('./@normal')[0]
        name_input: str = node.xpath('./text()')[0]

        if name_input != name_normal and (name_normal, name_input) not in AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON:
            AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON.append((name_normal, name_input))

        split_name = node.xpath('./@normal')[0].split(',', 1)

        if len(split_name) == 2:
            [last_name, first_name] = split_name
        else:
            last_name = ''
            first_name = ''

        gnd_id: str = node.xpath('./@authfilenumber')[0]
        name: str = node.text

        if '[vermutlich]' in name.lower():
            name_presumed = True
        else:
            name_presumed = False

        person = Person(name, name_presumed, gnd_id, gnd_first_name=first_name, gnd_last_name=last_name)
        persons.append(person)

    return persons


def _format_origin_date(origin_date_str: str, is_start_date: bool) -> str:
    iso_origin_date: str = ''
    date_str_length: int = len(origin_date_str)

    if not (date_str_length == 4 or date_str_length == 7 or date_str_length == 8):
        raise ValueError()

    elif date_str_length == 8:
        iso_origin_date = "-".join([origin_date_str[0:4], origin_date_str[4:6], origin_date_str[6:8]])

    elif date_str_length == 7 and is_start_date:
            iso_origin_date = origin_date_str + "-01"

    elif date_str_length == 7 and not is_start_date:
        year: int = int(origin_date_str[0:4])
        month: str = origin_date_str[5:7]

        if month == '01' or month == '03' or month == '05' or \
                month == '07' or month == '08' or month == '10' or month == '12':
            iso_origin_date = origin_date_str + "-31"

        elif month == '04' or month == '06' or month == '09' or month == '11':
            iso_origin_date = origin_date_str + "-30"

        elif month == '02' and calendar.isleap(year):
            iso_origin_date = origin_date_str + "-29"

        elif month == '02' and not calendar.isleap(year):
            iso_origin_date = origin_date_str + "-28"

        else:
            raise ValueError()

    elif date_str_length == 4 and is_start_date:
        iso_origin_date = origin_date_str + "-01-01"

    elif date_str_length == 4 and not is_start_date:
        iso_origin_date = origin_date_str + "-12-31"

    return iso_origin_date


def _extract_letter_origin_dates(origin_date: str) -> Tuple[date, date, bool]:
    origin_date_from: date = None
    origin_date_till: date = None
    origin_date_presumed: bool = False

    if len(origin_date) != 8 and len(origin_date) != 17:
        origin_date_presumed = True

    origin_date_list: List[str] = origin_date.split('/')
    if 1 > len(origin_date_list) > 2:
        raise ValueError()

    elif len(origin_date_list) == 2:
        origin_date_from = date.fromisoformat(_format_origin_date(origin_date_list[0], True))
        origin_date_till = date.fromisoformat(_format_origin_date(origin_date_list[1], False))

    elif len(origin_date_list) == 1:
        origin_date_from = date.fromisoformat(_format_origin_date(origin_date_list[0], True))
        origin_date_till = date.fromisoformat(_format_origin_date(origin_date_list[0], False))

    origin_dates: Tuple[date, date, bool] = (origin_date_from, origin_date_till, origin_date_presumed)

    return origin_dates


def _extract_letter(item: etree.Element,
                    authors: List[Person],
                    recipients: List[Person],
                    place_of_origin: Place,
                    place_of_reception: Place) -> Letter:
    global LETTER_DATE_VALUE_ERROR

    # obligatory elements
    xml_element_id: List[str] = item.xpath('./@id')
    xml_element_unittitle: List[etree.Element] = item.xpath(f'./{DF}:did/{DF}:unittitle', namespaces=NS)
    xml_elements_langcode: List[etree.Element] = item.xpath(f'./{DF}:did/{DF}:langmaterial/{DF}:language/@langcode', namespaces=NS)

    # optional elements
    xml_element_unitdate: List[str] = item.xpath(f'./{DF}:did/{DF}:unitdate[@label="Entstehungsdatum"]/@normal', namespaces=NS)
    xml_element_extend: List[str] = \
        item.xpath(f'./{DF}:did/{DF}:physdesc[@label="Angaben zum Material"]/{DF}:extend[@label="Umfang"]',
                   namespaces=NS)
    xml_elements_scopecontent: List[str] =\
        item.xpath(f'./{DF}:scopecontent/{DF}:head[text()="Inhaltsangabe"]/following-sibling::{DF}:p', namespaces=NS)

    # required letter attributes
    kalliope_id: str = str(xml_element_id[0])
    title: str = xml_element_unittitle[0].text

    language_code_list: List[str] = []
    for xml_element_langcode in xml_elements_langcode:
        language_code_list.append(xml_element_langcode)

    # optional letter attributes
    origin_date_from: date = None
    origin_date_till: date = None
    origin_date_presumed: bool = False
    if len(xml_element_unitdate) == 1:
        origin_date: str = xml_element_unitdate[0].strip()
        try:
            origin_dates: Tuple[date, date, bool] = _extract_letter_origin_dates(origin_date)
            origin_date_from = origin_dates[0]
            origin_date_till = origin_dates[1]
            origin_date_presumed = origin_dates[2]
        except ValueError:
            logger.info("Invalid letter origin date: %s.", origin_date)
            if (kalliope_id, origin_date) not in LETTER_DATE_VALUE_ERROR:
                LETTER_DATE_VALUE_ERROR.append((kalliope_id, origin_date))

    extent: str = None
    if len(xml_element_extend) == 1:
        extent = xml_element_extend[0].text

    summary_paragraph_list: List[str] = []
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


def process_ead_files(file_paths: List[str]) -> List[Letter]:
    result: List[Letter] = []

    for file_path in file_paths:
        result += process_ead_file(file_path)

    return result


def process_ead_file(ead_file: str) -> List[Letter]:
    global AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON
    global LETTER_DATE_VALUE_ERROR
    result: List[Letter] = []

    logger.info(f'Parsing input file {ead_file} ...')

    parser: etree.XMLParser = etree.XMLParser()
    tree: etree.ElementTree = etree.parse(ead_file, parser)
    items: List[etree.Element] = tree.xpath(f'//{DF}:c[@level="item"]', namespaces=NS)

    places.UNHANDLED_PLACE_AUTHORITY_SOURCES = []
    places.AUTH_NAME_DIFFERENT_FROM_VALUE = []
    AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON = []
    LETTER_DATE_VALUE_ERROR = []

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
            logger.info(f'{a} | {b}')

    if len(AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON) > 0:
        logger.info('-----')
        logger.info('Persons where the name given in the GND authority file differs from our input:')
        logger.info('-----')
        for (a, b) in AUTH_NAME_DIFFERENT_FROM_VALUE_PERSON:
            logger.info(f'{a} | {b}')

    if len(LETTER_DATE_VALUE_ERROR) > 0:
        logger.info('-----')
        logger.info('Letters with invalid origin dates:')
        logger.info('-----')
        for (kalliope_id, origin_date) in LETTER_DATE_VALUE_ERROR:
            logger.info(f'letter id: {kalliope_id}, origin date: {origin_date}')

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
