from nltk.corpus.reader import ConllCorpusReader
from nltk.util import LazyMap, LazyConcatenation

class KorrIOBCorpusReader(ConllCorpusReader):
    
    def __init__(self, root, fileids, columntypes):
        super().__init__(root, fileids, [c for c in columntypes if c not in ["textlayer", "entityid", "lemma"]])
        self.TEXTLAYER = "textlayer"
        self.ENTITYID="entityid"
        self.LEMMA="lemma"
        self.COLUMN_TYPES = (self.WORDS, self.LEMMA, self.POS, self.TREE, self.CHUNK, self.NE, self.SRL, 
                             self.IGNORE, self.TEXTLAYER, self.ENTITYID)
        self._colmap = dict((c,i) for (i,c) in enumerate(columntypes))
        
    def full_tagged_words(self, fileids=None, tagset=None):
        #self._require(self.WORDS, self.POS, self.TEXTLAYER, self.CHUNK, self.LEMMA)#, self.ENTITYID)
        def get_tagged_words(grid):
            return self._get_full_tagged_words(grid, tagset)
        return LazyConcatenation(LazyMap(get_tagged_words,
                                         self._grids(fileids)))

    def full_tagged_sents(self, fileids=None, tagset=None):
        #self._require(self.WORDS, self.POS)
        def get_tagged_words(grid):
            return self._get_full_tagged_words(grid, tagset)
        return LazyMap(get_tagged_words, self._grids(fileids))

    def _get_full_tagged_words(self, grid, tagset=None):
        pos_tags = self._get_column(grid, self._colmap['pos'])
        if tagset and tagset != self._tagset:
            pos_tags = [map_tag(self._tagset, tagset, t) for t in pos_tags]
        return list(zip(
                self._get_column(grid, self._colmap['words']),
                pos_tags,
                self._get_column(grid, self._colmap['lemma']),
                self._get_column(grid, self._colmap['textlayer']),
                self._get_column(grid, self._colmap['chunk'])#,
#                self._get_column(grid, self._colmap['entityid'])
                ))
                