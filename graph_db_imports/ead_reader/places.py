import logging
import re
import requests

from config import NS, DF
from data_structures import Place
from lxml import etree
from rdflib import Graph, URIRef
from typing import Any, Dict, List, Match, Pattern, Tuple
from urllib.error import HTTPError

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

COORDINATES_PATTERN: Pattern = re.compile('Point \(\s(.*)\s(.*).*\s\).*')
RECIPIENT_PLACE_PATTERN: Pattern = re.compile('Empfängerort:\s(.*)')
PRESUMED_PLACE_IDENTIFIER: str = '[vermutlich]'

gnd_place_collection: Dict[str, Tuple[float, float]] = {}
gaz_place_collection: Dict[str, Tuple[str, float, float]] = {}
unhandled_place_authority_source_log: List[Tuple[str, str, str, str]] = []
unhandled_place_authority_coordinates_absence_log: List[Tuple[str, str]] = []
unhandled_place_authority_gazetteer_mapping_log: List[Tuple[str, str]] = []
auth_name_different_from_value_log: List[Tuple[str, str]] = []


def _extract_gazetteer_coordinates(gnd_id: str, json_data: Any):
    global gaz_place_collection
    global unhandled_place_authority_gazetteer_mapping_log
    global unhandled_place_authority_coordinates_absence_log
    result_total: int = json_data['total']

    if result_total == 0:
        logger.debug(f'No GND (id: {gnd_id}) to Gazetteer mapping found!')
        gaz_place_collection[gnd_id] = (None, None, None)
        log_entry: Tuple[str, str] = (gnd_id, 'GND')

        if log_entry not in unhandled_place_authority_gazetteer_mapping_log:
            unhandled_place_authority_gazetteer_mapping_log.append(log_entry)

    elif result_total == 1:
        gaz_id: str = json_data['result'][0]['gazId']

        if len(gaz_id) > 0:

            gaz_coordinates: List[float] = json_data['result'][0]['prefLocation']['coordinates']

            if len(gaz_coordinates) == 0:
                logger.debug(f'Found no coordinate set for Gazetteer place {gaz_id}.')
                gaz_place_collection[gnd_id] = (gaz_id, None, None)
                log_entry: Tuple[str, str] = (gnd_id, gaz_id)

                if log_entry not in unhandled_place_authority_coordinates_absence_log:
                    unhandled_place_authority_coordinates_absence_log.append(log_entry)

            elif len(gaz_coordinates) == 2:
                lng: float = gaz_coordinates[0]
                lat: float = gaz_coordinates[1]
                gaz_place_collection[gnd_id] = (gaz_id, lat, lng)

            else:
                logger.error(f'Found more than one coordinate set for Gazetteer place {gaz_id}.')

    elif result_total > 1:
        logger.error(f'Found more than one GND (id: {gnd_id}) to Gazetteer mapping!')


def _fetch_gazetteer_location_as_json(gnd_id: str) -> Any:
    query: str = '{"bool":{"must":[{"bool":{"should":[{"nested":{"path":"names",' \
            '"query":{"match":{"names.language":"deu"}}}},{"match":{"prefName.language":"deu"}}]}},' \
            '{"nested":{"path":"ids","query":{"bool":{"must":[{"match":{' \
            '"ids.value":{"query": "%s","operator":"and"}}},{"match":{"ids.context":"GND-ID"}}]}}}}]}}' % gnd_id
    url: str = 'https://gazetteer.dainst.org/search.json'
    payload: Dict[str, str] = {'offset': '0',
                               'limit': '10',
                               'noPolygons': 'true',
                               'q': query,
                               # 'add': 'parents,access,history,sort',
                               'fq': '_exists_:prefLocation.coordinates',
                               'type': 'extended'}
    response: requests.Response = None
    json_data = None

    try:
        response: requests.Response = requests.get(url=url, params=payload)
        response.raise_for_status()
        json_data = response.json()

    except ValueError:
        logger.error('JSON decoding fails!\n' + response.text)

    except requests.exceptions.RequestException as exception:
        logger.error(f'Arachne service request fails!\nRequest: {exception.request}\nResponse: {exception.response}')

    return json_data


def _fetch_gaz_location_coordinates(gnd_id: str) -> None:
    json_data: Any = _fetch_gazetteer_location_as_json(gnd_id)
    _extract_gazetteer_coordinates(gnd_id, json_data)


def _fetch_gnd_location_coordinates(gnd_id: str) -> None:
    global gnd_place_collection
    gnd_place_collection[gnd_id] = (None, None)
    url = f'http://d-nb.info/gnd/{gnd_id}/about/lds'
    rdf_graph: Graph = Graph()

    try:
        rdf_graph.load(url)
        coordinate_list: List[Tuple[float, float]] = []

        for rdf_object in rdf_graph.objects(predicate=URIRef('http://www.opengis.net/ont/geosparql#asWKT')):
            match: Match = COORDINATES_PATTERN.match(rdf_object)

            if match is not None:
                lng: float = float(match.group(1))
                lat: float = float(match.group(2))
                coordinate_list.append((lat, lng))

        if len(coordinate_list) == 1:
            gnd_place_collection[gnd_id] = coordinate_list[0]

        elif len(coordinate_list) == 0:
            logger.debug(f'Found no coordinate set for GND place {gnd_id}.')
            log_entry: Tuple[str, str] = (gnd_id, None)

            if log_entry not in unhandled_place_authority_coordinates_absence_log:
                unhandled_place_authority_coordinates_absence_log.append(log_entry)

        else:
            logger.error(f'Found more than one coordinate set for GND place {gnd_id}.')

    except HTTPError as e:
        logger.error(f'Got {e.code} for {url}.')


def _determinate_authority_source(place_auth_source: str, place_auth_id: str) -> (str, str, Tuple[float, float]):
    gaz_coordinates = gaz_place_collection[place_auth_id]
    gaz_id = gaz_coordinates[0]

    if gaz_id is not None:
        place_auth_source = 'GAZ'
        place_auth_id = gaz_id
        place_auth_coordinates = (gaz_coordinates[1], gaz_coordinates[2])

    else:
        try:
            place_auth_coordinates = gnd_place_collection[place_auth_id]

        except KeyError:
            _fetch_gnd_location_coordinates(place_auth_id)
            place_auth_coordinates = gnd_place_collection[place_auth_id]

    return place_auth_source, place_auth_id, place_auth_coordinates


def extract_place_of_origin(item: etree.Element) -> Place:
    xml_element_geoname: List[etree.Element] = item.xpath(
        f'./{DF}:controlaccess/{DF}:head[text()="Orte"]/following-sibling::{DF}:geogname/.', namespaces=NS
    )

    if len(xml_element_geoname) > 0:
        place_name: str = xml_element_geoname[0].xpath('./text()')[0]
        place_name_presumed: bool = False
        place_auth_source: str = xml_element_geoname[0].xpath('./@source')[0]
        place_auth_id: str = xml_element_geoname[0].xpath('./@authfilenumber')[0]
        place_auth_name: str = xml_element_geoname[0].xpath('./@normal')[0]

        if PRESUMED_PLACE_IDENTIFIER in place_name.lower():
            place_name_presumed = True

        if place_name != place_auth_name:
            if (place_name, place_auth_name) not in auth_name_different_from_value_log:
                auth_name_different_from_value_log.append((place_name, place_auth_name))

        if place_auth_source != 'GND':
            place_auth_coordinates: Tuple[float, float] = (None, None)

            log_entry: Tuple[str, str, str, str] = (place_name, place_auth_source, place_auth_id, place_auth_name)

            if log_entry not in unhandled_place_authority_source_log:
                unhandled_place_authority_source_log.append(log_entry)

        else:

            try:
                place_auth_source, place_auth_id, place_auth_coordinates = \
                    _determinate_authority_source(place_auth_source, place_auth_id)

            except KeyError:
                _fetch_gaz_location_coordinates(place_auth_id)
                place_auth_source, place_auth_id, place_auth_coordinates = \
                    _determinate_authority_source(place_auth_source, place_auth_id)

        return Place(
            name=place_name,
            name_presumed=place_name_presumed,
            auth_source=place_auth_source,
            auth_id=place_auth_id,
            auth_name=place_auth_name,
            auth_lat=place_auth_coordinates[0],
            auth_lng=place_auth_coordinates[1]
        )


# TODO: Parse recipient places.py less naively
def extract_place_of_reception(item: etree.Element) -> Place:
    recipients_place_node: List[etree.Element] = \
        item.xpath(f'./{DF}:did/{DF}:note[@label="Bemerkung"]/{DF}:p', namespaces=NS)
    place_name: str = None
    place_name_presumed: bool = False

    if len(recipients_place_node) > 0:
        match: Match = RECIPIENT_PLACE_PATTERN.match(recipients_place_node[0].text)
        if match is not None:
            place_name = match.group(1)

    if place_name is not None:
        if PRESUMED_PLACE_IDENTIFIER in place_name.lower():
            place_name_presumed = True

        return Place(
            name=place_name,
            name_presumed=place_name_presumed
        )
