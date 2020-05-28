from json import load
from math import ceil
from pathlib import Path

import click
from click import argument, BadOptionUsage, command, get_terminal_size, option, style
from more_itertools import pairwise
from numpy import histogram

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
@option('--buckets', '-b',
        default=10,
        type=int,
        show_default=True,
        help='Number of histogram buckets to use for non-boolean features')
@option('features', '--feature', '-f',
        type=str,
        multiple=True,
        help='The features to graph. Omitting this graphs all features.')
def main(training_set, ruleset, trainee, training_cache, delay, show_browser, buckets, features):
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

    training_data = make_or_find_vectors(
        ruleset,
        trainee,
        training_set,
        training_cache,
        show_browser,
        'training',
        delay)
    training_pages = training_data['pages']
    x, y, num_yes, _ = tensors_from(training_pages)
    feature_names = training_data['header']['featureNames']
    print_feature_report(feature_metrics(feature_names, x, y, buckets, features or feature_names))


def feature_metrics(feature_names, x, y, buckets, enabled_features):
    x_t = x.T  # [[...feature0 values across all pages...], [...feature1 values...], ...].
    for name, values in zip(feature_names, x_t):
        if name not in enabled_features:
            continue
        is_boolean = is_boolean_feature(values)
        _, boundaries = histogram(values.numpy(),
                                  bins=2 if is_boolean else buckets)
        highest_boundary = boundaries[-1]
        bars = []
        for boundary, (low_bound, high_bound) in zip(boundaries, pairwise(boundaries)):
            is_last_time = high_bound == highest_boundary

            # Whether each feature value is a member of this bucket. Last
            # interval is inclusive on the right.
            x_is_for_this_bar = ((values >= low_bound) &
                                 ((values <= high_bound) if is_last_time else
                                  (values < high_bound)))

            y_for_this_bar = y.T[0].masked_select(x_is_for_this_bar)
            positives = (y_for_this_bar.numpy() == 1).sum()
            negatives = len(y_for_this_bar) - positives
            label = str(ceil(boundary)) if is_boolean else f'{boundary:.1f}'
            bars.append((label, positives, negatives))
        yield name, bars


def print_feature_report(metrics):
    def bar(length, label):
        """Return a bar of about the given length with the given label printed
        on it.

        We may cheat and expand a bar a bit to fit the label.

        """
        if not label:
            # Don't expand a bar just to print a 0. The bar's absence serves.
            label = ''
        return ('{label: ^%i}' % length).format(label=label)

    term_width = get_terminal_size()[0]
    pos_style = style('', fg='black', bg='bright_green', bold=True, reset=False)
    neg_style = style('', fg='bright_white', bg='bright_black', bold=True, reset=False)
    style_reset = style('', reset=True)
    print(f'{pos_style} {style_reset} Positive Samples   {neg_style} {style_reset} Negative Samples')
    for feature, bars in metrics:
        longest_bar = max((positives + negatives) for _, positives, negatives in bars)
        print('\n', style(feature, bold=True), sep='')
        longest_label = max(len(label) for label, _, _ in bars)
        longest_total = max(len(str(n + p)) for _, p, n in bars)
        # This could still be slightly short if bar() has to cheat any bar lengths:
        samples_per_char = longest_bar / (term_width - longest_label - longest_total - 4)
        for label, positives, negatives in bars:
            pos_length = int(round(positives / samples_per_char))
            neg_length = int(round(negatives / samples_per_char))
            padded_label = ('{label: >%i}' % longest_label).format(label=label)
            pos_bar = bar(pos_length, positives)
            neg_bar = bar(neg_length, negatives)
            print(f'  {padded_label} {pos_style}{pos_bar}{style_reset}{neg_style}{neg_bar}{style_reset}{" " if (positives + negatives) else ""}{positives + negatives}')


def is_boolean_feature(t):
    """Given a 1-D Tensor of a single feature's value across many samples,
    return whether it appears to be a yes/no feature."""
    return ((t == 0) | (t == 1)).min().item()
