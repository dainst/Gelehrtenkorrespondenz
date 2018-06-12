#!/usr/env/bin python

"""Make sure you update your conf file and configuration options!
Usage:

annotateXML <file.xml>

"""

import sys
sys.path.append("../")
sys.path.append("../../iDAIPublications")

from config_reader import ProjectCofiguration
from idai_journals.nlp import DAITokenizeSent
#import pyxmi
import os
import pickle
from training import load_dictionaries
from templates import template1
from collections import namedtuple
from lxml import etree
import logging

logging.basicConfig(level=logging.INFO)

Annotation = namedtuple('Annotation', ['token', 'pos', 'lemma', 'header', 'ne'])


# Fine tune your parameters here!
conf = ProjectCofiguration("../lib/config/korr_mac.json")
outdir = os.path.join(conf.project_root, "data/TSV")
#fix
basename = '5_GerhardAnBraun1844-1856'
model_path = conf.model
sent_tokenizer_path = '/Users/fmambrini/PycharmProjects/iDAIPublications/idai_journals/lib/nltk_data_extension/tokenizers/punkt/PY3/dai_german_punkt.pickle'

path_to_preproc = conf.preprocessing_regexp

#d = {
#    "persons": "lib/dictionaries/persons.txt",
#    "places": "lib/dictionaries/places.txt"
#  }
dicts = load_dictionaries(conf.dictionaries)

with open(model_path, 'rb') as f:
    crf = pickle.load(f)


ns = {'tei': "http://www.tei-c.org/ns/1.0"}

with open(path_to_preproc, "rb") as f:
    regs = pickle.load(f)

def getLines(page_el):
    return [par for par in page_el if par.text is not None]


def deleteRepeatedLines(lines):
    half = int(len(lines) / 2)
    isRepeat = False
    if len(lines) <= 4:
        lim = 2
    else:
        lim = 3
    #check the first 3 lines (unless there are only 4 lines in a text...); add numbers if you want
    for i in range(lim):
        try:
            if lines[half+i].text == lines[i].text:
                isRepeat = True
        except IndexError:
            isRepeat = False
    return lines[:half] if isRepeat == True else lines


def preprocess_xml_page(page_el, regexps=regs):
    lines = deleteRepeatedLines(getLines(page_el))
    #lines = getLines(page_el)
    p = "\n".join([l.text for l in lines])
    for reg in regexps:
        p = reg[0].sub(reg[1], p)
    return p.replace("\n", "")
    
#with open("korrespondez_model.pickle", "rb") as f:
#    crf = pickle.load(f)

def getPages(xml):
    return xml.xpath("//tei:body/tei:div", namespaces=ns)


def add_ner_tags(x, ner_tagged_toks, span_toks):
    pass


def pos_tag_sents(tokenized_sents):
    from treetagger import TreeTagger

    tagged_sents = []
    for i, s in enumerate(tokenized_sents):
        tt = TreeTagger(language='german')
        tags = [t for t in tt.tag(s) if len(t) > 1]
        tags = [tuple(tag + ["_", ""]) for tag in tags]
        tagged_sents.append(tags)
    return tagged_sents


def crf_annotate(tagged_sents, model = crf, dictionaries=dicts, template=template1):
    from training import InstanceFeatureExtractor

    ext = InstanceFeatureExtractor(tagged_sents, dictionaries)

    X_anno = ext.extract_features(template)
    y_pred = model.predict(X_anno)
    assert len(tagged_sents) == len(y_pred), "The lists of tokens and predictions are not in sync!"
    anno = []
    for s, p in zip(tagged_sents, y_pred):
        anno_sent = []
        for tok_sent, tok_pred in zip(s, p):
            anno_sent.append(tuple(list(tok_sent[:-1]) + [tok_pred]))
        anno.append(anno_sent)
    return anno


def _setEntityId(netag):
    if netag == 'O':
        entity_tag = 'O'
    else:
        entity_tag = netag[0] + '-webanno.custom.LetterEntity_'
    return entity_tag


def toTSV(annotated_sentences, tokenized_sentences):
    assert len(annotated_sentences) == len(tokenized_sentences), "Mismatch between annotated and tokenized sentences!"
    tsv = '''# de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS | PosValue # de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma|value  # webanno.custom.Tex | LayoutElement # webanno.custom.LetterEntity | entity_id | value\n'''
    for sent_num, (anno_sent, tok_sent) in enumerate(zip(annotated_sentences, tokenized_sentences)):
        tsv = "{}#id={}\n#text={}\n".format(tsv, sent_num + 1, tok_sent.replace("\n", ' '))
        for i, t in enumerate(anno_sent):
            tok = Annotation(*t)
            entity_id = _setEntityId(tok.ne)
            tsv_line = (
            "{}-{}".format(sent_num + 1, i + 1), tok.token, tok.pos, tok.lemma, tok.header, entity_id, tok.ne, "")
            tsv = tsv + "{}\n".format("\t".join(tsv_line))
        tsv = tsv + "\n"

    return tsv


def annotate_sents(sents):
    """Writes the processed page into a XMI tree

    :param page: str: text of a page
    :return: None
    """
    tagged_sents = pos_tag_sents(sents)
    ner_tagged_sents = crf_annotate(tagged_sents)
    return ner_tagged_sents


def process_page(page):
    sents = DAITokenizeSent(page, sent_tokenizer_path)
    annotated_sents = annotate_sents(sents)
    tsv = toTSV(annotated_sents, sents)
    return tsv


def main(pages, start_num=1):
    for num, p in enumerate(pages):
        logging.info("Working with page {}".format(num+start_num))
        outname = os.path.join(outdir, basename + '_page' + "{0:0=3d}".format(int(num) + start_num) + '.tsv')
        pre = preprocess_xml_page(p)
        t = process_page(pre)
        with open(outname, 'w') as out:
            out.write(t)


if __name__ == '__main__':
    import sys

    inpath = sys.argv[1]
    #parse xml file
    x = etree.parse(inpath)
    pages = getPages(x)
    main(pages[134:135], 135)