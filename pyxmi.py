import idai_journals
import pywebanno
from pywebanno.get import ns
import os
import logging
import requests
from lxml import etree


def _addElToXMI(x, el, el_ns, attr, nmsp=ns):
    """High-order function: add a new annotation element to an xmi file
    :param: x: the parsed xmi file to update
    :param: el: the name of the element to add
    :param: el_ns: the namespace for the element
    :param: attr: a dictionary with the attributes (except for the ID and the sofa id! that is generated automatically)
    :param: nmsp: a dictionary with a map of the namespaces
    :return: int: the xmi:id of the new element created
    """
    root = x.getroot()
    sofa = root.find("cas:Sofa", namespaces=nmsp)
    sofa_id = sofa.attrib["{http://www.omg.org/XMI}id"]
    viewEl = x.find("cas:View", namespaces=nmsp)
    ids = sorted([int(i) for i in viewEl.attrib["members"].split(" ")])
    last_id = ids[-1]
    if last_id > 12:
        new_id = last_id + 1
    else:
        new_id = 13
    tname = "{%s}%s" % (el_ns, el)
    tag = etree.SubElement(root, tname, attrib=attr, nsmap=nmsp)

    # move the newly appended element two elements above, so that we leave always Sofa and View as last
    root.insert(-3, root[-1])
    tag.attrib["{http://www.omg.org/XMI}id"] = str(new_id)
    tag.attrib["sofa"] = sofa_id
    viewEl.attrib["members"] = viewEl.attrib["members"] + " {}".format(new_id)
#    index = root.index(root[-1])
#    root.insert(index, sofa)
#    root.insert(index, viewEl)

    return new_id


class XMISerializer():
    def __init__(self, docname, raw, lang):
        self._template_path = os.path.join(os.path.dirname(idai_journals.__file__), "lib/template_daipub.xmi")
        self.raw = raw.replace("\x0c", "\n")
        self.lang = lang
        self._ns = ns
        self.doc = docname
        self.tree = self._loadTree()
        self.root = self.tree.getroot()
        
    @property
    def sentences(self):
        return self.tree.xpath("//type4:Sentence", namespaces=self._ns)
    @property
    def tokens(self):
        return self.tree.xpath("//type4:Token", namespaces=self._ns)
        
    def _loadTree(self):
        x = etree.parse(self._template_path)
        root = x.getroot()
        metadata = root.find("type2:DocumentMetaData", namespaces=self._ns)
        metadata.attrib["end"] = str(len(self.raw))
        metadata.attrib["language"] = self.lang
        sofa = root.find("cas:Sofa", namespaces=self._ns)
        sofa.attrib["sofaString"] = self.raw
        return x
    
    # generate sentences
    def generateSentences(self, sent_tokens):
        for stok in sent_tokens:
            attrs = {"begin" : str(stok[0]), "end" : str(stok[1])}
            _addElToXMI(self.tree, "Sentence", self._ns["type4"], attrs)

    # generate the tokens
    def generateTokens(self, span_tokens):
        for tok in span_tokens:
            attrs = {"begin" : str(tok[0]), "end" : str(tok[1])}
            _addElToXMI(self.tree, "Token", self._ns["type4"], attrs)
            
    # generate the annotations...
    # 1. POS tag?
    def addPOSTags(self, pos_tagged_toks, span_toks, includeLemma=True):
        for span,tok in zip(span_toks, pos_tagged_toks):
            attrs = {"begin" : str(span[0]), "end" : str(span[1]), "PosValue" : tok[1]}
            posel = _addElToXMI(self.tree, "POS", self._ns["pos"], attrs)
            if includeLemma:
                lemma_attrs = {"begin" : str(span[0]), "end" : str(span[1]), "value" : tok[-1]}
                lemmael = _addElToXMI(self.tree, "Lemma", self._ns["type4"], lemma_attrs)
            try:
                tel= self.tree.xpath("//type4:Token[@begin = '{}' and @end = '{}' ]".format(span[0], span[1]), namespaces=ns)[0]
            except IndexError:
                print("Token with position ({}-{}) not found!".format(span[0], span[1]))
            else:
                tel.attrib["pos"] = str(posel)
                if includeLemma:
                    tel.attrib["lemma"] = str(lemmael)

    #2. Named Entity
    #def addNE(self, dai_entities):
    #    pywebanno.insertNE(self.tree, dai_entities)
    
    #push it online
    def pushDocToWebanno(self, project_id, auth):
        """Push a doc to webanno 
        
        Parameters
        ----------
        auth : Tuple
                tuple with authentication parameters (user, password)
        
        Returns
        -------
        requests.Response
        """
        if pywebanno.doc_exists(project_id, self.doc):
            logging.error("There is already a document with the same name!")
            return None
        else:
            s = etree.tostring(self.tree, encoding="utf-8", xml_declaration=True)
            r = pywebanno.postDocument(project_id, s, self.doc, auth, "xmi")
            return r
    
    
    def updateAnnotation(self, project_id, doc_id, auth):
        raise NotImplementedError

class PubXMI(XMISerializer):
    def __init__(self, dai_publication):
        self._pub = dai_publication
        self._sentence_tok = dai_publication._tokenizer
        self._doc = dai_publication.lang.upper() + "_" + os.path.basename(dai_publication._path)
        self._span_toks = dai_publication.span_words
        self._toks = dai_publication.words
        self._postags = dai_publication.do_pos_tag()
        #self._ners = dai_publications.NER()
        super().__init__(self._doc, dai_publication.raw, dai_publication.lang)

    def generateSentences(self):
        super().generateSentences(self._pub._span_sents)

    def generateTokens(self):
        super().generateTokens(self._span_toks)
        
    def generatePOS(self, includeLemma=True):
        super().addPOSTags(self._postags, self._span_toks, includeLemma)
    
    #def generateEntities(self):
    #    ners = self._pub.NER()
    #    entities = self._pub.getEntities(ners)
    #    super().addNE(entities)
        