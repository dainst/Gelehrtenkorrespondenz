"""
A small script that takes care to verify (and in case, correct) some errors
that may occasionally occur in the annotation. The most egregious one is
produced when a transition is created from O to a I- tag.

Usage:
    postprocess.py [-r <regexp>] <data-folder>

Options:
    -r <reg>    regular expression for file names (regexp as in Unix paths!)
"""

from docopt import docopt
from glob import glob
import re
import os
import logging

logging.basicConfig(level=logging.INFO)

def fix_iob(lines, fname):
    for index,line in enumerate(lines[:-1]):
        #annos = [l.split("\t") for l in lines if len(l.split("\t")) > 1]
        #for i, a in enumerate(annos):
        l = line.split('\t')
        try:
            currentner = l[6]
        except IndexError:
            currentner = "O"

        reg = re.compile(r'\tI-([A-Z]{3})')

        if currentner == "O" and reg.search(lines[index+1]):
            logging.error('Line {}, token {} in {} is not correct ("O" followed by "I-")'.format(index+1, lines[index+1].split("\t")[0], fname) )
            #lines[index + 1] = reg.sub(r"\tB-\1")


if __name__ == "__main__":
    args = docopt(__doc__)
    files = os.listdir(args["<data-folder>"])
    if args["-r"]:
        reg = args["-r"]
    else:
        reg = "*.tsv"
    path = os.path.join(args["<data-folder>"], reg)
    print(path)
    files = glob(path)
    print(len(files))
    for fpath in files:
        with open(fpath) as f:
            lines = f.readlines()
        fix_iob(lines, fpath)
