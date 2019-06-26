# Gelehrtenkorrespondenz

This project holds the scripts and modules (as well as other useful materials) 
created for the DFG-funded project "Gelehrte, Ausgräber und Kunsthändler:
Die Korrespondenz des *Instituto di Corrispondenza Archeologica*
als Wissensquelle und Netzwerkindikator".

This repository contains two code independent subprojects, concerning different work packages:
1. Code used for training and testing CRF models used for annotating the project's digitized full text  (natural language processing). For further instructions see below.
2. Code used for importing Metadata (XML-RDF) exported from [Kalliope](http://kalliope.staatsbibliothek-berlin.de/de/index.html) into a  [Neo4j](https://neo4j.com) Graphdatabase. For further instructions refer to the subdirectory [graph_db_imports](graph_db_imports).

## General structure 

The main folder contains the most important scripts for the training and testing of the CRF model for entity annotation. 
If you're dying of curiosity to know what a CRF module is, you can read the documentation 
[here](doc/crf.ipynb). The relevant files are:

* [training.py](training.py): contains the main classes for feature generation, train-test splitting and model fitting; 
by using the classes documented there you should be able to replicate the operation discussed in the [notebook](doc/crf.ipynb)
* [templates.py](templates.py) : contains the template for feature generation
* [test_train.py](test_train.py) : a `pytest` file that implements a few test for the classes of `training.py`

A couple of files are also very important to read the annotations that are used in the model training:

* [korr_corpusreader.py](korr_corpusreader.py) : overrites the NLTK's [`ConllCorpusReader`](http://www.nltk.org/_modules/nltk/corpus/reader/conll.html).
This new corpus reader is more flexible and can load all the custom columns for annotation that we store in our IOB files.
* [config_reader.py](config_reader.py) : a class to load the project configuration parameters. Store them in JSON format into the [`lib/config`](lib/config) folder.



### Other Directories

* [data](data) has all the data files (except for the PDFs: they were useless and too heavy): IOB files with annotation 
(gold standards) and TEI XML files from Arachne.
* [lib](lib) stores the configurations, the dictionaries and the saved CRF models
* [scripts](scripts) : a few scripts for pre- and postprocessing
* [crfsuite](crfsuite) : a couple of useful scripts from the older python module [CRFSuite](https://github.com/chokkan/crfsuite)
 (but actually, `training.py` makes use of just a few scripts of them
* [doc](doc) is where the ipynb with the documentations and tutorials will go

## Installation

Well, at the moment it's not something that you would properly *install*... Just clone the project and put whatever file 
you need somewhere within your `$PYTHONPATH`; you'll be fine.
