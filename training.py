import re
from config_reader import ProjectCofiguration
#from

import sklearn
import scipy.stats
from sklearn.metrics import make_scorer

from sklearn_crfsuite import CRF, scorers, metrics

from korr_corpusreader import KorrIOBCorpusReader
from crfsuite import feature_extractor

import logging

def load_dictionaries(dics):
    """Takes a dictionary with {category : path} and returns a dictionary
    { category : entry_list }

    :param dics: mapping {category : path to dictionary}
    :type dics: dict
    :return: dict (category : list of entries)
    """
    for k, v in dics.items():
        with open(v) as f:
            lines = f.read().split("\n")
            dics[k] = lines
    return dics


def sent2simplifiedlabel(sent):
    import re
    reg = re.compile(r'^([IB]-OBJ+)[a-z]+')
    symp = [reg.sub(r'\1', label) for token, postag, lemma, text_layer, label in sent]
    # second passage: delete some relations
    symp = [re.sub(r'[IB]-(DATEpoststamp|MISC)', 'O', label) for label in symp]

    return symp


class Trainer():
    def __init__(self, config):
        self._config = ProjectCofiguration(config)
        self._cols = ["words", "pos", "lemma", "textlayer", "chunk", "entityid"]
        self._corpus = KorrIOBCorpusReader(self._config.root_training, r".*\.iob", columntypes=self._cols)
        self.training = self._corpus.full_tagged_sents()
        self.test = None
        self.dictionaries = load_dictionaries(self._config.dictionaries)

        # Logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Model
        self.crf = CRF(algorithm='lbfgs', c1=0.23110659280031873, c2=0.023096867643725663, 
                     max_iterations=100, all_possible_transitions=True)

        #Train and test features (X) and labels (y)
        self.X_train = None
        self.y_train = None
        self.X_test = None
        self.y_test = None

    def reload_corpus(self, regexp):
        """
        Reload a corpus using a regexp for fileids
        :param regexp:
        :return:
        """
        pass


    def split(self, test_perc=0.2):
        """
        Split the corpus into training and testing. Randomize the selection of sentences and add sentences
        until the total number of tokens of the test section is equal or greater than test_perc.
        :param test_perc: percentage of tokens saved for tests
        :type test_perc: float (between 0 and 1)
        :return: tuple (of lists): train corpus, test corpus
        """
        import random
        import numpy as np

        assert 0 < test_perc < 1, "The test percentage must be a value between 0 and 1"
        c = 0
        max_test_len = int(np.ceil(len(self._corpus.words()) * test_perc))
        corpus_train, corpus_test = ([], [])
        sents = list(self._corpus.full_tagged_sents())
        random.shuffle(sents)
        for sent in sents:
            if c < max_test_len:
                corpus_test.append(sent)
                c = c + len(sent)
            else:
                corpus_train.append(sent)
        return corpus_train, corpus_test


    def set_feats_labels(self, templ):
        ext = InstanceFeatureExtractor(self.training, self.dictionaries)
        self.X_train = ext.extract_features(templ)
        self.y_train = [sent2simplifiedlabel(s) for s in self.training]

        if self.test:
            test_ext = InstanceFeatureExtractor(self.test, self.dictionaries)
            self.X_test = test_ext.extract_features(templ)
            self.y_test = [sent2simplifiedlabel(s) for s in self.test]


    def fit(self):
        self.crf.fit(self.X_train, self.y_train)


    def evaluate(self):
        from collections import Counter

        def return_transitions(trans_features):
            trans = []
            for (label_from, label_to), weight in trans_features:
                trans.append("%-6s -> %-7s %0.6f" % (label_from, label_to, weight))
            return trans

        #print("Top likely transitions:")
        #print_transitions(Counter(crf.transition_features_).most_common(20))

        #print("\nTop unlikely transitions:")
        #print_transitions(Counter(crf.transition_features_).most_common()[-20:])
        labels = list(self.crf.classes_)

        labels.remove('O')
        y_pred = self.crf.predict(self.X_test)
        eval = {"F1_general" : metrics.flat_f1_score(self.y_test, y_pred,
                      average='weighted', labels=labels)}
        sorted_labels = sorted(labels, key=lambda name: (name[1:], name[0]))
        eval["F1_class"] = metrics.flat_classification_report(self.y_test, y_pred, labels=sorted_labels, digits=3)
        eval["Top_likely_transitions"] = return_transitions(Counter(self.crf.transition_features_).most_common(20))
        eval["Top_unlikely_transitions"] = return_transitions(Counter(self.crf.transition_features_).most_common()[-20:])

        return eval


    def write_model(self, outfile):
        import pickle
        pass




class InstanceFeatureExtractor:
    """
    An instance is a list of tagged sentence. It can be a document, a corpus or a training or testing set.
    Use this class to transform a collection of sentences into a list of list of feature.
    """

    def __init__(self, instance, dictionaries):
        self._dictionaries = dictionaries
        self._sentences = instance
        self._featdictlist = [SentFeatureExtractor(s,i, self._dictionaries).features
                              for i,s in enumerate(self._sentences)]
        # Logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.logger.info("Generating the list of features for the tokens")


    def extract_features(self, templ_name):
       sent_feats = []
       self.logger.info("Extracting the features with the specified template")
       for sent in self._featdictlist:
           feature_extractor(sent, templ_name)
           s = [f["F"] for f in sent]
           sent_feats.append(s)
       return sent_feats


    # def extract_feature(self, templ_name):
    #     """
    #     Work with features, which are list of lists (sentences) of lists (features)
    #     Return a list of lists (sentences) of dictionaries (features)
    #     :param templ_name: name of a template
    #     :return:
    #     """
    #     feats = self._apply_template(templ_name)
    #     dic_feats = []
    #     for s in feats:
    #         sent = []
    #         for t in s:
    #             tok = {}
    #             for feat in t:
    #                 try:
    #                     k,v = feat.split("=")
    #                 except ValueError:
    #                     print(feat)
    #                 tok[k] =v
    #             sent.append(tok)
    #         dic_feats.append(sent)
    #     return dic_feats





class SentFeatureExtractor():
    def __init__(self, tokens, sentence_num, dictionaries):
        self._tokens = tokens
        self._num = sentence_num
        self._sentlen = len(tokens)
        self._dictionaries = dictionaries

        # Logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)


    @property
    def features(self):
        #self.logger.info("Generating the list of features for the tokens")
        extrs = [TokenFeatureExtractor(self._tokens, i, self._num, self._dictionaries) for i in range(self._sentlen)]
        return [t.feature_dict for t in extrs]


class TokenFeatureExtractor():
    def __init__(self, sentence, tok_num, sentence_num, dictionaries):
        """
        This particular token feature extractor expects the token to have the following structure:

        [word, pos, lemma]

        :param sentence: a sentence
        :type sentence: list of tuples (token, pos, lemmas, header, ne_chunk)
        :param tok_num: the index of a token to featurize
        :type tok_num: int
        :param sentence_num: index of the sentence
        :param dictionaries: dictionary ( dict_type : list of values)
        """
        self._token = sentence[tok_num]
        self._dictionaries = dictionaries

        # FEATURES
        self.w = self._token[0]
        self.w_lower = self.w.lower()
        self.pos = self._token[1]
        self.lemma = self._token[2]
        self.rank = str(tok_num)
        self.sent_rank = str(sentence_num)
        self.isDigit = self.w.isdigit()
        self.isUpper = self.w.isupper()
        self.isTitle = self.w.istitle()
        self.suffix_long = self.w[-4:]
        self.suffix_short = self.w[-2:]
        self.prefix_long = self.w[:5]
        self.prefix_short = self.w[:3]
        self.hasDigit = any(i.isdigit() for i in self.w)
        self.endsWithDigit = True if re.search(r'\d+$', self.w) else False
        self.isInPersonDic = self.w in self._dictionaries["persons"]
        self.isInPlaceDic = self.w in self._dictionaries["places"]


    @property
    def feature_dict(self):
        d = { k : str(v) for k,v in self.__dict__.items() if k[0] != "_"}
        d["F"] = {}
        return d

