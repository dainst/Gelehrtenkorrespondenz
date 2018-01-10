#!/usr/bin/env python

"""
A feature extractor for chunking.
Copyright 2010,2011 Naoaki Okazaki.
"""

# Separator of field values.
separator = ' '

# Field names of the input data.
fields = 'w pos y'

# Attribute templates.
templates = (
    (('w', -2),), (('w', -1),), (('w', 0),), (('w', 1),), (('w', 2),), (('w', -1), ('w', 0)), (('w', 0), ('w', 1)),
    (('pos', -2),), (('pos', -1),), (('pos', 0),), (('pos', 1),), (('pos', 2),), (('pos', -2), ('pos', -1)),
    (('pos', -1), ('pos', 0)), (('pos', 0), ('pos', 1)), (('pos', 1), ('pos', 2)),
    (('pos', -2), ('pos', -1), ('pos', 0)), (('pos', -1), ('pos', 0), ('pos', 1)),
    (('pos', 0), ('pos', 1), ('pos', 2)),)

from crfsuite import apply_templates
#from crfsuite.crfutils import main as crfmain


def feature_extractor(X):
    # Apply attribute templates to obtain features (in fact, attributes)
    apply_templates(X, templates)
    if X:
        X[0]['F'].append('__BOS__')
        X[-1]['F'].append('__EOS__')

#if __name__ == '__main__':
#    crfmain(feature_extractor, fields=fields, sep=separator)
