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

COORDINATES_PATTERN: Pattern = re.compile(r'Point \(\s(.*)\s(.*).*\s\).*')
RECIPIENT_PLACE_PATTERN: Pattern = re.compile(r'Empfängerort:\s(.*)')
RECIPIENT_PLACE_GND_ID_PATTERN: Pattern = re.compile(r'(.*)\s\(GND: ([0-9a-zA-Z\-]+)\)')
PRESUMED_PLACE_IDENTIFIER: str = '[vermutlich]'

gnd_coordinates_mapping: Dict[str, Tuple[float, float]] = {}
gnd_id_to_name_mapping: Dict[str, str] = {}
gnd_to_gazetteer_mapping: Dict[str, Tuple[str, float, float]] = {}
place_without_gnd_authority_source_log: List[Tuple[str, str, str, str, str]] = []
place_without_authority_coordinates_log: List[Tuple[str, str, str]] = []
place_without_gnd_gazetteer_mapping_log: List[Tuple[str, str, str]] = []
place_gnd_id_invalid_log: List[Tuple[str, str, str, str]] = []
place_name_differs_from_authority_name_log: List[Tuple[str, str, str]] = []


def _extract_gazetteer_coordinates(kalliope_id: str, gnd_id: str, json_data: Any):
    global gnd_to_gazetteer_mapping
    global place_without_gnd_gazetteer_mapping_log
    global place_without_authority_coordinates_log
    result_total: int = json_data['total']

    if result_total == 0:
        logger.debug(f'No GND (id: {gnd_id}) to Gazetteer mapping found!')
        gnd_to_gazetteer_mapping[gnd_id] = (None, None, None)
        log_entry: Tuple[str, str, str] = (gnd_id, 'GND', kalliope_id)

        if log_entry not in place_without_gnd_gazetteer_mapping_log:
            place_without_gnd_gazetteer_mapping_log.append(log_entry)

    elif result_total > 0:
        gaz_id: str = json_data['result'][0]['gazId']

        if result_total > 1:
            logger.warning(f'Found more than one GND (id: {gnd_id}) to Gazetteer mapping! Gazetteer IDs: ')
            for result in json_data['result']:
                logger.warning(f'  {result["gazId"]}')
            logger.warning(f'Mapping to first ID: {gaz_id}.')

        if len(gaz_id) > 0:

            gaz_coordinates: List[float] = json_data['result'][0]['prefLocation']['coordinates']

            if len(gaz_coordinates) == 0:
                logger.debug(f'Found no coordinate set for Gazetteer place {gaz_id}.')
                gnd_to_gazetteer_mapping[gnd_id] = (gaz_id, None, None)
                log_entry: Tuple[str, str, str] = (gnd_id, gaz_id, kalliope_id)

                if log_entry not in place_without_authority_coordinates_log:
                    place_without_authority_coordinates_log.append(log_entry)

            elif len(gaz_coordinates) == 2:
                lng: float = gaz_coordinates[0]
                lat: float = gaz_coordinates[1]
                gnd_to_gazetteer_mapping[gnd_id] = (gaz_id, lat, lng)

            else:
                logger.error(f'Found more than one coordinate set for Gazetteer place {gaz_id}.')


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


def _fetch_gaz_location_coordinates(kalliope_id: str, gnd_id: str) -> None:
    json_data: Any = _fetch_gazetteer_location_as_json(gnd_id)
    _extract_gazetteer_coordinates(kalliope_id, gnd_id, json_data)


def _fetch_gnd_location_coordinates(kalliope_id: str, gnd_id: str) -> None:
    global gnd_coordinates_mapping
    gnd_coordinates_mapping[gnd_id] = (None, None)
    coordinate_list: List[Tuple[float, float]] = []

    url: str = f'http://d-nb.info/gnd/{gnd_id}/about/lds'
    coordinate_uri: str = 'http://www.opengis.net/ont/geosparql#asWKT'
    rdf_graph: Graph = Graph()
    rdf_graph.load(url)

    for rdf_object in rdf_graph.objects(predicate=URIRef(coordinate_uri)):
        match: Match = COORDINATES_PATTERN.match(rdf_object)

        if match is not None:
            lng: float = float(match.group(1))
            lat: float = float(match.group(2))
            coordinate_list.append((lat, lng))

    if len(coordinate_list) == 1:
        gnd_coordinates_mapping[gnd_id] = coordinate_list[0]

    elif len(coordinate_list) == 0:
        logger.debug(f'Found no coordinate set for GND place {gnd_id}.')
        log_entry: Tuple[str, str, str] = (gnd_id, None, kalliope_id)

        if log_entry not in place_without_authority_coordinates_log:
            place_without_authority_coordinates_log.append(log_entry)

    else:
        logger.error(f'Found more than one coordinate set for GND place {gnd_id}.')


def _fetch_gnd_location_name(gnd_id: str, kalliope_id: str) -> str:
    url: str = f'http://d-nb.info/gnd/{gnd_id}/about/lds'
    predicate: str = 'https://d-nb.info/standards/elementset/gnd#preferredNameForThePlaceOrGeographicName'

    rdf_graph: Graph = Graph()
    rdf_graph.load(url)

    if gnd_id in gnd_id_to_name_mapping:
        return gnd_id_to_name_mapping[gnd_id]
    else:
        name = ""
        for pref_name in rdf_graph.objects(predicate=URIRef(predicate)):
            name = pref_name
            break
        if name == "":
            logger.error(f"No name found for GND ID {gnd_id}, kalliope ID: {kalliope_id}.")
        gnd_id_to_name_mapping[gnd_id] = name
        return name


# TODO: Further refactoring needed, this method seems to have morphed far from its original purpose.
def _get_authority_data(kalliope_id: str, place_auth_source: str, gnd_id: str) -> (str, str, Tuple[float, float]):
    global place_gnd_id_invalid_log
    (gaz_id, lat, lng) = gnd_to_gazetteer_mapping[gnd_id]

    if gaz_id is not None:
        place_auth_source = 'GAZ'
        gnd_id = gaz_id
        place_auth_coordinates = (lat, lng)

    else:
        try:
            place_auth_coordinates = gnd_coordinates_mapping[gnd_id]

        except KeyError:
            try:
                _fetch_gnd_location_coordinates(kalliope_id, gnd_id)
                place_auth_coordinates = gnd_coordinates_mapping[gnd_id]

            except HTTPError as error:
                place_auth_coordinates = (None, None)
                logger.error(f'_fetch_gnd_location_coordinates: Got {error.code} for {error.url}.')

                if error.code == 404:
                    log_entry: Tuple[str, str, str, str] = (place_auth_source, gnd_id, error.url, kalliope_id)

                    if log_entry not in place_gnd_id_invalid_log:
                        place_gnd_id_invalid_log.append(log_entry)

    return place_auth_source, gnd_id, place_auth_coordinates


def extract_places_of_origin(kalliope_id, xml_elements_geoname: List[etree.Element]) -> List[Place]:
    global place_name_differs_from_authority_name_log
    global place_without_gnd_authority_source_log
    places: List[Place] = []

    for xml_element_geoname in xml_elements_geoname:
        place_name: str = xml_element_geoname.text
        place_name_presumed: bool = False
        place_auth_source: str = xml_element_geoname.get('source')
        place_auth_id: str = xml_element_geoname.get('authfilenumber')
        place_auth_name: str = xml_element_geoname.get('normal')

        if PRESUMED_PLACE_IDENTIFIER in place_name.lower():
            place_name_presumed = True

        if place_name != place_auth_name:
            if (place_name, place_auth_name) not in place_name_differs_from_authority_name_log:
                place_name_differs_from_authority_name_log.append((place_name, place_auth_name, kalliope_id))

        if place_auth_source != 'GND':
            place_auth_coordinates: Tuple[float, float] = (None, None)

            log_entry: Tuple[str, str, str, str, str] = (place_name, place_auth_source, place_auth_id, place_auth_name, kalliope_id)

            if log_entry not in place_without_gnd_authority_source_log:
                place_without_gnd_authority_source_log.append(log_entry)

        else:
            try:
                place_auth_source, place_auth_id, place_auth_coordinates = \
                    _get_authority_data(kalliope_id, place_auth_source, place_auth_id)

            except KeyError:
                _fetch_gaz_location_coordinates(kalliope_id, place_auth_id)
                place_auth_source, place_auth_id, place_auth_coordinates = \
                    _get_authority_data(kalliope_id, place_auth_source, place_auth_id)

        place: Place = Place(name=place_name,
                             name_presumed=place_name_presumed,
                             auth_source=place_auth_source,
                             auth_id=place_auth_id,
                             auth_name=place_auth_name,
                             auth_lat=place_auth_coordinates[0],
                             auth_lng=place_auth_coordinates[1])

        places.append(place)

    return places


def extract_place_of_reception(kalliope_id: str, item: etree.Element) -> Place:
    """Try to read the place of reception from XML item. If there is an
    explicit GND provided, use the ID to retrieve coordinates and authority
    name.
    :param item:
    :return: Place
    """
    recipients_place_node: List[etree.Element] = \
        item.xpath(f'./{DF}:did/{DF}:note[@label="Bemerkung"]/{DF}:p', namespaces=NS)
    place_name_presumed: bool = False

    if len(recipients_place_node) > 0:
        match: Match = RECIPIENT_PLACE_PATTERN.match(recipients_place_node[0].text)
        if match is not None:
            place_name = match.group(1)
            match_gnd: Match = RECIPIENT_PLACE_GND_ID_PATTERN.match(match.group(1))
            if match_gnd is not None:
                place_name = match_gnd.group(1)
                gnd_id = match_gnd.group(2)
                try:
                    place_auth_source, auth_id, place_auth_coordinates = \
                        _get_authority_data(kalliope_id, 'GND', gnd_id)
                except KeyError:
                    _fetch_gaz_location_coordinates(kalliope_id, gnd_id)
                    place_auth_source, auth_id, place_auth_coordinates = \
                        _get_authority_data(kalliope_id, 'GND', gnd_id)

                place_auth_name = _fetch_gnd_location_name(gnd_id, kalliope_id)

                return Place(name=place_name,
                             name_presumed=place_name_presumed,
                             auth_source=place_auth_source,
                             auth_id=gnd_id,
                             auth_name=place_auth_name,
                             auth_lat=place_auth_coordinates[0],
                             auth_lng=place_auth_coordinates[1])

            else:
                if PRESUMED_PLACE_IDENTIFIER in place_name.lower():
                    place_name_presumed = True

                return Place(
                    name=place_name,
                    name_presumed=place_name_presumed
                )
