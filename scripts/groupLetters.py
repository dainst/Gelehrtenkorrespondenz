import locale
from datetime import datetime
from tqdm import tqdm

import sys
sys.path.append("../")
from korr_corpusreader import KorrIOBCorpusReader



locale.setlocale(locale.LC_TIME, ("de_DE", "UTF-8"))
date_formats = ["%d %B %Y", "%d . %B %Y", "%d %B , %Y", "%d . %B , %Y",
                "%d.%B %Y", "%d.%B.%Y", "%B %Y"]

def sub_leaves(tree, label):
    """it works with a tree and a label (from the chunker: ORG, LOC, PER, MISC).
    it will return only the sub-tree correspodning to the label"""
    return [t.leaves() for t in tree.subtrees(lambda s: s.label() == label)]


cols = ["words", "pos", "lemma", "textlayer", "chunk", "entityid"]
korr = KorrIOBCorpusReader("../data/IOB_GOLD", ".*\.iob", columntypes=cols)

letter_start = "###"

not_parsed = []
parsed = 0

with open("LetterPageList.csv", "w") as out:
    for f in tqdm(korr.fileids()):
        cks_sents = korr.chunked_sents(f)
        dates = []
        for t in cks_sents:
            dates.extend(sub_leaves(t, "DATEletter"))
        dt_output = "Not parsed"
        for date in dates:
            if dt_output != "Not parsed":
                break
            dlist = [w[0] for w in date]
            dlist[0] = dlist[0].zfill(2)
            d = " ".join(dlist)
            for date_format in date_formats:
                try:
                    dt = datetime.strptime(d, date_format)
                    dt_output = dt.strftime('%Y-%m-%d')
                except ValueError :
                    not_parsed.append((f, d))
                else:
                    parsed += 1
                    break
            if dt_output == "Not parsed":
                dt_output = d
        out.write("{}\t{}\n".format(f, dt_output))


with open("DatesNotParsed.tsv", "w") as log:
    for n in not_parsed:
        log.write("\t".join(n)+"\n")

print("Tot files with a parsed date: {}".format(parsed))
