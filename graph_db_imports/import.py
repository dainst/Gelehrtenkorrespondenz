import sys
import logging
import os

from tsv_reader import read_data as read_tsv_data
from ead_reader import read_ead_file
from neo4j_writer import write_data

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':

    if len(sys.argv) != 6:
        logger.info('Please provide as arguments: ')

        logger.info('1) The TSV file containing metadata.')
        logger.info('2) Neo4j URL')
        logger.info('3) Neo4j port')
        logger.info('4) Neo4j username')
        logger.info('5) Neo4j user password')

        sys.exit()

    [file_name, file_extension] = os.path.splitext(sys.argv[1])

    if file_extension == '.tsv':
        letter_data = read_tsv_data(tsv_path=sys.argv[1], ignore_first_line=True)
    elif file_extension == '.xml':
        letter_data = read_ead_file(ead_file=sys.argv[1])
    else:
        logger.warning(f'Not a valid file format: {sys.argv[1]}')
        sys.exit()

    write_data(letter_data, url=sys.argv[2], port=int(sys.argv[3]), username=sys.argv[4], password=sys.argv[5])

