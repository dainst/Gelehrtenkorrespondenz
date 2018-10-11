import calendar
import logging
import sys
import ead_reader.places as places

from config import *
from data_structures import *
from datetime import date
from lxml import etree
from typing import Tuple, Dict
from rdflib import Graph, URIRef
from urllib.error import HTTPError

logging.basicConfig(format='%(asctime)s %(message)s')
logger: logging.Logger = logging.getLogger(__name__)
logger.level = logging.DEBUG

PRESUMED_PERSON_IDENTIFIER: str = '[vermutlich]'

gnd_biographical_data_collection: Dict[str, Tuple[date, date]] = {}
person_name_different_from_auth_name_log: List[Tuple[str, str]] = []
unhandled_person_authority_source_log: List[Tuple[str, str, str, str]] = []
letter_date_value_error_log: List[Tuple[str, str]] = []


def _extract_persons(person_xml_elements: List[etree.Element]) -> List[Person]:
    global gnd_biographical_data_collection
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
        auth_first_name: str = None
        auth_last_name: str = None
        gnd_date_of_birth: date = None     # date oder str statt float
        gnd_date_of_death: date = None

        if PRESUMED_PERSON_IDENTIFIER in name.lower():
            name_presumed = True

        if person_xml_element.tag == '{%s}persname' % (NS[DF]):
            if ',' in name_normal:
                split_name = name_normal.split(',', 1)
                auth_last_name = split_name[0].strip()
                auth_first_name = split_name[1].strip()

            else:
                auth_last_name = name_normal

        if person_xml_element.tag == '{%s}corpname' % (NS[DF]):
            is_corporation = True

        if name != name_normal and (name, name_normal) not in person_name_different_from_auth_name_log:
            person_name_different_from_auth_name_log.append((name, name_normal))

        if auth_source != 'GND':
            log_entry: Tuple[str, str, str, str] = (name, auth_source, auth_id, name_normal)
            if log_entry not in unhandled_person_authority_source_log:
                unhandled_person_authority_source_log.append(log_entry)

        if auth_source == 'GND':
            try:
                gnd_date_of_birth, gnd_date_of_death = gnd_biographical_data_collection[auth_id]
            except KeyError:
                _fetch_gnd_biographical_data(auth_id)
                gnd_date_of_birth, gnd_date_of_death = gnd_biographical_data_collection[auth_id]
                logger.debug(f'_extract_persons_: {auth_id, gnd_date_of_birth, gnd_date_of_death}')

        person = Person(name,
                        name_presumed,
                        is_corporation,
                        auth_source=auth_source,
                        auth_id=auth_id,
                        auth_name=name_normal,
                        auth_first_name=auth_first_name,
                        auth_last_name=auth_last_name,
                        date_of_birth=gnd_date_of_birth,
                        date_of_death=gnd_date_of_death)
        persons.append(person)

    return persons


def _fetch_gnd_biographical_data(gnd_auth_id: str):
    global gnd_biographical_data_collection

    url = f'https://d-nb.info/gnd/{gnd_auth_id}/about/lds'
    rdf_graph: Graph = Graph()
    gnd_date_of_birth: date = None
    gnd_date_of_death: date = None

    try:
        rdf_graph.load(url)

        rdf_objects = list(rdf_graph.objects(predicate=URIRef('http://d-nb.info/standards/elementset/gnd#dateOfBirth')))
        if len(rdf_objects) == 1:
            gnd_date_of_birth: date = date.fromisoformat(rdf_objects[0])
        elif len(rdf_objects) == 0:
            logger.debug(f'Found no date of birth for GND person {gnd_auth_id}.')
        else:
            logger.error(f'Found more than one date of birth for GND person {gnd_auth_id}:')
            logger.error(rdf_objects)

        rdf_objects = list(rdf_graph.objects(predicate=URIRef('http://d-nb.info/standards/elementset/gnd#dateOfDeath')))
        if len(rdf_objects) == 1:
            gnd_date_of_death: date = date.fromisoformat(rdf_objects[0])
        elif len(rdf_objects) == 0:
            logger.debug(f'Found no date of death for GND person {gnd_auth_id}.')
        else:
            logger.error(f'Found more than one date of death for GND person {gnd_auth_id}:')
            logger.error(rdf_objects)

    except HTTPError as e:
        logger.error(f'Got {e.code} for {url}.')

    biographical_data_tuple: Tuple[date, date] = (gnd_date_of_birth, gnd_date_of_death)

    gnd_biographical_data_collection[gnd_auth_id] = biographical_data_tuple


def _extract_digital_archival_objects(xml_element_ead_component: etree.Element) -> List[DigitalArchivalObject]:
    digital_archival_objects: List[DigitalArchivalObject] = []

    xml_element_dao_list: List[etree.Element] = \
        xml_element_ead_component.xpath(f'./{DF}:did/{DF}:dao', namespaces=NS)

    for xml_element_dao in xml_element_dao_list:
        dao_url_list: List[str] = xml_element_dao.xpath(f'./@{XL}:href', namespaces=NS)
        dao_title_list: List[str] = xml_element_dao.xpath(f'./@{XL}:title', namespaces=NS)

        if len(dao_url_list) == 1 and len(dao_title_list) == 1:
            dao_url: str = dao_url_list[0].strip()
            dao_title: str = dao_title_list[0].strip()

            if dao_title.lower() == 'digitalisat' or dao_title == 'Digitalisate':
                dao_content_type = ContentType.LETTER
            else:
                dao_content_type = ContentType.ATTACHMENT

        elif len(dao_url_list) == 1 and len(dao_title_list) < 1:
            dao_url: str = dao_url_list[0].strip()
            dao_content_type: ContentType = ContentType.UNDEFINED
            dao_title: str = ContentType.UNDEFINED.name

        else:
            raise ValueError

        digital_archival_object = DigitalArchivalObject(url=dao_url, content_type=dao_content_type, title=dao_title)
        digital_archival_objects.append(digital_archival_object)

    return digital_archival_objects


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


def _extract_letter(xml_element_ead_component: etree.Element,
                    digital_archival_objects: List[DigitalArchivalObject],
                    authors: List[Person],
                    recipients: List[Person],
                    mentioned_persons: List[Person],
                    place_of_origin: Place,
                    place_of_reception: Place) -> Letter:
    global letter_date_value_error_log

    # obligatory elements
    xml_element_id: List[str] = xml_element_ead_component.xpath('./@id')
    xml_element_unittitle: List[etree.Element] = xml_element_ead_component.xpath(f'./{DF}:did/{DF}:unittitle',
                                                                                 namespaces=NS)
    xml_elements_langcode: List[etree.Element] = xml_element_ead_component.xpath(
        f'./{DF}:did/{DF}:langmaterial/{DF}:language/@langcode', namespaces=NS)

    # optional elements
    xml_element_unitdate: List[str] = xml_element_ead_component.xpath(
        f'./{DF}:did/{DF}:unitdate[@label="Entstehungsdatum"]/@normal', namespaces=NS)
    xml_element_extent: List[etree.Element] = xml_element_ead_component.xpath(
        f'./{DF}:did/{DF}:physdesc[@label="Angaben zum Material"]/{DF}:extent[@label="Umfang"]', namespaces=NS)
    xml_elements_scopecontent: List[etree.Element] = xml_element_ead_component.xpath(
        f'./{DF}:scopecontent/{DF}:head[text()="Inhaltsangabe"]/following-sibling::{DF}:p', namespaces=NS)

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
            logger.debug("Invalid letter origin date: %s.", origin_date)
            if (kalliope_id, origin_date) not in letter_date_value_error_log:
                letter_date_value_error_log.append((kalliope_id, origin_date))

    extent: str = None
    if len(xml_element_extent) == 1:
        extent = xml_element_extent[0].text

    summary_paragraph_list: List[str] = None
    if len(xml_elements_scopecontent) > 0:
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
        mentioned_persons=mentioned_persons,
        origin_place=place_of_origin,
        reception_place=place_of_reception,
        summary_paragraphs=summary_paragraph_list,
        digital_archival_objects=digital_archival_objects)


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

    xml_parser: etree.XMLParser = etree.XMLParser()
    xml_element_tree: etree.ElementTree = etree.parse(ead_file, xml_parser)
    xml_element_ead_component_list: List[etree.Element] = xml_element_tree.xpath(f'//{DF}:c[@level="item"]',
                                                                                 namespaces=NS)

    places.unhandled_place_authority_source_log = []
    places.auth_name_different_from_value_log = []
    person_name_different_from_auth_name_log = []
    letter_date_value_error_log = []

    for xml_element_ead_component in xml_element_ead_component_list:
        digital_archival_objects: List[DigitalArchivalObject] = \
            _extract_digital_archival_objects(xml_element_ead_component)
        authors: List[Person] = _extract_persons(xml_element_ead_component.xpath(
            f'./{DF}:controlaccess/{DF}:persname[@role="Verfasser"] | '
            f'./{DF}:controlaccess/{DF}:corpname[@role="Verfasser"]', namespaces=NS))
        recipients: List[Person] = _extract_persons(xml_element_ead_component.xpath(
            f'./{DF}:controlaccess/{DF}:persname[@role="Adressat"] | '
            f'./{DF}:controlaccess/{DF}:corpname[@role="Adressat"]', namespaces=NS))
        mentioned_persons: List[Person] = _extract_persons(xml_element_ead_component.xpath(
            f'./{DF}:controlaccess/{DF}:persname[@role="Erwähnt"] | '
            f'./{DF}:controlaccess/{DF}:persname[@role="Behandelt"] | '
            f'./{DF}:controlaccess/{DF}:persname[@role="Dokumentiert"]', namespaces=NS))

        origin_place: Place = places.extract_place_of_origin(xml_element_ead_component)
        recipient_place: Place = places.extract_place_of_reception(xml_element_ead_component)

        letter: Letter = _extract_letter(xml_element_ead_component,
                                         digital_archival_objects,
                                         authors,
                                         recipients,
                                         mentioned_persons,
                                         origin_place,
                                         recipient_place)

        result.append(letter)

    if len(places.unhandled_place_authority_source_log) > 0:
        logger.info('-----')
        logger.info('Unhandled place authority sources (place name, authority source, authority id, authority name):')
        logger.info('-----')
        for place in sorted(places.unhandled_place_authority_source_log):
            logger.info(f'{place}')

    if len(places.unhandled_place_authority_gazetteer_mapping_log) > 0:
        logger.info('-----')
        logger.info('Unhandled place authority gazetteer mappings (authority id, authority source):')
        logger.info('-----')
        for place_authority_gazetteer_mapping in sorted(places.unhandled_place_authority_gazetteer_mapping_log):
            logger.info(f'{place_authority_gazetteer_mapping}')

    if len(places.unhandled_place_authority_coordinates_absence_log) > 0:
        logger.info('-----')
        logger.info('Unhandled place authority coordinates absence (GND Id, Gazetteer Id):')
        logger.info('-----')
        for place_authority_coordinates_absence in sorted(places.unhandled_place_authority_coordinates_absence_log):
            logger.info(f'{place_authority_coordinates_absence}')

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
