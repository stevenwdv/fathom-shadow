from json import load
from math import ceil
from pathlib import Path

import click
from click import argument, BadOptionUsage, command, option
from more_itertools import pairwise
from numpy import histogram
from sklearn.preprocessing import minmax_scale

from ..utils import path_or_none, tensors_from
from ..vectorizer import make_or_find_vectors


@command()
@argument('training_set',
          type=click.Path(exists=True, resolve_path=True),
          metavar='TESTING_SET_FOLDER')
@option('--ruleset', '-r',
        type=click.Path(exists=True, dir_okay=False, resolve_path=True),
        callback=path_or_none,
        help='The rulesets.js file containing your rules. The file must have no imports except from fathom-web, so pre-bundle if necessary.')
@option('--trainee',
        type=str,
        metavar='ID',
        help='The trainee ID of the ruleset you are testing. Usually, this is the same as the type you are testing.')
@option('--training-cache',
        type=click.Path(dir_okay=False, resolve_path=True),
        callback=path_or_none,
        help='Where to cache training vectors to speed future testing runs. Any existing file will be overwritten. [default: vectors/training_yourTraineeId.json next to your ruleset]')
@option('--delay',
        default=5,
        type=int,
        show_default=True,
        help='Number of seconds to wait for a page to load before vectorizing it')
@option('--show-browser',
        default=False,
        is_flag=True,
        help='Show browser window while vectorizing. (Browser runs in headless mode by default.)')
def main(training_set, ruleset, trainee, training_cache, delay, show_browser):
    """Print a histogram of feature values, showing what proportion at each
    value was a positive or negative sample.

    This gives you an idea whether a feature is broadly applicable,
    discriminatory, and spitting out what you expect.

    """
    training_set = Path(training_set)
    if training_set.is_dir():
        if not ruleset:
            raise BadOptionUsage('ruleset', 'A --ruleset file must be specified when TRAINING_SET_FOLDER is passed a directory.')
        if not trainee:
            raise BadOptionUsage('trainee', 'A --trainee ID must be specified when TRAINING_SET_FOLDER is passed a directory.')

    with make_or_find_vectors(ruleset,
                              trainee,
                              training_set,
                              training_cache,
                              show_browser,
                              'training',
                              delay).open(encoding='utf-8') as training_file:
        training_data = load(training_file)
    training_pages = training_data['pages']
    x, y, num_yes = tensors_from(training_pages)
    x_t = x.T  # [[...feature0 values across all pages...], [...feature1 values...], ...].
    feature_names = training_data['header']['featureNames']
    BAR_WIDTH = 80
    samples_per_char = len(y) / BAR_WIDTH

    for name, values in zip(feature_names, x_t):
        print(f'{name}:')
        is_boolean = is_boolean_feature(values)
        counts, boundaries = histogram(values.numpy(),
                                       bins=2 if is_boolean else 10)
        lengths = (counts / samples_per_char).round().astype(int)
        highest_boundary = boundaries[-1]
        for boundary, length, count, (low_bound, high_bound) in zip(boundaries, lengths, counts, pairwise(boundaries)):
            is_last_time = high_bound == highest_boundary

            # Whether each feature value is a member of this bucket. Last
            # interval is inclusive on the right.
            x_is_for_this_bar = ((x_t[0] >= low_bound) &
                                  ((x_t[0] <= high_bound) if is_last_time else
                                   (x_t[0] < high_bound)))

            y_for_this_bar = y.T[0].masked_select(x_is_for_this_bar)
            positives = (y_for_this_bar.numpy() == 1).sum()
            negatives = len(y_for_this_bar) - positives
            positives_length = int(round(positives / samples_per_char))
            negatives_length = int(round(negatives / samples_per_char))

            label = ceil(boundary) if is_boolean else f'{boundary:.1f}'
            print(f'{label: >4} {"+" * positives_length}{"-" * negatives_length} {count}: {positives}+ / {negatives}-')


def is_boolean_feature(t):
    """Given a 1-D Tensor of a single feature's value across many samples,
    return whether it appears to be a yes/no feature."""
    return ((t == 0) | (t == 1)).min().item()
