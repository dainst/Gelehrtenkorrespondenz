import pytest
import training as trn
from templates import template1



@pytest.fixture
def trainer():
    """Returns a trained corpus"""
    return trn.Trainer("lib/config/korr_main.json")


@pytest.fixture
def dicts():
    """Returns a dict of dictionaries"""
    return trn.load_dictionaries( {"persons": "lib/dictionaries/persons.txt",
                                   "places": "lib/dictionaries/places.txt"})

@pytest.fixture
def tagged_sent0(trainer):
    return trainer._corpus.full_tagged_sents()[0]


def test_dicts(dicts):
    assert len(dicts["persons"]) == 2783


def test_corpus_reader(trainer):
    assert len(trainer._corpus.sents()) > 0


def test_taggedsent(tagged_sent0):
    assert tagged_sent0[2] == ('Braun', 'NE', 'Braun', 'HEAD', 'B-PERauthor')


def test_Xestraction(trainer, tagged_sent0):
    trainer.training = [tagged_sent0, ]
    trainer.set_feats_labels(template1)
    assert trainer.X_train[0][2]["pos[0]"] == "NE"


def test_split(trainer):
    train,test = trainer.split()
    flat_test = [i for sent in test for i in sent ]
    assert len(flat_test) >= 17641

