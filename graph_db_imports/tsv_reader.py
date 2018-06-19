import logging
import re

from data_structures import *

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DATE_PATTERN = re.compile('\d{4}-\d{2}-\d{2}')


def _create_localization_points(data_rows):
    localization_points = dict()
    for line_values in data_rows:

        date = _extract_date(line_values)

        authors = _extract_authors(line_values, [])
        author_location = _extract_author_location(line_values)

        recipients = _extract_recipients(line_values, [])
        recipient_location = _extract_recipient_location(line_values)

        if author_location is not None:
            for author in authors:
                new_point = LocalizationPoint(author_location, date)
                if author.id not in localization_points:
                    localization_points[author.id] = [new_point]
                else:
                    localization_points[author.id] += [new_point]

        if recipient_location is not None:
            for recipient in recipients:
                new_point = LocalizationPoint(recipient_location, date)
                if recipient.id not in localization_points:
                    localization_points[recipient.id] = [new_point]
                else:
                    localization_points[recipient.id] += [new_point]

    return localization_points


def _extract_date(line_values):
    match = DATE_PATTERN.match(line_values[7])
    if match is not None:
        return match.group(0)
    else:
        return ''


def _extract_authors(line_values, localizations):
    indices = [(0, 1), (2, 3)]
    temp = [PersonData(line_values[i].rstrip(','), line_values[j], []) for (i, j) in indices if line_values[i] != '']
    results = []

    for person in temp:
        if person.id in localizations:
            person.localizations = localizations[person.id]
        results.append(person)

    return results


def _extract_recipients(line_values, localizations):
    indices = [(9, 10), (11, 12), (13, 14)]
    temp = [PersonData(line_values[i].rstrip(','), line_values[j], []) for (i, j) in indices if line_values[i] != '']
    results = []

    for person in temp:
        if person.id in localizations:
            person.localizations = localizations[person.id]
        results.append(person)

    return results


def _extract_author_location(line_values):
    if line_values[5] != '' or line_values[6] != '':
        return Location(line_values[5].rstrip('.'), line_values[6])
    else:
        return None


def _extract_recipient_location(line_values):
    if line_values[15] != '' or line_values[16]:
        return Location(line_values[15].rstrip('.'), line_values[16])
    else:
        return None


def _extract_letter_data(line_values, localizations):

    authors = _extract_authors(line_values, localizations)
    recipients = _extract_recipients(line_values, localizations)

    result = LetterData(authors, recipients, date=line_values[7], title=line_values[4], summary=line_values[17],
                        quantity_description=line_values[8],
                        quantity_page_count=LetterData.parse_page_count(line_values[8]))

    return result


def read_data(tsv_path, ignore_first_line):
    result = []
    logger.info(f'Parsing input file {tsv_path}.')
    with open(tsv_path, 'r') as input_file:
        lines = []
        for line in input_file:
            if ignore_first_line:
                ignore_first_line = False
                continue

            line_values = line.split('\t')
            lines.append(line_values)

        logger.info('Aggregating localization timespans...')
        localization_points = _create_localization_points(lines)
        localization_timespans = dict()
        for person_id in localization_points:
            localization_timespans[person_id] = \
                LocalizationTimeSpan.aggregate_localization_points_to_timespan(localization_points[person_id])

        logger.info('Parsing letter data...')
        for line in lines:
            letter_data = _extract_letter_data(line, localization_timespans)
            result.append(letter_data)

    logger.info('Done.')

    return result
