import hashlib
from json import dump, JSONDecodeError, load
from pathlib import Path
from pprint import pformat

import click
from click import argument, BadOptionUsage, command, option, progressbar
from tensorboardX import SummaryWriter
from torch import tensor
from torch.nn import BCEWithLogitsLoss
from torch.optim import Adam

from ..accuracy import accuracy_per_tag, per_tag_metrics, pretty_accuracy, print_per_tag_report
from ..utils import classifier, read_chunks, samples_from_dir, speed_readout, tensors_from
from ..vectorizer import vectorize


def learn(learning_rate, iterations, x, y, confidence_threshold, validation=None, stop_early=False, run_comment='', pos_weight=None, layers=[]):
    # Define a neural network using high-level modules.
    writer = SummaryWriter(comment=run_comment)
    model = classifier(len(x[0]), len(y[0]), layers)
    if pos_weight:
        pos_weight = tensor([pos_weight])
    loss_fn = BCEWithLogitsLoss(reduction='sum', pos_weight=pos_weight)  # reduction=mean converges slower.
    # TODO: Maybe also graph using add_pr_curve(), which can show how that tradeoff is going.
    optimizer = Adam(model.parameters(), lr=learning_rate)

    if validation:
        validation_ins, validation_outs = validation
        previous_validation_loss = None
    stopped_early = False
    with progressbar(range(iterations)) as bar:
        for t in bar:
            y_pred = model(x)  # Make predictions.
            loss = loss_fn(y_pred, y)
            writer.add_scalar('loss', loss, t)
            if validation:
                validation_loss = loss_fn(model(validation_ins), validation_outs)
                if stop_early:
                    if previous_validation_loss is not None and previous_validation_loss < validation_loss:
                        stopped_early = True
                        model.load_state_dict(previous_model)  # noqa: previous_model will always be defined here, but the linter can't follow the logic.
                        break
                    else:
                        previous_validation_loss = validation_loss
                        previous_model = model.state_dict()
                writer.add_scalar('validation_loss', validation_loss, t)
            accuracy, _, _ = accuracy_per_tag(y, y_pred, confidence_threshold)
            writer.add_scalar('training_accuracy_per_tag', accuracy, t)
            optimizer.zero_grad()  # Zero the gradients.
            loss.backward()  # Compute gradients.
            optimizer.step()
    if stopped_early:
        print(f'Stopping early at iteration {t}, just before validation error rose.')

    # Horizontal axis is what confidence. Vertical is how many samples were that confidence.
    writer.add_histogram('confidence', confidences(model, x), t)
    writer.close()
    return model


def confidences(model, x):
    return model(x).sigmoid()


def pretty_coeffs(model, feature_names):
    """Format coefficient and bias numbers for easy pasting into JS."""
    dict_params = {}
    for name, param in model.named_parameters():
        dict_params[name] = param.data.tolist()
    if '2.weight' in dict_params:  # There are hidden layers.
        return pformat(dict_params, compact=True)
    else:
        pretty = ',\n        '.join(f'["{k}", {v}]' for k, v in zip(feature_names, dict_params['0.weight'][0]))
        return ("""{{"coeffs": [
        {coeffs}
        ],
     "bias": {bias}}}""".format(coeffs=pretty, bias=dict_params['0.bias'][0]))


def exclude_indices(excluded_indices, list):
    """Remove the elements at the given indices from the list, and return
    it."""
    # I benched this, and del turns out to be over twice as fast as
    # concatenating a bunch of slices on a list of 32 items.
    vacuum = 0
    for i in excluded_indices:
        del list[i - vacuum]
        vacuum += 1
    return list


def exclude_features(exclude, vector_data):
    """Given a JSON-decoded vector file, remove any excluded features, and
    return the modified object."""
    feature_names = vector_data['header']['featureNames']
    excluded_indices = [feature_names.index(e) for e in exclude]
    exclude_indices(excluded_indices, feature_names)
    for page in vector_data['pages']:
        for tag in page['nodes']:
            exclude_indices(excluded_indices, tag['features'])
    return vector_data


def path_or_none(ctx, param, value):
    return None if value is None else Path(value)


def hash_file(path):
    """Return the hex digest of the SHA256 hash of a file."""
    hash = hashlib.new('sha256')
    with path.open('rb') as file:
        for chunk in read_chunks(file):
            hash.update(chunk)
    return hash.hexdigest()


def out_of_date(sample_cache, ruleset, sample_set):
    """Determine whether the sample cache is out of date compared to the
    ruleset and sample set.

    If it is, return a dict of hashes we can add to the new sample cache. If
    not, return None.

    We use hashes to determine out-of-dateness because git sets the mod dates
    to now whenever it changes branches. This way, you can check out somebody
    else's branch from across the internet and still not have to revectorize,
    as long as they checked their vectors in. And it takes only .2s for 250
    samples on my 2020 SSD laptop.

    :arg sample_cache: A Path to possibly-pre-existing vector file
    :arg ruleset: A Path to a rulesets.js file. Can be None if ``sample_set``
        is a file.
    :arg sample_set: A Path to a folder full of samples

    """
    if sample_cache.exists():
        with sample_cache.open(encoding='utf-8') as file:
            try:
                cache_header = load(file)['header']
            except JSONDecodeError:
                cache_header = {}
    else:
        cache_header = {}
    ruleset_hash = hash_file(ruleset)
    page_hashes = {}
    for sample in samples_from_dir(sample_set):
        # Hash each file separately. Otherwise, we can't tell the difference
        # between file 1 that says "ab" and file 2 that says "c" vs. file 1
        # that says "a" and file 2 "bc". Plus, if we store the hashes along
        # with their sample-dir-relative paths, we can someday make this
        # revectorize only the new samples if some are added—and delete the
        # ones deleted.
        page_hashes[str(sample.relative_to(sample_set))] = hash_file(sample)
    if (ruleset_hash != cache_header.get('rulesetHash') or
        page_hashes != cache_header.get('pageHashes')):
        return {'pageHashes': page_hashes,
                'rulesetHash': ruleset_hash}


def make_or_read_vectors(ruleset, trainee, sample_set, sample_cache, show_browser, kind_of_set):
    """Return a Path to the vector file to use, building it first if necessary.

    If passed a vector file for ``sample_set``, we return it verbatim. If
    passed a folder rather than a vector file, we use the cache if it's fresh.
    Otherwise, we build the vectors, based on the given ``ruleset`` and
    ``trainee`` ID, and then cache them at Path ``sample_cache``.

    :arg sample_cache: A Path to possibly-pre-existing vector files or None to
        use the default location

    """
    if not sample_set.is_dir():
        return sample_set  # It's just a vector file.
    if not sample_cache:
        sample_cache = ruleset.parent / 'vectors' / f'{kind_of_set}_{trainee}.json'
    updated_hashes = out_of_date(sample_cache, ruleset, sample_set)
    if updated_hashes:
        # Make a vectors file, replacing it if already present:
        vectorize(ruleset, trainee, sample_set, sample_cache, show_browser)
        # Stick the new hashes in it:
        with sample_cache.open(encoding='utf-8') as file:
            json = load(file)
        json['header'].update(updated_hashes)
        with sample_cache.open('w', encoding='utf-8') as file:
            dump(json, file)
    return sample_cache


@command()
@argument('training_set',
          type=click.Path(exists=True, resolve_path=True),
          metavar='TRAINING_SET_FOLDER')
@option('--validation-set', '-a',
        type=click.Path(exists=True, resolve_path=True),
        callback=path_or_none,
        metavar='FOLDER',
        help="Either a folder of validation pages or a JSON file made manually by FathomFox's Vectorizer. Validation pages are used to avoid overfitting.")
@option('--ruleset', '-r',
        type=click.Path(exists=True, dir_okay=False, resolve_path=True),
        callback=path_or_none,
        help='The rulesets.js file containing your rules. The file must have no imports except from fathom-web, so pre-bundle if necessary.')
@option('--trainee',
        type=str,
        metavar='ID',
        help='The trainee ID of the ruleset you want to train. Usually, this is the same as the type you are training for.')
@option('--training-cache',
        type=click.Path(dir_okay=False, resolve_path=True),
        callback=path_or_none,
        help='Where to cache training vectors to speed future training runs. Any existing file will be overwritten. [default: vectors/training_yourTraineeId.json next to your ruleset]')
@option('--validation-cache',
        type=click.Path(dir_okay=False, resolve_path=True),
        callback=path_or_none,
        help='Where to cache validation vectors to speed future training runs. Any existing file will be overwritten. [default: vectors/validation_yourTraineeId.json next to your ruleset]')
@option('--show-browser',
        default=False,
        is_flag=True,
        help='Show browser window while vectorizing. (Browser runs in headless mode by default.)')
@option('--stop-early', '-s',
        default=False,
        is_flag=True,
        help='Stop 1 iteration before validation loss begins to rise, to avoid overfitting. Before using this, check Tensorboard graphs to make sure validation loss is monotonically decreasing.')
@option('--learning-rate', '-l',
        default=1.0,
        show_default=True,
        help='The learning rate to start from')
@option('--iterations', '-i',
        default=1000,
        show_default=True,
        help='The number of training iterations to run through')
@option('--pos-weight', '-p',
        type=float,
        default=None,
        show_default=True,
        help='The weighting factor given to all positive samples by the loss function. See: https://pytorch.org/docs/stable/nn.html#bcewithlogitsloss')
@option('--comment', '-c',
        default='',
        help='Additional comment to append to the Tensorboard run name, for display in the web UI')
@option('--quiet', '-q',
        default=False,
        is_flag=True,
        help='Hide per-tag diagnostics that may help with ruleset debugging.')
@option('--confidence-threshold', '-t',
        default=0.5,
        show_default=True,
        help='Threshold at which a sample is considered positive. Higher values decrease false positives and increase false negatives.')
@option('layers', '--layer', '-y',
        type=int,
        multiple=True,
        help='Add a hidden layer of the given size. You can specify more than one, and they will be connected in the given order. EXPERIMENTAL.')
@option('--exclude', '-x',
        type=str,
        multiple=True,
        help='Exclude a rule while training. This helps with before-and-after tests to see if a rule is effective.')
def main(training_set, validation_set, ruleset, trainee, training_cache, validation_cache, show_browser, stop_early, learning_rate, iterations, pos_weight, comment, quiet, confidence_threshold, layers, exclude):
    """Compute optimal numerical parameters for a Fathom ruleset.

    There are a lot of options, but the usual invocation is something like...

      fathom-train samples/training --validation-set samples/validation --stop-early --ruleset rulesets.js --trainee new

    TRAINING_SET_FOLDER is a directory of labeled training pages. It can also
    be, for backward compatibility, a JSON file of vectors from FathomFox's
    Vectorizer.

    To see graphs of the results, install TensorBoard, then run this:
    tensorboard --logdir runs/. These will tell you whether you need to adjust
    the --learning-rate.

    Some vocab used in the output messages:

      target -- A "right answer" DOM node, one that should be recognized

      candidate -- Any node (target or not) brought into the ruleset, by a
      dom() call, for consideration

      negative sample -- A sample with no intended target nodes, used to bait
      the recognizer into a false-positive choice

    """
    training_set = Path(training_set)

    # If they pass in a dir for either the training or validation sets, we need
    # a ruleset and a trainee for vectorizing:
    if (validation_set and validation_set.is_dir()) or training_set.is_dir():
        if not ruleset:
            raise BadOptionUsage('ruleset', 'A --ruleset file must be specified when TRAINING_SET or --validation-set are passed a directory.')
        if not trainee:
            raise BadOptionUsage('trainee', 'A --trainee ID must be specified when TRAINING_SET or --validation-set are passed a directory.')

    with open(make_or_read_vectors(ruleset,
                                   trainee,
                                   training_set,
                                   training_cache,
                                   show_browser,
                                   'training'),
              encoding='utf-8') as training_file:
        training_data = exclude_features(exclude, load(training_file))
    training_pages = training_data['pages']
    x, y, num_yes = tensors_from(training_pages, shuffle=True)

    if validation_set:
        with open(make_or_read_vectors(ruleset,
                                       trainee,
                                       validation_set,
                                       validation_cache,
                                       show_browser,
                                       'validation'),
                  encoding='utf-8') as validation_file:
            validation_pages = exclude_features(exclude, load(validation_file))['pages']
        validation_ins, validation_outs, validation_yes = tensors_from(validation_pages)
        validation_arg = validation_ins, validation_outs
    else:
        validation_arg = None

    layers = list(layers)  # Comes in as tuple
    full_comment = '.LR={l},i={i}{c}'.format(
        l=learning_rate,
        i=iterations,
        c=(',' + comment) if comment else '')
    model = learn(learning_rate,
                  iterations,
                  x,
                  y,
                  confidence_threshold,
                  validation=validation_arg,
                  stop_early=stop_early,
                  run_comment=full_comment,
                  pos_weight=pos_weight,
                  layers=layers)

    print(pretty_coeffs(model, training_data['header']['featureNames']))
    accuracy, false_positives, false_negatives = accuracy_per_tag(y, model(x), confidence_threshold)
    print(pretty_accuracy(('  ' if validation_set else '') + 'Training accuracy per tag: ',
                          accuracy,
                          len(x),
                          false_positives,
                          false_negatives,
                          num_yes))
    if validation_set:
        accuracy, false_positives, false_negatives = accuracy_per_tag(validation_outs, model(validation_ins), confidence_threshold)
        print(pretty_accuracy('Validation accuracy per tag: ',
                              accuracy,
                              len(validation_ins),
                              false_positives,
                              false_negatives,
                              validation_yes))

    # Print timing information:
    if training_pages and 'time' in training_pages[0]:
        if validation_set and validation_pages and 'time' in validation_pages[0]:
            print(speed_readout(training_pages + validation_pages))
        else:
            print(speed_readout(training_pages))

    if not quiet:
        print('\nTraining per-tag results:')
        print_per_tag_report([per_tag_metrics(page, model, confidence_threshold) for page in training_pages])
        if validation_set:
            print('\nValidation per-tag results:')
            print_per_tag_report([per_tag_metrics(page, model, confidence_threshold) for page in validation_pages])
    # TODO: Print "8000 elements. 7900 successes. 50 false positive. 50 false negatives."
