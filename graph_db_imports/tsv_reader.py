import logging

from data_structures import *
from typing import Tuple


logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

            results.append(Person(name, name_presumed, gnd_id))

    return results


def _extract_place(line: List[str], index_tuple: Tuple[int, int]) -> Place:
    label = ''
    gnd_id = '-1'

    if line[index_tuple[0]] != '':
        label = line[index_tuple[0]].rstrip('.')

    if line[index_tuple[1]] != '':
        gnd_id=line[index_tuple[1]]

    return Place(label=label, gnd_id=gnd_id)


def _extract_letter_data(
        index: int,
        line:  List[str],
        authors: List[Person],
        recipients: List[Person],
        origin_place: Place,
        reception_place: Place
) -> Letter:

    return Letter(index, authors, recipients, date=line[7], title=line[4], summary=line[17],
                  quantity_description=line[8], quantity_page_count=Letter.parse_page_count(line[8]),
                  place_of_origin=origin_place, place_of_reception=reception_place)


def _process_tsv_data(lines:  List[List[str]]) -> List[Letter]:
    letter_list: List[Letter] = []

    for idx, line in enumerate(lines):
        authors: List[Person] = _extract_persons(line, index_tuple_list=[(0, 1), (2, 3)])
        recipients: List[Person] = _extract_persons(line, index_tuple_list=[(9, 10), (11, 12), (13, 14)])
        author_place: Place = _extract_place(line, index_tuple=(5, 6))
        recipient_place: Place = _extract_place(line, index_tuple=(15, 16))
        letter = _extract_letter_data(idx, line, authors, recipients, author_place, recipient_place)
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
