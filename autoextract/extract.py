#!/usr/bin/env python3

import random
from random import shuffle
from sys import argv

from fathom_web.utils import samples_from_dir
from pyquery import PyQuery as pq
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.metrics import accuracy_score


def load_data(positive_dir, negative_dir):
    """Load the samples from disk.

    Make sure we have the same number of positive and negative samples in
    training and testing. Otherwise, choose randomly, and shuffle the result so
    we don't throw off the first epoch. (Shuffling happens after epochs.)

    """
    positive_corpus = [(text_from_sample(filename), 1) for filename in samples_from_dir(positive_dir)]
    negative_corpus = [(text_from_sample(filename), 0) for filename in samples_from_dir(negative_dir)]
    shuffle(positive_corpus)
    shuffle(negative_corpus)
    TRAINING_PROPORTION = .8
    pos_training, pos_testing = partition(positive_corpus, TRAINING_PROPORTION)
    neg_training, neg_testing = partition(negative_corpus, TRAINING_PROPORTION)
    training = pos_training + neg_training
    testing = pos_testing + neg_testing
    shuffle(training)
    shuffle(testing)

    # Unzip xs and ys:
    x_train, y_train = zip(*training)
    x_test, y_test = zip(*testing)

    return x_train, y_train, x_test, y_test


def vectorize_data(x_train, x_test):
    """Extract features and convert samples into vectors of floats."""
    # These settings seem to nicely weight heavily words that are uncommon
    # across docs and demote (though not eliminate) stopwords:
    vectorizer = TfidfVectorizer(max_df=.8)  # Decrease max_df to be more aggressive about declaring things stopwords.
    # Learn the words in the corpus. Other words seen in the future will be
    # ignored. Automatically reasons out stopwords by default.
    tfidf_matrix = vectorizer.fit_transform(x_train)
    #print(tfidf_matrix.toarray())
    # TODO: Add stemming. Otherwise evaluate the tokenizer.
    print('Stopwords:', vectorizer.stop_words_)
    #print(vectorizer.vocabulary_)
    # TODO: Consider using a hashing vectorizer in production to save
    # RAM/storage with large vocabs.

    x_train = vectorizer.fit_transform(x_train)
    x_test = vectorizer.transform(x_test)

    # Chi^2 seems like a weird thing to use for non-categoricals.
    #     ch2 = SelectKBest(chi2, k=1000)
    #     x_train = ch2.fit_transform(x_train, y_train)
    #     x_test = ch2.transform(x_test)

    # price regex as signal? But I don't want to write signal.

    return x_train, x_test


def model_data(x_train, y_train, x_test, y_test):
    """Train and return a predictive model of the data."""
    model = PassiveAggressiveClassifier(early_stopping=True, class_weight='balanced', validation_fraction=.2)
    model.fit(x_train, y_train)
    return model


def main(positive_dir, negative_dir):
    random.seed(42)

    x_train, y_train, x_test, y_test = load_data(positive_dir, negative_dir)
    x_train, x_test = vectorize_data(x_train, x_test)
    print(f'Dimensions: {x_train.shape[1]}')
    model = model_data(x_train, y_train, x_test, y_test)
    pred = model.predict(x_test)
    accuracy = accuracy_score(y_test, pred)
    print(f'Accuracy: {accuracy}')

    # NEXT: Try different classifiers, and teach it some basic HTML features. Also, get it more convergent; graph loss to see what's going on.


def partition(sliceable, proportion):
    """Divide sliceable into 2 pieces, and return them as a tuple."""
    boundary = round(proportion * len(sliceable))
    return sliceable[:boundary], sliceable[boundary:]


def text_from_sample(filename):
    """Return the innerText (or thereabouts) from an HTML file."""
    with open(filename, encoding='utf-8') as file:
        return pq(file.read()).text()


if __name__ == '__main__':
    main(argv[1], argv[2])
