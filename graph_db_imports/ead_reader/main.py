import calendar
import logging
import sys
import ead_reader.places as places

from config import DF, NS
from data_structures import *
from datetime import date
from lxml import etree
from typing import Tuple

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

person_name_different_from_auth_name_log: List[Tuple[str, str]] = []
unhandled_person_authority_source_log: List[Tuple[str, str, str, str]] = []
letter_date_value_error_log: List[Tuple[str, str]] = []


def _extract_persons(person_xml_elements: List[etree.Element]) -> List[Person]:
    global person_name_different_from_auth_name_log
    global unhandled_person_authority_source_log
    persons: List[Person] = []

    for person_xml_element in person_xml_elements:
        name: str = person_xml_element.text
        name_presumed: bool = False
        is_corporation: bool = False
        auth_source: str = person_xml_element.xpath('./@source')[0]
        auth_id: str = person_xml_element.xpath('./@authfilenumber')[0]
        name_normal: str = person_xml_element.xpath('./@normal')[0]
        auth_first_name = ''
        auth_last_name = ''

        if '[vermutlich]' in name.lower():
            name_presumed = True

        if person_xml_element.tag == '{%s}persname' % (NS[DF]):
            split_name = name_normal.split(',', 1)
            if len(split_name) == 2:
                auth_last_name = split_name[0].strip()
                auth_first_name = split_name[1].strip()
        if person_xml_element.tag == '{%s}corpname' % (NS[DF]):
            is_corporation = True
            auth_first_name = ''
            auth_last_name = name_normal

        if name != name_normal and (name, name_normal) not in person_name_different_from_auth_name_log:
            person_name_different_from_auth_name_log.append((name, name_normal))

        if auth_source != 'GND':
            log_entry: Tuple[str, str, str, str] = (name, auth_source, auth_id, name_normal)
            if log_entry not in unhandled_person_authority_source_log:
                unhandled_person_authority_source_log.append(log_entry)

        person = Person(name,
                        name_presumed,
                        is_corporation,
                        auth_source=auth_source,
                        auth_id=auth_id,
                        auth_first_name=auth_first_name,
                        auth_last_name=auth_last_name)
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
    global letter_date_value_error_log

    # obligatory elements
    xml_element_id: List[str] = item.xpath('./@id')
    xml_element_unittitle: List[etree.Element] = item.xpath(f'./{DF}:did/{DF}:unittitle', namespaces=NS)
    xml_elements_langcode: List[etree.Element] = item.xpath(f'./{DF}:did/{DF}:langmaterial/{DF}:language/@langcode',
                                                            namespaces=NS)

    # optional elements
    xml_element_unitdate: List[str] =\
        item.xpath(f'./{DF}:did/{DF}:unitdate[@label="Entstehungsdatum"]/@normal', namespaces=NS)
    xml_element_extent: List[etree.Element] = item.xpath(
        f'./{DF}:did/{DF}:physdesc[@label="Angaben zum Material"]/{DF}:extent[@label="Umfang"]', namespaces=NS)
    xml_elements_scopecontent: List[etree.Element] =\
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
            logger.error("Invalid letter origin date: %s.", origin_date)
            if (kalliope_id, origin_date) not in letter_date_value_error_log:
                letter_date_value_error_log.append((kalliope_id, origin_date))

    extent: str = None
    if len(xml_element_extent) == 1:
        extent = xml_element_extent[0].text

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
    global person_name_different_from_auth_name_log
    global letter_date_value_error_log
    result: List[Letter] = []

    logger.info(f'Parsing input file {ead_file} ...')

    parser: etree.XMLParser = etree.XMLParser()
    tree: etree.ElementTree = etree.parse(ead_file, parser)
    items: List[etree.Element] = tree.xpath(f'//{DF}:c[@level="item"]', namespaces=NS)

    places.unhandled_place_authority_source_log = []
    places.auth_name_different_from_value_log = []
    person_name_different_from_auth_name_log = []
    letter_date_value_error_log = []

    for item in items:
        authors: List[Person] = \
            _extract_persons(item.xpath(f'./{DF}:controlaccess/{DF}:persname[@role="Verfasser"] | '
                                        f'./{DF}:controlaccess/{DF}:corpname[@role="Verfasser"]', namespaces=NS))
        recipients: List[Person] = \
            _extract_persons(item.xpath(f'./{DF}:controlaccess/{DF}:persname[@role="Adressat"] | '
                                        f'./{DF}:controlaccess/{DF}:corpname[@role="Adressat"]', namespaces=NS))

        origin_place: Place = places.extract_place_of_origin(item)
        recipient_place: Place = places.extract_place_of_reception(item)

        letter: Letter = _extract_letter(item, authors, recipients, origin_place, recipient_place)

        result.append(letter)

    if len(places.unhandled_place_authority_source_log) > 0:
        logger.info('-----')
        logger.info('Unhandled place authority sources (place name, authority source, authority id, authority name):')
        logger.info('-----')
        for place in sorted(places.unhandled_place_authority_source_log):
            logger.info(f'{place}')

    if len(places.auth_name_different_from_value_log) > 0:
        logger.info('-----')
        logger.info('Places where the name given in the GND authority file differs from our input '
                    '(place name, authority name):')
        logger.info('-----')
        for (place_name, auth_place_name) in sorted(places.auth_name_different_from_value_log):
            logger.info(f'{place_name} | {auth_place_name}')

    if len(unhandled_person_authority_source_log) > 0:
        logger.info('-----')
        logger.info('Unhandled person authority sources (person name, authority source, authority id, authority name):')
        logger.info('-----')
        for unhandled_person_authority_source_log_entry in sorted(unhandled_person_authority_source_log):
            logger.info(f'{unhandled_person_authority_source_log_entry}')

    if len(person_name_different_from_auth_name_log) > 0:
        logger.info('-----')
        logger.info('Persons where the name given in the GND authority file differs from our input '
                    '(person name, authority name):')
        logger.info('-----')
        for (person_name, auth_person_name) in sorted(person_name_different_from_auth_name_log):
            logger.info(f'{person_name} | {auth_person_name}')

    if len(letter_date_value_error_log) > 0:
        logger.info('-----')
        logger.info('Letters with invalid origin dates (letter id, origin_date):')
        logger.info('-----')
        for letter_date_value_error_log_entry in sorted(letter_date_value_error_log):
            logger.info(f'{letter_date_value_error_log_entry}')

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
