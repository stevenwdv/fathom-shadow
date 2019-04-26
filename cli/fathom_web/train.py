from json import load
from math import floor, sqrt
from random import sample

from click import argument, command, File, option, progressbar, style
from tensorboardX import SummaryWriter
import torch
from torch.nn import Sequential, Linear, BCEWithLogitsLoss
from torch.optim import Adam


def tensor(some_list):
    """Cast a list to a tensor of the proper type for our problem."""
    return torch.tensor(some_list, dtype=torch.float)


def data_from_file(file):
    return load(file)


def tensors_from(pages, shuffle=False):
    """Return (inputs, correct outputs, number of tags that are recognition targets)
    tuple.

    Can also shuffle to improve training performance.

    """
    xs = []
    ys = []
    num_targets = 0
    maybe_shuffled_pages = sample(pages, len(pages)) if shuffle else pages
    for page in maybe_shuffled_pages:
        for tag in page['nodes']:
            xs.append(tag['features'])
            ys.append([1 if tag['isTarget'] else 0])  # Tried 0.1 and 0.9 instead. Was much worse.
            if tag['isTarget']:
                num_targets += 1
    return tensor(xs), tensor(ys), num_targets


def learn(learning_rate, iterations, x, y, validation=None, stop_early=False, run_comment=''):
    # Define a neural network using high-level modules.
    writer = SummaryWriter(comment=run_comment)
    model = Sequential(
        Linear(len(x[0]), len(y[0]), bias=True)  # n inputs -> 1 output
    )
    loss_fn = BCEWithLogitsLoss(reduction='sum')  # reduction=mean converges slower.
    # TODO: Add an option to twiddle pos_weight, which lets us trade off precision and recall. Maybe also graph using add_pr_curve(), which can show how that tradeoff is going.
    optimizer = Adam(model.parameters(),lr=learning_rate)

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
                        model.load_state_dict(previous_model)
                        break
                    else:
                        previous_validation_loss = validation_loss
                        previous_model = model.state_dict()
                writer.add_scalar('validation_loss', validation_loss, t)
            writer.add_scalar('training_accuracy_per_tag', accuracy_per_tag(model, x, y), t)
            optimizer.zero_grad()  # Zero the gradients.
            loss.backward()  # Compute gradients.
            optimizer.step()
    if stopped_early:
        print('Stopping early at iteration {t}, just before validation error rose.'.format(t=t))

    # Horizontal axis is what confidence. Vertical is how many samples were that confidence.
    writer.add_histogram('confidence', confidences(model, x), t)
    writer.close()
    return model


def accuracy_per_tag(model, x, y):
    """Return the accuracy 0..1 of the model on a per-tag basis, given input
    and correct output tensors."""
    successes = 0
    for (i, input) in enumerate(x):
        if abs(model(input).sigmoid().item() - y[i].item()) < .5:
            successes += 1
    return successes / len(x)


def confidences(model, x):
    return model(x).sigmoid()


def confidence_interval(success_ratio, number_of_samples):
    """Return a 95% binomial proportion confidence interval."""
    z_for_95_percent = 1.96
    addend = z_for_95_percent * sqrt(success_ratio * (1 - success_ratio) / number_of_samples)
    return max(0., success_ratio - addend), min(1., success_ratio + addend)


def first_target_prediction(predictions):
    for i, p in enumerate(predictions):
        if p['isTarget']:
            return i, p['prediction']
    return None


def success_on_page(model, page):
    """Return whether the model succeeded on the given page, along with lots of
    metadata to help diagnose how the model is doing.

    Return a tuple of...

    * color_scheme: 'good', 'bad', or 'medium', reflecting the goodness of the
      result
    * is_success: Whether the model should be said to have succeeded on the
      page
    * reason: Explanation of why a page succeeded or failed
    * confidence: The score of the top-scoring node. None if no nodes at all
      were extracted from the page.
    * first_target: If the top-scoring node is not a target, a tuple of (the
      index of the highest-scoring actual target on the stack (so we can see
      how far off we were), the score of that target). If the top-scoring node
      is a target or no candidates were extracted at all, None.

    """
    predictions = [{'prediction': model(tensor(tag['features'])).sigmoid().item(),
                    'isTarget': tag['isTarget']} for tag in page['nodes']]
    predictions.sort(key=lambda x: x['prediction'], reverse=True)

    first_target = None
    is_success = False
    reason = ''
    if predictions:  # We found a candidate...
        candidate = predictions[0]
        confidence = predictions[0]['prediction']
        if candidate['isTarget']:  # ...and our top one is a target.
            is_success = True
            if candidate['prediction'] >= .5:
                color_scheme = 'good'
            else:  # a low-confidence success
                color_scheme = 'medium'
        else:  # Our surest candidate isn't a target.
            first_target = first_target_prediction(predictions)
            if first_target:  # There was a target to hit.
                color_scheme = 'bad'
                reason = ' Highest-scoring element was a wrong choice.'
            else:  # There were no targets.
                if candidate['prediction'] < .5:
                    color_scheme = 'good'
                    is_success = True
                    reason = ' No target nodes. Assumed negative sample.'
                else:  # a high-confidence non-target
                    color_scheme = 'bad'
                    reason = ' There were no right choices, but highest-scorer had high confidence anyway.'
    else:  # We did not find a candidate.
        confidence = None
        color_scheme = 'good'
        is_success = True
        reason = ' Assumed negative sample.'
    return color_scheme, is_success, reason, confidence, first_target


def thermometer(ratio):
    """Return a graphical representation of a decimal with linear scale."""
    text = '{ratio:.8f}'.format(ratio=ratio)
    tenth = min(floor(ratio * 10), 9)  # bucket to [0..9]
    return (style(text[:tenth], bg='white', fg='black') +
            style(text[tenth:], bg='bright_white', fg='black'))


def accuracy_per_page(model, pages):
    """Return the accuracy 0..1 of the model on a per-page basis. A page is
    considered a success if...

        * The top-scoring node found is a target
        * No candidate scoring >0.5 is found and there are no targets labeled

    We may later tighten this to require that all targets are found >0.5.

    """
    if not pages:
        return 1  # just to keep max() from crashing
    successes = 0
    COLOR_SCHEMES = {'good': {'fg': 'black', 'bg': 'bright_green'},
                     'medium': {'fg': 'black', 'bg': 'bright_yellow'},
                     'bad': {'fg': 'white', 'bg': 'red', 'bold': True}}
    report_lines = []
    max_filename_len = max(len(page['filename']) for page in pages)
    for page in pages:
        color_scheme, is_success, reason, confidence, first_target = success_on_page(model, page)
        if is_success:
            successes += 1

        # Build pretty report:
        report_lines.append(('{success_or_failure} on {file: >' + str(max_filename_len) + '}. Confidence: {confidence}{reason}').format(
                file=page['filename'],
                confidence=thermometer(confidence) if confidence is not None else 'no candidate nodes.',
                reason=reason,
                success_or_failure=style(' success ' if is_success else ' failure ', **COLOR_SCHEMES[color_scheme])))
        if first_target:
            index, score = first_target
            report_lines.append('    First target at index {index}: {confidence}'.format(
                    index=index,
                    confidence=thermometer(score)))
    return (successes / len(pages)), '\n'.join(report_lines)


def pretty_coeffs(model, feature_names):
    """Format coefficient and bias numbers for easy pasting into JS."""
    dict_params = {}
    for name, param in model.named_parameters():
        dict_params[name] = param.data.tolist()
    pretty = '\n        '.join("['{k}', {v}],".format(k=k, v=v) for k, v in zip(feature_names, dict_params['0.weight'][0]))
    return """Coeffs: [
        {coeffs}
    ]
Bias: {bias}""".format(coeffs=pretty, bias=dict_params['0.bias'][0])


def pretty_accuracy(description, accuracy, number_of_samples):
    ci_low, ci_high = confidence_interval(accuracy, number_of_samples)
    return '{description} {accuracy:.5f}    95% CI: ({ci_low:.5f}, {ci_high:.5f})'.format(description=description, accuracy=accuracy, ci_low=ci_low, ci_high=ci_high)


@command()
@argument('training_file',
          type=File('r'))
@option('validation_file', '-a',
        type=File('r'),
        help="A file of validation samples from FathomFox's Vectorizer, used to graph validation loss so you can see when you start to overfit")
@option('--stop-early', '-s',
        default=False,
        is_flag=True,
        help='Stop 1 iteration before validation loss begins to rise, to avoid overfitting. Before using this, make sure validation loss is monotonically decreasing.')
@option('--learning-rate', '-l',
        default=1.0,
        show_default=True,
        help='The learning rate to start from')
@option('--iterations', '-i',
        default=1000,
        show_default=True,
        help='The number of training iterations to run through')
@option('--comment', '-c',
        default='',
        help='Additional comment to append to the Tensorboard run name, for display in the web UI')
@option('--verbose', '-v',
        default=False,
        is_flag=True,
        help='Show additional diagnostics that may help with ruleset debugging')
def main(training_file, validation_file, stop_early, learning_rate, iterations, comment, verbose):
    """Compute optimal coefficients for a Fathom ruleset, based on a set of
    labeled pages exported by the FathomFox Vectorizer.

    To see graphs of the results, install TensorBoard, then run this:
    tensorboard --logdir runs/.

    """
    full_comment = '.LR={l},i={i}{c}'.format(
            l=learning_rate,
            i=iterations,
            c=(',' + comment) if comment else '')
    training_data = data_from_file(training_file)
    x, y, num_yes = tensors_from(training_data['pages'], shuffle=True)
    if validation_file:
        validation_data = data_from_file(validation_file)
        validation_ins, validation_outs, _ = tensors_from(validation_data['pages'])
        validation_arg = validation_ins, validation_outs
    else:
        validation_arg = None
    model = learn(learning_rate, iterations, x, y, validation=validation_arg, stop_early=stop_early, run_comment=full_comment)
    print(pretty_coeffs(model, training_data['header']['featureNames']))
    accuracy = accuracy_per_tag(model, x, y)
    print(pretty_accuracy(('  ' if validation_file else '') + 'Training accuracy per tag: ', accuracy, len(x)))
    if validation_file:
        accuracy = accuracy_per_tag(model, validation_ins, validation_outs)
        print(pretty_accuracy('Validation accuracy per tag: ', accuracy, len(validation_ins)))
    accuracy, training_report = accuracy_per_page(model, training_data['pages'])
    print(pretty_accuracy(('  ' if validation_file else '') + 'Training accuracy per page:', accuracy, len(training_data['pages'])))
    if validation_file:
        accuracy, validation_report = accuracy_per_page(model, validation_data['pages'])
        print(pretty_accuracy('Validation accuracy per page:', accuracy, len(validation_data['pages'])))

    if verbose:
        print('\nTraining per-page results:\n', training_report, sep='')
        if validation_file:
            print('\nValidation per-page results:\n', validation_report, sep='')
    # TODO: Print "8000 elements. 7900 successes. 50 false positive. 50 false negatives."
