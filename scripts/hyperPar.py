import sys
sys.path.append("../")

from korr_corpusreader import KorrIOBCorpusReader
from training import Trainer
from templates import template1

from sklearn.metrics import make_scorer
from sklearn.model_selection import RandomizedSearchCV

import scipy

import sklearn_crfsuite
from sklearn_crfsuite import scorers
from sklearn_crfsuite import metrics

import pickle

with open("../lib/models/korrespondez_model_stage4.pickle", "rb") as f:
    m = pickle.load(f)

labels = list(m.classes_)
labels.remove('O') 

f1_scorer = make_scorer(metrics.flat_f1_score,
                        average='weighted', labels=labels)

t = Trainer("../lib/config/korr_nlp.json")

#train,test = t.split(test_perc=0.20)
#t.training = train
#t.test = test

print("extracting features...")
t.set_feats_labels(template1)

params_space = {
    'c1': scipy.stats.expon(scale=0.5),
    'c2': scipy.stats.expon(scale=0.05),
}


# search
rs = RandomizedSearchCV(t.crf, params_space,
                        cv=3,
                        verbose=5,
                        n_jobs=1,
                        n_iter=50,
                        scoring=f1_scorer)

print("working with {} sentence".format(len(t.X_train)))                    
rs.fit(t.X_train, t.y_train)

print("Finished! Now I will write everything to a pickle file...")
print('best params:', rs.best_params_)

with open('randomized_search_results.pickle', 'wb') as out:
    pickle.dump(rs, out)
