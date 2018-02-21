#!/usr/env/bin python

from config_reader import ProjectCofiguration
from idai_journals.nlp import DAITokenizeSent
import pyxmi
import os
import pickle
from training import load_dictionaries
from templates import template1
from collections import namedtuple

Annotation = namedtuple('Annotation', ['token', 'pos', 'lemma', 'header', 'ne'])


# Fine tune your parameters here!
conf = ProjectCofiguration("/Users/fmambrini/PycharmProjects/Gelehrtenkorrespondenz/lib/config/korr_main.json")
outdir = os.path.join(conf.project_root, "data/TSV")
basename = '4_MommsenAnBrunn'
model_path = os.path.join(conf.project_root, "lib/models/korrespondez_model_stage3.pickle")
sent_tokenizer_path = '/Users/fmambrini/PycharmProjects/iDAIPublications/idai_journals/lib/nltk_data_extension/tokenizers/punkt/PY3/dai_german_punkt.pickle'

#d = {
#    "persons": "lib/dictionaries/persons.txt",
#    "places": "lib/dictionaries/places.txt"
#  }
dicts = load_dictionaries(conf.dictionaries)

with open(model_path, 'rb') as f:
    crf = pickle.load(f)


def add_ner_tags(x, ner_tagged_toks, span_toks):
    pass


def pos_tag_sents(tokenized_sents):
    from treetagger import TreeTagger

    tagged_sents = []
    for i, s in enumerate(tokenized_sents):
        tt = TreeTagger(language='german')
        tags = tt.tag(s)
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


def main(pages):
    for num, p in enumerate(pages):
        outname = os.path.join(outdir, basename + '_page' + "{0:0=3d}".format(int(num) + 1) + '.tsv')
        t = process_page(p)
        with open(outname, 'w') as out:
            out.write(t)


if __name__ == '__main__':
    import sys

    inpath = sys.argv[1]
    with open(inpath) as f:
        txt = f.read()
    pages = txt.split("\f")
    main(pages)