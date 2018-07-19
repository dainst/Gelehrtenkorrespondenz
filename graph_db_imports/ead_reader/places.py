import logging
import re
import urllib.error
import rdflib
from rdflib import URIRef

from data_structures import Place
from config import NS, DF

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

COORDINATES_PATTERN = re.compile('Point \(\s(.*)\s(.*).*\s\).*')
RECIPIENT_PLACE_PATTERN = re.compile('Empfängerort:\s(.*)')
PLACE_COLLECTION = dict()

UNHANDLED_PLACE_AUTHORITY_SOURCES = []
AUTH_NAME_DIFFERENT_FROM_VALUE = []


def _fetch_gnd_location_coordinates(gnd_id):
    global PLACE_COLLECTION
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
            PLACE_COLLECTION[gnd_id] = coordinate_list[0]
        elif len(coordinate_list) == 0:
            logger.warning(f'Found no coordinate set for GND place {gnd_id}.')
            PLACE_COLLECTION[gnd_id] = (None, None)
        else:
            logger.error(f'Found more than one coordinate set for GND place {gnd_id}.')
    except urllib.error.HTTPError as e:
        logger.error(f'Got {e.code} for {url}.')
        PLACE_COLLECTION[gnd_id] = (None, None)


def extract_place_of_origin(item):
    # TODO: Extract coordinates from other authorities
    place_of_origin_node = item.xpath(
        f'./{DF}:controlaccess/{DF}:head[text()="Orte"]/following-sibling::{DF}:geogname[@source="GND"]/.',
        namespaces=NS
    )

    unknown_place_source_node = item.xpath(
        f'./{DF}:controlaccess/{DF}:head[text()="Orte"]/following-sibling::{DF}:geogname[@source!="GND"]/.',
        namespaces=NS
    )

    try:
        unknown_place_source = unknown_place_source_node[0].xpath('./@source')[0]
        unknown_place_source_label = unknown_place_source_node[0].xpath('./@normal')[0]
        unknown_place_source_id = unknown_place_source_node[0].xpath('./@authfilenumber')[0]

        log = (unknown_place_source, unknown_place_source_label, unknown_place_source_id)

        if log not in UNHANDLED_PLACE_AUTHORITY_SOURCES:
            UNHANDLED_PLACE_AUTHORITY_SOURCES.append(log)
    except IndexError:
        pass

    if len(place_of_origin_node) == 1:
        authors_place_label = place_of_origin_node[0].xpath('./@normal')[0]
        authors_place_text_content = place_of_origin_node[0].xpath('./text()')[0]

        if authors_place_label != authors_place_text_content:

            if (authors_place_label, authors_place_text_content) not in AUTH_NAME_DIFFERENT_FROM_VALUE:
                AUTH_NAME_DIFFERENT_FROM_VALUE.append((authors_place_label, authors_place_text_content))

        authors_place_gnd_id = place_of_origin_node[0].xpath('./@authfilenumber')[0]
    else:
        authors_place_label = ''
        authors_place_gnd_id = "-1"

    try:
        coordinates = PLACE_COLLECTION[authors_place_gnd_id]
    except KeyError:
        _fetch_gnd_location_coordinates(authors_place_gnd_id)
        coordinates = PLACE_COLLECTION[authors_place_gnd_id]

    return Place(label=authors_place_label, gnd_id=authors_place_gnd_id, lat=coordinates[0],
                 lng=coordinates[1])


# TODO: Parse recipient places.py less naively
def extract_place_of_reception(item):
    recipients_place_node = item.xpath(f'./{DF}:did/{DF}:note[@label="Bemerkung"]/{DF}:p', namespaces=NS)

    if len(recipients_place_node) == 1:
        match = RECIPIENT_PLACE_PATTERN.match(recipients_place_node[0].text)
        if match is not None:
            recipients_place_label = match.group(1)
        else:
            recipients_place_label = ''
    else:
        recipients_place_label = ''

    return Place(label=recipients_place_label, gnd_id=str(-1))
