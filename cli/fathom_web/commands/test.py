from json import JSONDecodeError, loads
from pathlib import Path

import click
from click import argument, BadOptionUsage, BadParameter, command, option

from ..accuracy import accuracy_per_tag, per_tag_metrics, pretty_accuracy, print_per_tag_report
from ..utils import classifier, path_or_none, speed_readout, tensor, tensors_from
from ..vectorizer import make_or_find_vectors


def decode_weights(ctx, param, value):
    """Validate a click option, making sure it's a valid JSON object with
    properly formatted "coeff" and "bias" keys."""
    try:
        decoded_weights = loads(value)
    except JSONDecodeError:
        raise BadParameter('Weights must be a valid JSON object.')

    if 'coeffs' not in decoded_weights or 'bias' not in decoded_weights:
        raise BadParameter('Weights must contain "coeffs" and "bias" keys.')
    if not isinstance(decoded_weights['bias'], float):
        raise BadParameter('Bias must be a float.')
    if not (isinstance(decoded_weights['coeffs'], list) and
            all((len(pair) == 2 and
                 isinstance(pair[0], str) and
                 isinstance(pair[1], float))
                for pair in decoded_weights['coeffs'])):
        raise BadParameter('Coeffs must be a list of 2-element lists: [["ruleName", numericCoefficient], ...].')
    return decoded_weights


def model_from_json(weights, num_outputs, feature_names):
    """Return a linear model with the the passed in coeffs and biases.

    :arg weights: A dict with coeff and bias keys, as the program takes from
        the commandline
    :arg num_outputs: The number of output nodes of the network, typically 1
    :arg feature_names: The ordered list of feature names so we can get the
        coeffs lined up with the feature order used by the vectors

    """
    model = classifier(len(weights['coeffs']), num_outputs)
    coeffs = dict(weights['coeffs'])
    model.load_state_dict({'0.weight': tensor([[coeffs[f] for f in feature_names]]),
                           '0.bias': tensor([weights['bias']])})
    return model


@command()
@argument('testing_set',
          type=click.Path(exists=True, resolve_path=True),
          metavar='TESTING_SET_FOLDER')
@argument('weights', callback=decode_weights)
@option('--confidence-threshold', '-t',
        default=0.5,
        show_default=True,
        help='Threshold at which a sample is considered positive. Higher values decrease false positives and increase false negatives.')
@option('--ruleset', '-r',
        type=click.Path(exists=True, dir_okay=False, resolve_path=True),
        callback=path_or_none,
        help='The rulesets.js file containing your rules. The file must have no imports except from fathom-web, so pre-bundle if necessary.')
@option('--trainee',
        type=str,
        metavar='ID',
        help='The trainee ID of the ruleset you are testing. Usually, this is the same as the type you are testing.')
@option('--testing-cache',
        type=click.Path(dir_okay=False, resolve_path=True),
        callback=path_or_none,
        help='Where to cache testing vectors to speed future testing runs. Any existing file will be overwritten. [default: vectors/testing_yourTraineeId.json next to your ruleset]')
@option('--delay',
        default=5,
        type=int,
        show_default=True,
        help='Number of seconds to wait for a page to load before vectorizing it')
@option('--show-browser',
        default=False,
        is_flag=True,
        help='Show browser window while vectorizing. (Browser runs in headless mode by default.)')
@option('--verbose', '-v',
        default=False,
        is_flag=True,
        help='Show per-tag diagnostics, even though that could ruin blinding for the test set.')
def main(testing_set, weights, confidence_threshold, ruleset, trainee, testing_cache, delay, show_browser, verbose):
    """Compute the accuracy of the given coefficients and biases on a folder of
    testing samples.

    TESTING_SET_FOLDER is a directory of labeled testing pages. It can also be,
    for backward compatibility, a JSON file of vectors from FathomFox's
    Vectorizer.

    WEIGHTS should be a JSON-formatted object like this. You can paste it
    directly from the output of fathom-train.

        {"coeffs": [["nextAnchorIsJavaScript", 1.1627885103225708],
        ["nextButtonTypeSubmit", 4.613410949707031],
        ["nextInputTypeSubmit", 4.374269008636475]],

        "bias": -8.645608901977539}

    """
    testing_set = Path(testing_set)
    if testing_set.is_dir():
        if not ruleset:
            raise BadOptionUsage('ruleset', 'A --ruleset file must be specified when TESTING_SET_FOLDER is passed a directory.')
        if not trainee:
            raise BadOptionUsage('trainee', 'A --trainee ID must be specified when TESTING_SET_FOLDER is passed a directory.')

    testing_data = make_or_find_vectors(ruleset,
                                        trainee,
                                        testing_set,
                                        testing_cache,
                                        show_browser,
                                        'testing',
                                        delay)
    testing_pages = testing_data['pages']
    x, y, num_yes, num_prunes = tensors_from(testing_pages)
    model = model_from_json(weights, len(y[0]), testing_data['header']['featureNames'])

    accuracy, false_positives, false_negatives = accuracy_per_tag(y, model(x), confidence_threshold, num_prunes)
    print(pretty_accuracy('Testing', accuracy, len(x), false_positives, false_negatives, num_yes + num_prunes))

    if testing_pages and 'time' in testing_pages[0]:
        print(speed_readout(testing_pages))

    if verbose:
        print('\nTesting per-tag results:')
        print_per_tag_report([per_tag_metrics(page, model, confidence_threshold) for page in testing_pages])
