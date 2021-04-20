#!/usr/bin/env python3

import random
from random import shuffle
from sys import argv

from click import progressbar
from fathom_web.utils import samples_from_dir
from numpy import unique
from pyquery import PyQuery as pq
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.linear_model import PassiveAggressiveClassifier, SGDClassifier
from sklearn.metrics import accuracy_score, hinge_loss, log_loss
from tensorboardX import SummaryWriter


def load_data(positive_dir, negative_dir):
    """Load the samples from disk.

    Make sure we have the same number of positive and negative samples in
    training and testing. Otherwise, choose randomly, and shuffle the result so
    we don't throw off the first epoch. (Shuffling happens after epochs.)

    """
    positive_corpus = [(text_from_sample(filename), 1) for filename in samples_from_dir(positive_dir)]
    negative_corpus = [(text_from_sample(filename), -1) for filename in samples_from_dir(negative_dir)]
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
    #tfidf_matrix = vectorizer.fit_transform(x_train)
    #print(tfidf_matrix.toarray())
    # TODO: Add stemming. Otherwise evaluate the tokenizer.
    #print(vectorizer.vocabulary_)
    # TODO: Consider using a hashing vectorizer in production to save
    # RAM/storage with large vocabs.

    x_train = vectorizer.fit_transform(x_train)
    print('Stopwords:', vectorizer.stop_words_)
    x_test = vectorizer.transform(x_test)

    # Chi^2 seems like a weird thing to use for non-categoricals.
    #     ch2 = SelectKBest(chi2, k=1000)
    #     x_train = ch2.fit_transform(x_train, y_train)
    #     x_test = ch2.transform(x_test)

    # price regex as signal? But I don't want to write signal.

    return x_train, x_test


def model_data(x_train, y_train, iterations, validation_fraction=0.2):
    """Train and return a predictive model of the data."""
    #model = PassiveAggressiveClassifier()
    # early_stopping=True, class_weight='balanced', validation_fraction=.2
    #loss_fn = hinge_loss
#     model = SGDClassifier(class_weight='balanced', validation_fraction=validation_fraction, early_stopping=True, verbose=100, random_state=43, max_iter=50, n_iter_no_change=10)
#     # n_iter_no_change 5 gave .8
#     #                  10 gave .83
    model = SGDClassifier(class_weight='balanced', validation_fraction=validation_fraction, early_stopping=True, verbose=0, random_state=48, max_iter=100, n_iter_no_change=5, learning_rate='adaptive', eta0=1)
    # Testing accuracies:
    # eta0=.01:
    # n_iter_no_change 5 gave .816
    #                  10 gave .816 but asked for a higher max_iter
    #                  10 with higher max_iter gave .816
    # Changing random_state to 48 gives .73 :-P

    # eta0=.1 (Trying bigger to knock us out of local minima:
    # n_iter_no_change 5 gave .816 at random=43; .75 at random=42; .816 at random=48
    #                  10 gave .816 at random=43; .766 at random=42; .8 at random=48

    # NEXT: Go by loss, not test accuracy.

    # Training/testing accuracies:
    # eta0=1 (Trying bigger to knock us out of local minima:
    # n_iter_no_change 5 gave 95.4/80.0 at random=43; 95.8/73.3 at random=42; 93.8/83.3 at random=48
    #                  10 gave
    
    # Different random_states give training accuracies of 95.4, 97.0, 95.8, 94.2
    model.fit(x_train, y_train)
    return model

    loss_fn = hinge_loss
    x_validation, x_train = partition(x_train, validation_fraction)
    y_validation, y_train = partition(y_train, validation_fraction)
    writer = SummaryWriter(comment='sgd svm fit() earlystopping')

    classes = unique(y_train)
    # TODO: Balance classes.
    prev_validation_loss = None
    with progressbar(range(iterations), label='Training') as bar:
        for t in bar:
            model.partial_fit(x_train, y_train, classes=classes)
            pred = model.predict(x_train)
            accuracy = accuracy_score(y_train, pred)
            validation_loss = loss_fn(y_validation, model.predict(x_validation))
            writer.add_scalar('training accuracy',
                              accuracy,
                              t)
            writer.add_scalar('training loss',
                              loss_fn(y_train, pred),
                              t)
            writer.add_scalar('validation loss',
                              validation_loss,
                              t)

            if False:
                # Do early stopping:
                if prev_validation_loss is not None and validation_loss > prev_validation_loss and t >= 13:
                    # Restore previous model:
                    model.coef_ = prev_coef
                    model.intercept_ = prev_intercept
                    print(f'Stopping early at iteration {t} with training accuracy {accuracy}.')
                    break
                else:
                    prev_validation_loss = validation_loss
                    # TODO: Don't redo allocation each time.
                    prev_coef = model.coef_.copy()
                    prev_intercept = model.intercept_.copy()  # copy() not really needed
    return model


def main(positive_dir, negative_dir):
    random.seed(42)

    x_train, y_train, x_test, y_test = load_data(positive_dir, negative_dir)
    x_train, x_test = vectorize_data(x_train, x_test)
    print(f'Dimensions: {x_train.shape[1]}')
    model = model_data(x_train, y_train, 1500)
    pred = model.predict(x_test)
    accuracy = accuracy_score(y_test, pred)
    print(f'Training accuracy: {accuracy_score(y_train, model.predict(x_train))}')
    print(f'Test accuracy: {accuracy}')

    # NEXT: Try different classifiers, and teach it some basic HTML features. Also, get it more convergent; graph loss to see what's going on.


def partition(sliceable, proportion):
    """Divide sliceable into 2 pieces, and return them as a tuple."""
    try:
        length = len(sliceable)
    except TypeError:  # It was a matrix.
        length = len(sliceable.getnnz(1))
    boundary = round(proportion * length)
    return sliceable[:boundary], sliceable[boundary:]


def text_from_sample(filename):
    """Return the innerText (or thereabouts) from an HTML file."""
    with open(filename, encoding='utf-8') as file:
        return pq(file.read()).text()


if __name__ == '__main__':
    main(argv[1], argv[2])
