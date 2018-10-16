import logging
import re

from data_structures import *
from datetime import date
from typing import Tuple


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DATE_PATTERN = re.compile('\d{4}-\d{2}-\d{2}')


def _extract_date(line_values):
    match = DATE_PATTERN.match(line_values[7])
    if match is not None:
        return match.group(0)
    else:
        return ''


def _extract_persons(line: List[str], index_tuple_list: List[Tuple[int, int]]) -> List[Person]:
    results: List[Person] = []

    for (i, j) in index_tuple_list:
        if line[i] != '':
            name = line[i].rstrip(',')
            name_presumed = False
            gnd_id = line[j]

            results.append(Person(name=name,
                                  name_presumed=name_presumed,
                                  is_corporation=False,
                                  auth_source='GND',
                                  auth_id=gnd_id))

    return results


def _extract_place(line: List[str], index_tuple: Tuple[int, int]) -> Place:
    name = ''
    name_presumed = False
    auth_source = ''
    auth_id = ''

    if line[index_tuple[0]] != '':
        name = line[index_tuple[0]].rstrip('.')
        if '[vermutlich]' in name.lower():
            name_presumed = True

    if line[index_tuple[1]] != '':
        auth_source = 'GND'
        auth_id = line[index_tuple[1]]

    return Place(name=name, name_presumed=name_presumed, auth_source=auth_source, auth_id=auth_id, auth_name='')


def _extract_letter_data(
        index: int,
        line:  List[str],
        authors: List[Person],
        recipients: List[Person],
        origin_places: List[Place],
        reception_place: Place
) -> Letter:

    origin_date_str: str = line[7]

    try:
        origin_date: date = date.fromisoformat(origin_date_str)
    except ValueError:
        origin_date = None

    return Letter(kalliope_id=str(index),
                  title=line[4],
                  language_codes=[],
                  origin_date_from=origin_date,
                  origin_date_till=origin_date,
                  extent=line[8],
                  authors=authors,
                  recipients=recipients,
                  origin_places=origin_places,
                  reception_place=reception_place,
                  summary_paragraphs=[line[17]])


def _process_tsv_data(lines:  List[List[str]]) -> List[Letter]:
    letter_list: List[Letter] = []

    for idx, line in enumerate(lines):
        authors: List[Person] = _extract_persons(line, index_tuple_list=[(0, 1), (2, 3)])
        recipients: List[Person] = _extract_persons(line, index_tuple_list=[(9, 10), (11, 12), (13, 14)])
        author_place: Place = _extract_place(line, index_tuple=(5, 6))
        recipient_place: Place = _extract_place(line, index_tuple=(15, 16))
        letter = _extract_letter_data(idx, line, authors, recipients, [author_place], recipient_place)
        letter_list.append(letter)

    return letter_list


def read_data(tsv_path: str, ignore_first_line: bool) -> List[Letter]:

    logger.info(f'Parsing input file {tsv_path}.')

    with open(tsv_path, 'r') as input_file:
        lines: List[List[str]] = []
        for line in input_file:
            if ignore_first_line:
                ignore_first_line = False
                continue

            line_values = line.split('\t')
            lines.append(line_values)

        logger.info('Processing tsv data...')
        result = _process_tsv_data(lines)
        logger.info('Processing done.')

    logger.info('Parsing done.')

    return result
