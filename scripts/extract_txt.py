#!/usr/bin/env python

import sys
sys.path.append("../")

import os
from lxml import etree
from annotateXML import getPages, preprocess_xml_page
from pathlib import Path
from glob import glob
from config_reader import ProjectCofiguration
import pickle

conf = ProjectCofiguration("../lib/config/korr_mac.json")
path_to_preproc = conf.preprocessing_regexp

with open(path_to_preproc, "rb") as f:
    regs = pickle.load(f)
    
    
files = glob("../data/TEI/originals/BOOK-*/transcription.xml")
for f in files:
    bookname = Path(f).parent.parts[-1]
    x = etree.parse(f)
    pages = getPages(x)
    txts = [preprocess_xml_page(p) for p in pages]
    with open("../data/TXT/" + bookname + '.txt', 'w') as out:
        out.write("\n\f".join(txts))