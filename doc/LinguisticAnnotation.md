# Introduction<a name="intro"></a>

This file describes how to use (and maybe produce) linguistic annotation on the texts analyzed by the project [Gelehrte, Ausgräber und Kunsthändler](https://arachne.dainst.org/project/gelehrtenbriefe) of the DAI, funded by the DFG.

## Outline
1. [Introduction](#intro)
	* [Semi-automatic workflow](#semiauto)
	* [Automatic Annotation](#semiauto)
2. [HOWTOs and FAQs](#howtos)
3. [Workflow](#workflow)


## What we did

### Semiautomatic workflow<a name="semiauto"></a>

In Arachne, we have a series of volumes collecting the published letters concerning the early days of the institute. In total, we have [71 volumes](https://zenon.dainst.org/Search/Results?lookfor=000880085&type=ParentID&sort=title).

Of these, 9 volumes were annotated using a semi-automatic workflow, i.e. they were annotated automatically first, then corrected manually. The corrected annotation is stored in [Webanno](nlp.dainst.org:18080/webanno/) (i.e., an instance of the web-based annotation tool installed on one of the servers of the DAI). An export in an IOB format is also available [here](https://github.com/dainst/Gelehrtenkorrespondenz/tree/master/data/IOB_GOLD). This files constitute our "gold standard".

**Technical Note:** the IOB format of these files is NOT directly readable by Webanno. You will need to convert the files into a slightly different tab-separated format like [this one](https://github.com/dainst/Gelehrtenkorrespondenz/blob/master/data/TSV/4_MommsenAnBrunn_page001.tsv). One of the scripts used in this project performs this type of conversion: see [below](download).

**Technical Note:** the "gold standard" files (i.e. the manually corrected annotations) are stored in Webanno, but the annotation workflow has not been closed by the Project Curator. Make sure to download the annotation of the user `marina` to always get the most accurate versions.

See [below](#workflow) on how to download/export the annotations from Webanno.

### Automatic annotation<a name="auto"></a>

We then used the pages of the 9 "gold standard" volumes to annotate the remaining 62.

You can download a tar archive with the files (in a TSV format compatible with Webanno) from [here](https://github.com/dainst/Gelehrtenkorrespondenz/tree/master/data/test/webanno).

The annotation can also be visualized [here](http://nlp.dainst.org/brat/#/gelehrtekorrespondenz/AutomaticAnnotationTest/).

In total, they amount to 14.571 pages!

## What can be still done<a name="todo"></a>

... a lot! The trained CRF models (especially the final one) seems to work pretty well, but it can always gain in accuracy with more training data.

The semi-automatic workflow described above can be continued with more annotation!

# HOWTOs and FAQs<a name="howtos"></a>

## List of topics<a name="listoffaqs"></a>

* [What are we annotating?](#annotation)
* [What is a "model"?](#model)
* [How is CRF implemented?](#crf)
* [How do I use the model to annotate new texts?](#howtoannotate)
* [How to I train a new model?](#training)
* [What is a "template"?](#templates)

## What are we annotating?<a name="annotation"></a>

Basically, we want to retrieve the mentions to Person, Places, Organizations, Archaeological Objects and Dates within the texts.

For each of this categories (except Objects) some further sub-classification is given. E.g. we distinguish whether a person is the author of the letter, the addressee or simply somebody who's happens to be mentioned in the text. For places, we distinguish between the place from which the letter was sent, the places where it was delivered, or a location mentioned in the running text.

## What is a "model"?<a name="model"></a>

In order to annotate the texts we use [machine learning](https://en.wikipedia.org/wiki/Machine_learning). Simplifying a bit, we use features in the training data to teach a software how to predict the classification of words in some new texts.

In our case, we used some linguistic properties (the "features") of the 9 volumes mentioned above to guess whether words in the remaining 62 volumes belongs to the classes we were interested in.

For an introduction on the statistical method we used (Conditional Random Field, or CRF) see [here](https://en.wikipedia.org/wiki/Conditional_random_field)

## How is CRF implemented?<a name="crf"></a>

Everything is written in Python, and we used the `sklearn-crfsuite` implementation (see [here](https://sklearn-crfsuite.readthedocs.io)).

See below for some discussion on the `Trainer`.

## How do I use the trained models to annotate new texts?<a name="howtoannotate"></a>

An introduction is provided in this [Notebook](https://github.com/dainst/Gelehrtenkorrespondenz/blob/master/doc/How%20to%20annotate%20a%20text.ipynb).

Keep in mind that, as said in the other questions, we use a lot of linguistic features to guess the correct labelling of tokens. Some of them (e.g. whether a word is capitalized, or whether there is a number in it) can be straightforwardly guessed by analyzing the word itself. Some others rely on preliminary linguistic annotation (like the [Part-Of-Speech (POS) tagging](https://en.wikipedia.org/wiki/Part-of-speech_tagging)).

This means that, if your model uses POS-tagging as a feature (and our models do!), you must first POS-tag your text before using the model to annotate.

But everything is explained in the Notebook mentioned above.

## How do I train a CRF module with more/different data?<a name="training"></a>

See the introduction [here](https://github.com/dainst/Gelehrtenkorrespondenz/blob/master/doc/How%20to%20train%20new%20models.ipynb).

Basically, you may use a special [`Trainer`](https://github.com/dainst/Gelehrtenkorrespondenz/blob/master/training.py) class defined for this project, which is also included in this repository.

The `Trainer` reads a configuration file in JSON (see [here](https://github.com/dainst/Gelehrtenkorrespondenz/tree/master/lib/config) for a couple of examples) and allows you to perform every task involved in the training process.

In particular, you can use the `Trainer` in 2 scenarios:

* to evaluate how well you're model performs; use the [train-test splitting function](https://render.githubusercontent.com/view/ipynb?commit=c0bb045719a91eea6b4b6b146715876e0d0142c7&enc_url=68747470733a2f2f7261772e67697468756275736572636f6e74656e742e636f6d2f6461696e73742f47656c65687274656e6b6f72726573706f6e64656e7a2f633062623034353731396139316565613662346236623134363731353837366530643031343263372f646f632f486f77253230746f253230747261696e2532306e65772532306d6f64656c732e6970796e623f746f6b656e3d4148652d4e42354f456b36616a6a574b78306851545357424e67585674686c586b733562713238797741253344253344&nwo=dainst%2FGelehrtenkorrespondenz&path=doc%2FHow+to+train+new+models.ipynb&repository_id=116979459&repository_type=Repository#With-training/test-splitting)
* if you want to use all the available training data (e.g. to annotate some new text), use the entire corpus, without splitting the training set ([see here](https://render.githubusercontent.com/view/ipynb?commit=c0bb045719a91eea6b4b6b146715876e0d0142c7&enc_url=68747470733a2f2f7261772e67697468756275736572636f6e74656e742e636f6d2f6461696e73742f47656c65687274656e6b6f72726573706f6e64656e7a2f633062623034353731396139316565613662346236623134363731353837366530643031343263372f646f632f486f77253230746f253230747261696e2532306e65772532306d6f64656c732e6970796e623f746f6b656e3d4148652d4e42354f456b36616a6a574b78306851545357424e67585674686c586b733562713238797741253344253344&nwo=dainst%2FGelehrtenkorrespondenz&path=doc%2FHow+to+train+new+models.ipynb&repository_id=116979459&repository_type=Repository#Train-with-the-full-corpus))

## What is a "template"?<a name="templates"></a>

As said, a CRF trainer uses some linguistic features to learn what are the most useful properties of a word that could be used in the classification task. Basically, the trainer transforms each word in the text in a "bag of linguistic features". So, in the sentence:

```quote
John Smith is a nice guy

```

the second word is "studied" by the trainer as a list of properties, like `form=Smith`, `capitalized=True`, `isDigit=False` and so forth. That's not all! In order to classify it as a name (of a person), the software will find the information that this very word is preceded by the word "John" extremely useful; therefore, we may instruct the software to also include some features as `isPreviousCapitalized=True`, `previousForm=John` etc. in its learning exercise.

In order to decide which feature to extract for each token, `sklearn-crfsuite` allows you to define a template; there you define all the information that you want the CRF model to "study" or memorize for each token.

We create the templates as a tuple of tuples within the [`template.py'](https://github.com/dainst/Gelehrtenkorrespondenz/blob/master/training.py) file. The right template can be imported as regular python object, e.g.:

```python
from templates import template1
```

# Workflow<a name="workflow"></a>

So how would you replicate the whole annotation workflow? We adopted the following steps, which may also be continued ad lib.:

1. (optional) annotate some text automatically using the pre-trained models (see the instructions [here](#howtoannotate))
2. load your texts or annotation into Webanno
3. annotate them / correct them manually
4. download the corrected annotations and, in case, convert them to a suitable format
5. train a new and updated model
6. go back at step 1 with new texts and a new model

Each of these steps (starting from 2) is described with some more details in the following subsections.

## Load your documents to Webanno<a name="load"></a>

You can load either "clean" txt files to be annotated from scratches or use pre-annotated texts.

Have a look at the [Webanno documentation](https://webanno.github.io/webanno/releases/2.3.0/docs/user-guide.html#sect_formats), especially the sections about the accepted formats, as Webanno is pretty strict on the layers of annotation and the format to store information about them.

If you want, you can use the Web API to upload/download the documents programmatically. Your webanno account must have the REMOTE credentials for you to be able to use the API.

The API is experimental, its use is not recommended by the software maintainers, but it seems pretty stable to me. You can play around with it in the [Swagger](http://nlp.dainst.org:18080/webanno/swagger-ui.html#/) interface.

I have also written a minimalistic Python module called [`pywebanno`](https://github.com/dainst/PyWebanno) to interact with our Web API.

Up to now, we did everything with a dedicated project called `Gelehrtekorrespondenz_Test` (id=3). In order to start a workflow like the one described above, it might be beneficial to create a brand new project. It may be good to create it as a [Correction](https://webanno.github.io/webanno/releases/2.3.0/docs/user-guide.html#sect_correction) project (not as [Annotation](https://webanno.github.io/webanno/releases/2.3.0/docs/user-guide.html#sect_annotation)).

The settings and layers of annotation that you would need (for most of  them are custom) can be exported from the `Gelehrtekorrespondenz_Test` as JSON and reimported in the new project: go to `Projects > Gelehrtekorrespondenz_Test > [your layer]` and click on the `Export Layer` button. **Note** that you must have the ADMIN role to perform these steps.

**Important!** if you want to download the annotations in the same way as we did (see [below](#download)) make sure to build your file names with some meaningful structure. In particular, the script mentioned below requires the file name to have a stage number prepended, as in:

```quote
5_GerhardAnBraun1844-1856_page214.tsv"
```

In this example, `5` is the stage in the annotation cycle and `GerhardAnBraun1844-1856` is a human-readable id for the volume that was annotated in that particular stage.

## Annotate / correct in Webanno

See above and the [Webanno User guide](https://webanno.github.io/webanno/releases/2.3.0/docs/user-guide.html)

## Download and convert the annotation<a name="download"></a>

I use my [`pywebanno`](https://github.com/dainst/PyWebanno) to do it. Once you dowloaded the annotated files, you might need to convert them to some other format (e.g. the format required by the `Trainer` class).

Most of the time, in order to download files and convert them to the format used by the `Trainer`, I relied on a little script (which you might need to tweak according to the new settings of your project in Webanno in the future): [`getTrainingFromWebanno.py`](https://github.com/dainst/Gelehrtenkorrespondenz/blob/master/scripts/getTrainingFromWebanno.py)

The script takes a config json file (like [this ones](https://github.com/dainst/Gelehrtenkorrespondenz/tree/master/lib/config)) as argument and `--password` and `--stage` as parameters. Note (line 188) that the script is pulling the annotation of the user `marina`; I could do that because I am accessing the API with an account with ADMIN credentials (make sure you do the same), but you might need to modify the parameters passed to the Webanno API according to the structure and workflow of your own Webanno project.

The `--stage` option requires the files to have a recognizable part identifying the stage id in the cycle (see [above](#load)). This is used to filter the documents to be downloaded and converted.

## Training a new model

See the [FAQs](#training).

For the sake of this project, I used a pretty simple script called [`annotateTXT.py`](https://github.com/dainst/Gelehrtenkorrespondenz/blob/master/scripts/annotateTXT.py), which assumes that you have a single TXT file with the whole volume.

This script will annotate the pages of the TXT file and output the annotation as a list of TSV files (one per each of the volume pages) that can be imported into Webanno.

So we're back at [step 2](#load)... ;-)

