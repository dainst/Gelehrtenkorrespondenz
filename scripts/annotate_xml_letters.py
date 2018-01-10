#!/usr/local/share/.virtualenvs/nlppy3/bin/python

'''This script takes a series of xml corresponding to a volume of letter
analyzed in the DFG Gelehrten Korrespondenz and annotate everything using
a CRF module. It then takes care of producing and updating everything into
a Webanno project.
All the settings are defined in the first lines. Later we'll decide if we want
to turn some of them into arguments for the program.

Usage:
    annotate_xml_letters.py <config-file>
'''

from lxml import etree
#from idai_journals.publications import DAITokenizeSent
#from idai_journals.nlp import tagDAI
#from idai_journals.utils import reg_tok
from collections import namedtuple
import crf_models
import pickle
import os
import re
import sys
import logging
import json
from docopt import docopt


args = docopt("__doc__")

with open(args["<config-file>"]) as f:
    j = json.load(f)

path_to_preproc = j["preprocessing_regexp"]
path_to_mod = j["model_path"]
webanno_project_id = j["webanno_project_id"]
xml_root = j["dir_xml"]
sent_tokenizer = j["sentence_tokenizer"]
dics = j["dictionaries"]
auth = (j["user"], j["password"])


Annotation = namedtuple('Annotation', ['token', 'pos', 'lemma', 'header', 'ne'])
ns = {'tei': "http://www.tei-c.org/ns/1.0"}

with open(path_to_preproc, "rb") as f:
    regs = pickle.load(f)

with open(path_to_mod, "rb") as f:
    crf = pickle.load(f)

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
        if lines[half+i].text == lines[i].text:
            isRepeat = True
    return lines[:half] if isRepeat == True else lines


def processPage(page_el, regexps=regs):
    lines = deleteRepeatedLines(getLines(page_el))
    p = "\n".join([l.text for l in lines])
    for reg in regexps:
        p = reg[0].sub(reg[1], p)
    return p.replace("\n", "")
    
#with open("korrespondez_model.pickle", "rb") as f:
#    crf = pickle.load(f)

def getPages(xml):
    return xml.xpath("//tei:body/tei:div", namespaces=ns)


def tokenizeSents(page_txt, sent_tok=sent_tokenizer):
    return DAITokenizeSent(page_txt, sent_tok)


def tagPage(tokenized_sents):
    from treetagger import TreeTagger
    
    tagged_sents = []
    for i,s in enumerate(tokenized_sents):
        tt = TreeTagger(language='german')
        tags = tt.tag(s)
        tags = [tuple(tag + ["_", ""]) for tag in tags]
        tagged_sents.append(tags)
    return tagged_sents


def annotateSents(tagged_sents, model=crf, dictionaries=dics):
    X_anno = [crf_models.sent2features(s, i, dics) for i,s in enumerate(tagged_sents)]
    y_pred = crf.predict(X_anno)
    assert len(tagged_sents) == len(y_pred), "The lists of tokens and predictions are not in sync!"
    anno = []
    for s,p in zip(tagged_sents, y_pred):
        anno_sent = []
        for tok_sent, tok_pred in zip(s,p):
            anno_sent.append(tuple(list(tok_sent[:-1]) + [tok_pred] ))
        anno.append(anno_sent)
    return anno


def _setEntityId(netag):
    if netag == 'O':
        entity_tag = 'O'
    else:
        entity_tag = netag[0] + '-webanno.custom.LetterEntity_'
    return entity_tag


def sendToWebanno(tsv, filename, project_id = webanno_project_id, authentication=auth):
    from pywebanno import postDocument
    import io
    
    stream = io.StringIO(tsv)
    r = postDocument(webanno_project_id, stream, filename, authentication=authentication, format="tsv")
    return r
    

def toTSV(annotated_sentences, tokenized_sentences):
    assert len(annotated_sentences) == len(tokenized_sentences), "Mismatch between annotated and tokenized sentences!"
    tsv = '''# de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS | PosValue # de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Lemma|value  # webanno.custom.Tex | LayoutElement # webanno.custom.LetterEntity | entity_id | value\n'''
    for sent_num,(anno_sent, tok_sent) in enumerate(zip(annotated_sentences, tokenized_sentences)):
        tsv = "{}#id={}\n#text={}\n".format(tsv, sent_num + 1, tok_sent)
        for i,t in enumerate(anno_sent):
            tok = Annotation(*t)
            entity_id = _setEntityId(tok.ne)
            tsv_line = ("{}-{}".format(sent_num + 1, i + 1), tok.token, tok.pos, tok.lemma, tok.header, entity_id, tok.ne, "")
            tsv = tsv + "{}\n".format("\t".join(tsv_line))
        tsv = tsv + "\n"
        
    return tsv


def processPages(fpath):
    basename = "tsv/" + os.path.splitext(os.path.basename(fpath))[0]
    x = etree.parse(fpath)
    pages = getPages(x)
    for i, page in enumerate(pages):
        outname = basename + '_page' + "{0:0=3d}".format(i + 1) + '.tsv'
        print(outname)
        if os.path.isfile(outname):
            continue
        proc_page = processPage(page)
        tok_sents = tokenizeSents(proc_page)
        tagged_sents = tagPage(tok_sents)
        annotated_sents = annotateSents(tagged_sents)
        tsv = toTSV(annotated_sents, tok_sents)
        with open(outname, 'w') as out:
            out.write(tsv)
        #r = sendToWebanno(tsv, outname)
        #if r.status_code != requests.codes.ok:
        #    log.error("Your document was not posted: Error {}".format(r.status_code))

def _test(fpath, page_num):
    basename = os.path.splitext(os.path.basename(fpath))[0]
    outname = basename + '_page' + "{0:0=3d}".format(int(page_num) + 1) + '.tsv'
    x = etree.parse(fpath)
    pages = getPages(x)
    page = pages[int(page_num)]
    proc_page = processPage(page)
    logging.debug("preprocessing done!")
    tok_sents = tokenizeSents(proc_page)
    tagged_sents = tagPage(tok_sents)
    logging.debug("tagging done!")
    annotated_sents = annotateSents(tagged_sents)
    logging.debug("annotation done!")
    tsv = toTSV(annotated_sents, tok_sents)
    with open(outname, 'w') as out:
        out.write(tsv)
    #r = sendToWebanno(tsv, outname)
    #if r.status_code == 201:
    #    logging.debug("Your document was posted!")
    #else:
    #    logging.error("Your document was not posted: Error {}".format(r.status_code))

if __name__ == "__main__":
    #_test("/home/nlp-data/gelehrtekorrespondenz/tei/Brunn1858.xml", int(sys.argv[1]))
    fpath  = os.path.join(xml_root, sys.argv[1])
    processPages(fpath)





























