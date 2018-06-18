import logging
import sys

from lxml import etree
from data_structures import *

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# See: http://lxml.de/xpathxslt.html#namespaces-and-prefixes
# and https://stackoverflow.com/questions/8053568/how-do-i-use-empty-namespaces-in-an-lxml-xpath-query
namespaces = {
    'default': 'urn:isbn:1-931666-22-9'
}


def _extract_persons(author_nodes):
    authors = []

    for node in author_nodes:
        split_name = node.xpath('./@normal')[0].split(',', 1)

        if len(split_name) == 2:
            [last_name, first_name] = split_name
        else:
            last_name = ''
            first_name = ''

        gnd_id = node.xpath('./@authfilenumber')[0]
        localizations = []

        name = node.text

        author = PersonData(name, gnd_id, localizations, first_name=first_name, last_name=last_name)

        authors.append(author)

    return authors


def _process_ead_item(item):
    global namespaces

    letter_date = item.xpath('.//default:unitdate[@label="Entstehungsdatum"]/@normal', namespaces=namespaces)

    summary = item.xpath('./default:scopecontent/default:head/following-sibling::default:p', namespaces=namespaces)
    if len(summary) == 1:
        summary = summary[0].text
    else:
        summary = ''

    quantity = item.xpath('.//default:extend[@label="Umfang"]', namespaces=namespaces)
    if len(quantity) == 1:
        quantity = quantity[0].text
    else:
        quantity = ''

    title = item.xpath('.//default:unittitle', namespaces=namespaces)[0].text

    authors = _extract_persons(item.xpath('.//default:persname[@role="Verfasser"]', namespaces=namespaces))
    recipients = _extract_persons(item.xpath('.//default:persname[@role="Adressat"]', namespaces=namespaces))

    letter = LetterData(authors, recipients, date=letter_date, summary=summary, quantity_description=quantity,
                        quantity_page_count=LetterData.parse_page_count(quantity), title=title)

    return letter


def read_ead_file(ead_file):
    result = []
    logger.info(f'Parsing input file {ead_file}.')
    parser = etree.XMLParser()

    tree = etree.parse(ead_file, parser)

    items = tree.xpath(
        '/default:ead/default:archdesc[@level="collection"]/default:dsc/default:c[@level="item"]',
        namespaces=namespaces
    )

    for item in items:
        result.append(_process_ead_item(item))

    logger.info('Done.')

    return result


if __name__ == '__main__':

    if len(sys.argv) != 2:
        logger.info('Please provide as arguments: ')

        logger.info('1) The EAD file containing metadata.')
        sys.exit()

    read_ead_file(sys.argv[1])

