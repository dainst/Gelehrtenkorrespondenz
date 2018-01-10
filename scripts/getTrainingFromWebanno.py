#!/usr/local/share/.virtualenvs/nlppy3/bin/python

"""Use this script to download and add the relevant annotated files
that are stored in Webanno. Downloaded training data will to the the
selected output directory.

Usage:
    getTrainingFromWebanno.py <config-file>
"""


import os
from pywebanno import get
from docopt import docopt
from collections import defaultdict, namedtuple, OrderedDict
import json

arguments = docopt(__doc__)
with open(arguments["<config-file>"]) as f:
    j = json.load(f)
out_dir = j["output_directory"]
auth = (j["user"], j["password"])
proj_id = j["webanno_project_id"]



def getOutName(in_fname, root_dir=out_dir):
    base = '_'.join(in_fname.split(".")[:2]) + '.iob'
    return os.path.join(root_dir, base)


def splitInLinesFile(tsv_path):
    """Functions that reads a Webanno TSV file
    and returns the list of lines
    
    >>> splitInLinesFile("example.tsv")[0]
    ['2-1', '10-13', '929', 'CARD', '929', '_', '_']
    
    >>> splitInLines("example.tsv")[-1]
    ['3-5', '84-88', '1835', 'CARD', '@card@', '*[7]', 'DATEletter[7]']
    """
    with open(tsv_path) as f:
        tsv_in = [l.strip() for l in f.readlines()]
    lines = [l.split("\t") for l in tsv_in if len(l.split("\t")) > 1]
    return lines



def splitInLines(tsv_in):
    lines = []
    for l in tsv_in.split("\n"):
        l = l.strip()
        l = l.split("\t")
        if len(l) > 1:
            lines.append(l)
    return lines


def setValue(val, l, m):
    """Set the correct value
        
    >>> mapping_ex = defaultdict(lambda : -1, {'pos' : 3, 'lemma': 4, 'ne' : 6})
    >>> setValue("pos", ['2-17', '84-88', '1835', 'CARD', '@card@', '*[7]', 'DATEletter[7]'], mapping_ex)
    'CARD'
    >>> setValue("text_layer", ['2-17', '84-88', '1835', 'CARD', '@card@', '*[7]', 'DATEletter[7]'], mapping_ex)
    '_'
    """
    #return m
    i = m[val]
    if i != -1:
        return l[i]
    else:
        return '_'


def tsv2iob(lines, colmapping=['sent-tok', 'offset', 'form', 'pos', 'lemma', 'entity_id', 'ne']):
    """
    Quick and dirty function to convert WebAnno's TSV into IOB (2 columns, tab-separated).
    >>> lines = splitInLinesFile("example.tsv")
    >>> tsv2iob(lines)[0][2]
    ['Gerhard', 'NE', 'Gerhard', '_', 'B-PERaddressee', '*']
    >>> tsv2iob(lines)[1][3:]
    [['Luglio', 'NN', '<unknown>', '_', 'B-DATEletter', '*[7]'], ['1835', 'CARD', '@card@', '_', 'I-DATEletter', '*[7]']]
    """
    from collections import defaultdict, namedtuple

    #2-16	77-83	Luglio	NN	<unknown>	*[7]	DATEletter[7]
    #2-17	84-88	1835	CARD	@card@	*[7]	DATEletter[7]
    
    def normalize_ne_tag(tag):
        """
        WebAnno's TSV format uses square brackets to represent entities
        made up of several tokens. This functions returns just the entity
        tag.
        """
        return tag.split("[")[0] if "[" in tag else tag
    
    Token  = namedtuple('Token',["sentence_n", "token_n", "offsets", "surface","lemma", "pos", "text_layer",
                                "entity_id", "ne"])
    
    mapping = defaultdict(lambda : -1)
    for i,c in enumerate(colmapping):
        mapping[c] = i
    tokens = []
    
    for line in lines:
        sentence_number = int(line[0].split("-")[0])
        token_number = int(line[0].split("-")[1])
        offsets = line[1]
        surface = line[2]
        pos = setValue('pos', line, mapping)
        ne = setValue('ne', line, mapping)
        lemma = setValue('lemma', line, mapping)
        text_layer = setValue('text_layer', line, mapping)
        entity_id = setValue('entity_id', line, mapping)
        ne = setValue('ne', line, mapping) if ne!="_" else "O"
        tokens.append(Token(sentence_n=sentence_number
                            , token_n=token_number
                           , offsets=offsets
                           , surface=surface
                           , lemma = lemma
                           , pos =pos
                           , text_layer=text_layer
                           , entity_id = entity_id
                           , ne=ne))
        
    sentences = OrderedDict()
    for n,token in enumerate(tokens):

        # if sentence not yet added, add it
        if not token.sentence_n in sentences:
                sentences[token.sentence_n] = []

        prev_token = tokens[n-1]
        
        if token.ne!="O" and prev_token.ne=="O":
            ne = "B-%s" % normalize_ne_tag(token.ne)
        
        elif token.ne!="O" and prev_token.ne !="O" and token.ne != prev_token.ne:
            ne = "B-%s" % normalize_ne_tag(token.ne)
        
        elif token.ne!="O" and prev_token.ne !="O" and token.ne == prev_token.ne:
            ne = "I-%s" % normalize_ne_tag(token.ne)
        
        elif token.ne!="O" and token.ne == prev_token.ne:
            ne = "I-%s" % normalize_ne_tag(token.ne)
        
        else:
            ne = normalize_ne_tag(token.ne)
        
        sentences[token.sentence_n].append([token.surface, token.pos, token.lemma, token.text_layer, ne, token.entity_id])
    
    # transform the dictionary of sentences into a list of lists   
    iob = [sentences[key] for key in sentences.keys()]
    return iob


def getWebAnnoDocs(stage=2):
    #docs = pywebanno.get_annotations()
    docs = get.list_documents(auth, proj_id)
    doc_ids = [d["id"] for d in docs if d["name"].split(".")[0] == str(stage)]
    return doc_ids


def main(root=out_dir):
    listdir = os.listdir(root)
    ids = getWebAnnoDocs()
    for d in ids:
        fname = d["name"]
        outname = getOutName(fname, root)
        if os.path.basename(outname) in listdir:
            print("already in outdir")
            continue
            
        #tsv = pywebanno.getAnnotation(3, d["id"], "ctsv3")
        tsv = pywebanno.getDocument(3, d["id"], "ctsv3")
        if tsv.status_code == 500:
            continue
        lines = splitInLines(tsv.text)
        #fix IOB
        try:
            iob = tsv2iob(lines)
        except ValueError:
            print(d,fname, "dot in token num")
            continue
        with open(outname, "w") as out:
            for sent in iob:
                for t in sent:
                    out.write("\t".join(t) + "\n")
                out.write("\n")


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    args = docopt.parse_argv()
    main()