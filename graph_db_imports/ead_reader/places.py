import logging
import re

from config import NS, DF
from data_structures import Place
from lxml import etree
from rdflib import Graph, URIRef
from typing import Dict, List, Match, Pattern, Tuple
from urllib.error import HTTPError

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

COORDINATES_PATTERN: Pattern = re.compile('Point \(\s(.*)\s(.*).*\s\).*')
RECIPIENT_PLACE_PATTERN: Pattern = re.compile('Empfängerort:\s(.*)')
PRESUMED_PLACE_IDENTIFIER: str = '[vermutlich]'

place_collection: Dict[str, List[Tuple[float, float]]] = dict()
unhandled_place_authority_source_log: List[Tuple[str, str, str, str]] = []
auth_name_different_from_value_log: List[Tuple[str, str]] = []


def _fetch_gnd_location_coordinates(gnd_id: str) -> None:
    global place_collection
    url = f'http://d-nb.info/gnd/{gnd_id}/about/lds'
    rdf_graph: Graph = Graph()

    try:
        rdf_graph.load(url)
        coordinate_list: List[Tuple[float, float]] = []

        for rdf_object in rdf_graph.objects(predicate=URIRef('http://www.opengis.net/ont/geosparql#asWKT')):
            match: Match = COORDINATES_PATTERN.match(rdf_object)

            if match is not None:
                lng = float(match.group(1))
                lat = float(match.group(2))
                coordinate_list.append((lat, lng))

        if len(coordinate_list) == 1:
            place_collection[gnd_id] = coordinate_list[0]

        elif len(coordinate_list) == 0:
            logger.warning(f'Found no coordinate set for GND place {gnd_id}.')
            place_collection[gnd_id] = (None, None)
        else:
            logger.error(f'Found more than one coordinate set for GND place {gnd_id}.')
    except HTTPError as e:
        logger.error(f'Got {e.code} for {url}.')
        place_collection[gnd_id] = (None, None)


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
            coordinates: Tuple[float, float] = (None, None)

            log_entry: Tuple[str, str, str, str] = (place_name, place_auth_source, place_auth_id, place_auth_name)

            if log_entry not in unhandled_place_authority_source_log:
                unhandled_place_authority_source_log.append(log_entry)

        else:
            try:
                coordinates = place_collection[place_auth_id]
            except KeyError:
                _fetch_gnd_location_coordinates(place_auth_id)
                coordinates = place_collection[place_auth_id]

        return Place(
            name=place_name,
            name_presumed=place_name_presumed,
            auth_source=place_auth_source,
            auth_id=place_auth_id,
            auth_name=place_auth_name,
            auth_lat=coordinates[0],
            auth_lng=coordinates[1]
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
            name_presumed=place_name_presumed,
            auth_source="",
            auth_id="",
            auth_name="",
        )
