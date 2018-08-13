import logging
import re
import urllib.error
import rdflib

from config import NS, DF
from data_structures import Place
from rdflib import URIRef
from typing import Dict, List, Tuple

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

COORDINATES_PATTERN = re.compile('Point \(\s(.*)\s(.*).*\s\).*')
RECIPIENT_PLACE_PATTERN = re.compile('Empfängerort:\s(.*)')

place_collection: Dict[str, List[Tuple[float, float]]] = dict()
unhandled_place_authority_source_log: List[Tuple[str, str, str, str]] = []
auth_name_different_from_value_log: List[Tuple[str, str]] = []


def _fetch_gnd_location_coordinates(gnd_id):
    global place_collection
    url = f'http://d-nb.info/gnd/{gnd_id}/about/lds'

    g = rdflib.Graph()
    try:
        g.load(url)
        coordinate_list = []
        for s, p, o in g.triples((None, URIRef('http://www.opengis.net/ont/geosparql#asWKT'), None)):
            match = COORDINATES_PATTERN.match(o)
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
    except urllib.error.HTTPError as e:
        logger.error(f'Got {e.code} for {url}.')
        place_collection[gnd_id] = (None, None)


def extract_place_of_origin(item):
    # TODO: Extract coordinates from other authorities
    xml_element_geoname = item.xpath(
        f'./{DF}:controlaccess/{DF}:head[text()="Orte"]/following-sibling::{DF}:geogname/.', namespaces=NS
    )

    if len(xml_element_geoname) > 0:
        place_name = xml_element_geoname[0].xpath('./text()')[0]
        place_auth_source = xml_element_geoname[0].xpath('./@source')[0]
        place_auth_id = xml_element_geoname[0].xpath('./@authfilenumber')[0]
        place_auth_name = xml_element_geoname[0].xpath('./@normal')[0]

        if '[vermutlich]' in place_name.lower():
            place_name_presumed = True
        else:
            place_name_presumed = False

        if place_name != place_auth_name:
            if (place_name, place_auth_name) not in auth_name_different_from_value_log:
                auth_name_different_from_value_log.append((place_name, place_auth_name))

        if place_auth_source != 'GND':
            coordinates = (None, None)

            try:
                log_entry = (place_name, place_auth_source, place_auth_id, place_auth_name)

                if log_entry not in unhandled_place_authority_source_log:
                    unhandled_place_authority_source_log.append(log_entry)
            except IndexError:
                pass
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
def extract_place_of_reception(item):
    recipients_place_node = item.xpath(f'./{DF}:did/{DF}:note[@label="Bemerkung"]/{DF}:p', namespaces=NS)
    place_name = None

    if len(recipients_place_node) > 0:
        match = RECIPIENT_PLACE_PATTERN.match(recipients_place_node[0].text)
        if match is not None:
            place_name = match.group(1)

    if place_name is not None:
        if '[vermutlich]' in place_name.lower():
            place_name_presumed = True
        else:
            place_name_presumed = False

        return Place(
            name=place_name,
            name_presumed=place_name_presumed,
            auth_source="",
            auth_id="",
            auth_name="",
        )
