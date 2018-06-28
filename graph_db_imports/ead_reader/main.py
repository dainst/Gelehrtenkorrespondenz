import logging
import sys
import re
import urllib.error
import rdflib
from rdflib import URIRef
from lxml import etree

import ead_reader.places as places
from data_structures import *
from config import DF, NS

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _extract_persons(person_nodes, localization_timespans):
    persons = []

    for node in person_nodes:
        split_name = node.xpath('./@normal')[0].split(',', 1)

        if len(split_name) == 2:
            [last_name, first_name] = split_name
        else:
            last_name = ''
            first_name = ''

        gnd_id = node.xpath('./@authfilenumber')[0]
        name = node.text

        if gnd_id in localization_timespans:
            localizations = localization_timespans[gnd_id]
        else:
            localizations = []

        person = PersonData(name, gnd_id, localizations, first_name=first_name, last_name=last_name)

        persons.append(person)

    return persons


def _extract_localization_points(item):

    result = dict()

    authors = _extract_persons(
        item.xpath(
            f'./{DF}:controlaccess/{DF}:persname[@role="Verfasser"]', namespaces=NS
        ), [])

    recipients = _extract_persons(
        item.xpath(f'./{DF}:controlaccess/{DF}:persname[@role="Adressat"]', namespaces=NS), [])

    letter_date = item.xpath(f'./{DF}:did/{DF}:unitdate[@label="Entstehungsdatum"]/@normal', namespaces=NS)
    if len(letter_date) == 1:
        letter_date = letter_date[0]
    else:
        letter_date = ''

    authors_place = places.extract_place_of_origin(item)
    recipients_place = places.extract_place_of_reception(item)

    for author in authors:
        result[author.id] = LocalizationPoint(place=authors_place, date=letter_date)

    for recipient in recipients:
        result[recipient.id] = LocalizationPoint(place=recipients_place, date=letter_date)

    return result


def _process_ead_item(item, localization_timespans):

    letter_id = item.xpath(
        f'./@id'
    )

    letter_date = item.xpath(
        f'./{DF}:did/{DF}:unitdate[@label="Entstehungsdatum"]/@normal', namespaces=NS
    )
    if len(letter_date) == 1:
        letter_date = letter_date[0]
    else:
        letter_date = ''

    summary = item.xpath(
        f'./{DF}:scopecontent/{DF}:head[text()="Inhaltsangabe"]/following-sibling::{DF}:p', namespaces=NS
    )
    if len(summary) == 1:
        summary = summary[0].text
    else:
        summary = ''

    quantity = item.xpath(f'./{DF}:did/{DF}:physdesc[@label="Angaben zum Material"]/{DF}:extend[@label="Umfang"]', namespaces=NS)
    if len(quantity) == 1:
        quantity = quantity[0].text
    else:
        quantity = ''

    title = item.xpath(f'./{DF}:did/{DF}:unittitle', namespaces=NS)[0].text

    authors = _extract_persons(
        item.xpath(f'./{DF}:controlaccess/{DF}:persname[@role="Verfasser"]', namespaces=NS), localization_timespans)
    recipients = _extract_persons(
        item.xpath(f'./{DF}:controlaccess/{DF}:persname[@role="Adressat"]', namespaces=NS), localization_timespans)

    place_of_origin = places.extract_place_of_origin(item)
    place_of_reception = places.extract_place_of_reception(item)

    letter = LetterData(letter_id, authors, recipients, date=letter_date, summary=summary, title=title,
                        quantity_description=quantity, quantity_page_count=LetterData.parse_page_count(quantity),
                        place_of_origin=place_of_origin, place_of_reception=place_of_reception)

    return letter


def read_file(ead_file):

    result = []
    logger.info(f'Parsing input file {ead_file}.')
    parser = etree.XMLParser()

    tree = etree.parse(ead_file, parser)

    items = tree.xpath(
        f'//{DF}:c[@level="item"]',
        namespaces=NS
    )

    localization_points = dict()

    for item in items:
        points = _extract_localization_points(item)
        for person_id in points:
            if person_id in localization_points:
                localization_points[person_id].append(points[person_id])
            else:
                localization_points[person_id] = [points[person_id]]

    logger.info('Unhandled place authority sources:')
    logger.info('---')
    for place in places.UNHANDLED_PLACE_AUTHORITY_SOURCES:
        logger.info(f'{place}')
    logger.info('---')

    logger.info('Places where the name given in the GND authority file differs from our input:')
    logger.info('---')
    for (a, b) in places.AUTH_NAME_DIFFERENT_FROM_VALUE:
        logger.info(f'{a},{b}')
    logger.info('---')

    localization_time_spans = dict()
    for person_id in localization_points:
        localization_time_spans[person_id] = \
            LocalizationTimeSpan.aggregate_localization_points_to_timespan(localization_points[person_id])

    for item in items:
        result.append(_process_ead_item(item, localization_time_spans))

    logger.info('Done.')

    return result


def read_files(file_paths):

    result = []

    localization_points = dict()

    logger.info(f'Collecting localization points.')
    for file_path in file_paths:
        logger.info(f'File: {file_path}.')
        parser = etree.XMLParser()
        tree = etree.parse(file_path, parser)
        items = tree.xpath(
            f'//{DF}:c[@level="item"]',
            namespaces=NS
        )

        for item in items:
            points = _extract_localization_points(item)
            for person_id in points:
                if person_id in localization_points:
                    localization_points[person_id].append(points[person_id])
                else:
                    localization_points[person_id] = [points[person_id]]

    logger.info('Unhandled place authority sources:')
    for place in places.UNHANDLED_PLACE_AUTHORITY_SOURCES:
        logger.info(f'{place}')

    logger.info('Places where the name given in the GND authority file differs from our input:')
    for (a, b) in places.AUTH_NAME_DIFFERENT_FROM_VALUE:
        logger.info(f'{a},{b}')

    localization_time_spans = dict()

    logger.info('Aggregating localization points into timespans.')
    for person_id in localization_points:
        localization_time_spans[person_id] = \
            LocalizationTimeSpan.aggregate_localization_points_to_timespan(localization_points[person_id])

    for file_path in file_paths:
        logger.info(f'Parsing letter data for input file {file_path}.')
        parser = etree.XMLParser()
        tree = etree.parse(file_path, parser)

        items = tree.xpath(
            f'//{DF}:c[@level="item"]',
            namespaces=NS
        )

        for item in items:
            result.append(_process_ead_item(item, localization_time_spans))

    return result


if __name__ == '__main__':

    if len(sys.argv) != 2:
        logger.info('Please provide as arguments: ')

        logger.info('1) The EAD file containing metadata.')
        sys.exit()

    read_file(sys.argv[1])

