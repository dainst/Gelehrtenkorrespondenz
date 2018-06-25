import logging
import sys
import re

from lxml import etree
from data_structures import *

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# See: http://lxml.de/xpathxslt.html#namespaces-and-prefixes
# and https://stackoverflow.com/questions/8053568/how-do-i-use-empty-namespaces-in-an-lxml-xpath-query

DF = 'default'

NS = {
    DF: 'urn:isbn:1-931666-22-9'
}

RECIPIENT_PLACE_PATTERN = re.compile('Empfängerort:\s(.*)')


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
    global NS
    global DF
    global RECIPIENT_PLACE_PATTERN

    result = dict()

    authors = _extract_persons(
        item.xpath(
            f'./{DF}:controlaccess/{DF}:persname[@role="Verfasser"]', namespaces=NS
        ), [])

    authors_location_node = item.xpath(
        f'./{DF}:controlaccess/{DF}:head[text()="Orte"]/following-sibling::{DF}:geogname', namespaces=NS
    )

    if len(authors_location_node) == 1:
        authors_location_label = authors_location_node[0].text
        authors_location_gnd_id = authors_location_node[0].xpath('./@authfilenumber')[0]
    else:
        authors_location_label = ''
        authors_location_gnd_id = -1

    recipients = _extract_persons(item.xpath(f'./{DF}:controlaccess/{DF}:persname[@role="Adressat"]', namespaces=NS), [])
    recipients_location_node = item.xpath(f'./{DF}:did/{DF}:note[@label="Bemerkung"]/{DF}:p', namespaces=NS)

    if len(recipients_location_node) == 1:
        match = RECIPIENT_PLACE_PATTERN.match(recipients_location_node[0].text)
        if match is not None:
            recipients_location_label = match.group(1)
        else:
            recipients_location_label = ''
    else:
        recipients_location_label = ''

    letter_date = item.xpath(f'./{DF}:did/{DF}:unitdate[@label="Entstehungsdatum"]/@normal', namespaces=NS)
    if len(letter_date) == 1:
        letter_date = letter_date[0]
    else:
        letter_date = ''

    authors_location = Location(label=authors_location_label, gnd_id=authors_location_gnd_id)
    recipients_location = Location(label=recipients_location_label, gnd_id=-1)

    for author in authors:
        result[author.id] = LocalizationPoint(location=authors_location, date=letter_date)
    for recipient in recipients:
        result[recipient.id] = LocalizationPoint(location=recipients_location, date=letter_date)

    return result


def _process_ead_item(item, localization_timespans):
    global NS
    global DF

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

    letter = LetterData(authors, recipients, date=letter_date, summary=summary, quantity_description=quantity,
                        quantity_page_count=LetterData.parse_page_count(quantity), title=title)

    return letter


def read_file(ead_file):
    global NS
    global DF

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

    localization_timespans = dict()
    for person_id in localization_points:
        localization_timespans[person_id] = \
            LocalizationTimeSpan.aggregate_localization_points_to_timespan(localization_points[person_id])

    for item in items:
        result.append(_process_ead_item(item, localization_timespans))

    logger.info('Done.')

    return result


def read_files(file_paths):
    global NS
    global DF

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

    localization_timespans = dict()

    logger.info('Aggregating localization points into timespans.')
    for person_id in localization_points:
        localization_timespans[person_id] = \
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
            result.append(_process_ead_item(item, localization_timespans))

    return result


if __name__ == '__main__':

    if len(sys.argv) != 2:
        logger.info('Please provide as arguments: ')

        logger.info('1) The EAD file containing metadata.')
        sys.exit()

    read_file(sys.argv[1])

