import sys
import logging
import os

from tsv_reader import read_data as read_tsv_data
from ead_reader import read_ead_file, read_ead_files
from neo4j_writer import write_data

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':

    if len(sys.argv) != 6:
        logger.info('Please provide as arguments: ')

        logger.info('1) Directory or file containing the metadata files (TSV or EAD XML).')
        logger.info('2) Neo4j URL')
        logger.info('3) Neo4j port')
        logger.info('4) Neo4j username')
        logger.info('5) Neo4j user password')

        sys.exit()

    input_path = sys.argv[1]

    if os.path.isfile(input_path):
        [file_name, file_extension] = os.path.splitext(input_path)

        if file_extension == '.tsv':
            letter_data = read_tsv_data(tsv_path=input_path, ignore_first_line=True)
        elif file_extension == '.xml':
            letter_data = read_ead_file(ead_file=input_path)
        else:
            logger.warning(f'Not a valid file format: {input_path}')
            sys.exit()
    elif os.path.isdir(input_path):

        if not input_path.endswith('/'):
            input_path += '/'

        files_in_dir = [f for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]

        xml_files_in_dir = [f'{input_path}{f}' for f in files_in_dir if os.path.splitext(f)[1] == '.xml']

        if len(xml_files_in_dir) != 0:
            logger.debug(xml_files_in_dir)
            letter_data = read_ead_files(xml_files_in_dir)
        else:
            logger.warning(f'Not valid files found in directory: {input_path}')
            sys.exit()
    else:
        logger.warning(f'No valid files found at {input_path}.')
        sys.exit()

    write_data(letter_data, url=sys.argv[2], port=int(sys.argv[3]), username=sys.argv[4], password=sys.argv[5])

