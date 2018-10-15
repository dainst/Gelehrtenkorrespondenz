import calendar
import logging
import sys
import ead_reader.places as places

from config import *
from data_structures import *
from datetime import date
from lxml import etree
from typing import Tuple, Dict
from rdflib import Graph, URIRef, Literal
from urllib.error import HTTPError

logging.basicConfig(format='%(asctime)s %(message)s')
logger: logging.Logger = logging.getLogger(__name__)
logger.level = logging.INFO

PRESUMED_PERSON_IDENTIFIER: str = '[vermutlich]'

gnd_biographical_person_data_dict: Dict[str, Tuple[date, date]] = {}
person_name_differs_from_authority_name_log: List[Tuple[str, str]] = []
person_without_gnd_authority_source_log: List[Tuple[str, str, str, str]] = []
person_gnd_id_invalid_log: List[Tuple[str, str, str, str, str]] = []
letter_origin_date_invalid_log: List[Tuple[str, str]] = []


def _extract_persons(person_xml_elements: List[etree.Element]) -> List[Person]:
    global gnd_biographical_person_data_dict
    global person_name_differs_from_authority_name_log
    global person_without_gnd_authority_source_log
    global person_gnd_id_invalid_log
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
        gnd_date_of_birth: date = None
        gnd_date_of_death: date = None

        if name != name_normal and (name, name_normal) not in person_name_differs_from_authority_name_log:
            person_name_differs_from_authority_name_log.append((name, name_normal))

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

        if auth_source != 'GND':
            log_entry: Tuple[str, str, str, str] = (name, auth_source, auth_id, name_normal)
            if log_entry not in person_without_gnd_authority_source_log:
                person_without_gnd_authority_source_log.append(log_entry)

        if auth_source == 'GND':
            try:
                gnd_date_of_birth, gnd_date_of_death = gnd_biographical_person_data_dict[auth_id]

            except KeyError:
                try:
                    _fetch_gnd_biographical_person_data(auth_id)
                    gnd_date_of_birth, gnd_date_of_death = gnd_biographical_person_data_dict[auth_id]

                except HTTPError as error:
                    logger.error(f'_fetch_gnd_biographical_data: Got {error.code} for {error.url}.')

                    if error.code == 404:
                        log_entry: Tuple[str, str, str, str, str] = (name, auth_source, auth_id, name_normal, error.url)

                        if log_entry not in person_gnd_id_invalid_log:
                            person_gnd_id_invalid_log.append(log_entry)

        person = Person(name,
                        name_presumed,
                        is_corporation,
                        auth_source=auth_source,
                        auth_id=auth_id,
                        auth_name=name_normal,
                        auth_first_name=auth_first_name,
                        auth_last_name=auth_last_name,
                        auth_birth_date=gnd_date_of_birth,
                        auth_death_date=gnd_date_of_death)
        persons.append(person)

    return persons


def _fetch_gnd_biographical_person_data(gnd_id: str) -> None:
    global gnd_biographical_person_data_dict

    url: str = f'https://d-nb.info/gnd/{gnd_id}/about/lds'
    date_of_birth_uri: str = 'http://d-nb.info/standards/elementset/gnd#dateOfBirth'
    date_of_death_uri: str = 'http://d-nb.info/standards/elementset/gnd#dateOfDeath'
    rdf_graph: Graph = Graph()
    date_of_birth: date = None
    date_of_death: date = None

    rdf_graph.load(url)
    rdf_objects: List[Literal] = list(rdf_graph.objects(predicate=URIRef(date_of_birth_uri)))

    if len(rdf_objects) == 1:
        rdf_date_of_birth: Literal = rdf_objects[0]

        try:
            date_of_birth: date = date.fromisoformat(rdf_date_of_birth)

        except ValueError as date_of_birth_error:
            logger.error(f'Invalid person date of birth: {rdf_date_of_birth} ({date_of_birth_error})')

    elif len(rdf_objects) == 0:
        logger.debug(f'Found no date of birth for GND person {gnd_id}.')

    else:
        raise Exception(f'Found more than one date of birth for GND person {gnd_id}:\n{rdf_objects}')

    rdf_objects = list(rdf_graph.objects(predicate=URIRef(date_of_death_uri)))

    if len(rdf_objects) == 1:
        rdf_date_of_death: Literal = rdf_objects[0]

        try:
            date_of_death: date = date.fromisoformat(rdf_date_of_death)

        except ValueError as date_of_death_error:
            logger.error(f'Invalid person date of death: {rdf_date_of_death} ({date_of_death_error})')

    elif len(rdf_objects) == 0:
        logger.debug(f'Found no date of death for GND person {gnd_id}.')

    else:
        raise Exception(f'Found more than one date of death for GND person {gnd_id}:\n{rdf_objects}')

    biographical_data_tuple: Tuple[date, date] = (date_of_birth, date_of_death)
    gnd_biographical_person_data_dict[gnd_id] = biographical_data_tuple


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
                    places_of_origin: List[Place],
                    place_of_reception: Place) -> Letter:
    global letter_origin_date_invalid_log

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
        except ValueError as error:
            logger.error(f"Invalid letter origin date: {origin_date} ({error}).")
            if (kalliope_id, origin_date) not in letter_origin_date_invalid_log:
                letter_origin_date_invalid_log.append((kalliope_id, origin_date))

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
        origin_places=places_of_origin,
        reception_place=place_of_reception,
        summary_paragraphs=summary_paragraph_list,
        digital_archival_objects=digital_archival_objects)


def process_ead_files(file_paths: List[str]) -> List[Letter]:
    result: List[Letter] = []

    for file_path in file_paths:
        result += process_ead_file(file_path)

    return result


def process_ead_file(ead_file: str) -> List[Letter]:
    global person_without_gnd_authority_source_log
    global person_name_differs_from_authority_name_log
    global person_gnd_id_invalid_log
    global letter_origin_date_invalid_log
    result: List[Letter] = []

    logger.info(f'Parsing input file {ead_file} ...')

    xml_parser: etree.XMLParser = etree.XMLParser()
    xml_element_tree: etree.ElementTree = etree.parse(ead_file, xml_parser)
    xml_element_ead_component_list: List[etree.Element] = xml_element_tree.xpath(f'//{DF}:c[@level="item"]',
                                                                                 namespaces=NS)

    places.place_without_gnd_authority_source_log = []
    places.place_without_gnd_gazetteer_mapping_log = []
    places.place_without_authority_coordinates_log = []
    places.place_name_differs_from_authority_name_log = []
    places.place_gnd_id_invalid_log = []
    person_without_gnd_authority_source_log = []
    person_name_differs_from_authority_name_log = []
    person_gnd_id_invalid_log = []
    letter_origin_date_invalid_log = []

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

        origin_places: List[Place] = places.extract_places_of_origin(xml_element_ead_component.xpath(
            f'./{DF}:controlaccess/{DF}:geogname[@role="Entstehungsort"]', namespaces=NS))

        recipient_place: Place = places.extract_place_of_reception(xml_element_ead_component)

        letter: Letter = _extract_letter(xml_element_ead_component,
                                         digital_archival_objects,
                                         authors,
                                         recipients,
                                         mentioned_persons,
                                         origin_places,
                                         recipient_place)

        result.append(letter)

    if len(places.place_without_gnd_authority_source_log) > 0:
        logger.info('-----')
        logger.info('Places without GND authority source (place name, authority source, authority id, authority name):')
        logger.info('-----')
        for place in sorted(places.place_without_gnd_authority_source_log):
            logger.info(f'{place}')

    if len(places.place_without_gnd_gazetteer_mapping_log) > 0:
        logger.info('-----')
        logger.info('Places without GND Gazetteer mapping (authority id, authority source):')
        logger.info('-----')
        for place_without_gnd_gazetteer_mapping in sorted(places.place_without_gnd_gazetteer_mapping_log):
            logger.info(f'{place_without_gnd_gazetteer_mapping}')

    if len(places.place_without_authority_coordinates_log) > 0:
        logger.info('-----')
        logger.info('Places without authority coordinates (GND id, Gazetteer id):')
        logger.info('-----')
        for place_without_authority_coordinates in sorted(places.place_without_authority_coordinates_log):
            logger.info(f'{place_without_authority_coordinates}')

    if len(places.place_name_differs_from_authority_name_log) > 0:
        logger.info('-----')
        logger.info('Places where the name does not match the authority place name (place name, authority name):')
        logger.info('-----')
        for (place_name, auth_place_name) in sorted(places.place_name_differs_from_authority_name_log):
            logger.info(f'{place_name} | {auth_place_name}')

    if len(places.place_gnd_id_invalid_log) > 0:
        logger.info('-----')
        logger.info('Places with GND authority id on which the GND server does not respond '
                    '(authority source, authority id, authority url):')
        logger.info('-----')
        for (auth_source, auth_id, auth_url) in sorted(places.place_gnd_id_invalid_log):
            logger.info(f'{auth_source} | {auth_id} | {auth_url}')

    if len(person_without_gnd_authority_source_log) > 0:
        logger.info('-----')
        logger.info('Persons without GND authority source '
                    '(person name, authority source, authority id, authority name):')
        logger.info('-----')
        for person_without_gnd_authority_source_log_entry in sorted(person_without_gnd_authority_source_log):
            logger.info(f'{person_without_gnd_authority_source_log_entry}')

    if len(person_name_differs_from_authority_name_log) > 0:
        logger.info('-----')
        logger.info('Persons where the name does not match the authority name (person name, authority name):')
        logger.info('-----')
        for (person_name, auth_person_name) in sorted(person_name_differs_from_authority_name_log):
            logger.info(f'{person_name} | {auth_person_name}')

    if len(person_gnd_id_invalid_log) > 0:
        logger.info('-----')
        logger.info('Persons with GND authority id on which the GND server does not respond '
                    '(person name, authority source, authority id, authority name, url):')
        logger.info('-----')
        for (name, auth_source, auth_id, auth_name, auth_url) in sorted(person_gnd_id_invalid_log):
            logger.info(f'{name} | {auth_source} | {auth_id} | {auth_name} | {auth_url}')

    if len(letter_origin_date_invalid_log) > 0:
        logger.info('-----')
        logger.info('Letters with invalid origin dates (letter id, origin_date):')
        logger.info('-----')
        for letter_origin_date_invalid_log_entry in sorted(letter_origin_date_invalid_log):
            logger.info(f'{letter_origin_date_invalid_log_entry}')

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
