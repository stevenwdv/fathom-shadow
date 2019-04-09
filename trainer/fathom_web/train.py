from json import load

from click import argument, command, File, option, progressbar
from tensorboardX import SummaryWriter
import torch
from torch.nn import Sequential, Linear, BCEWithLogitsLoss
from torch.optim import Adam


def tensor(some_list):
    """Cast a list to a tensor of the proper type for our problem."""
    return torch.tensor(some_list, dtype=torch.float)


def data_from_file(file):
    return load(file)


def tensors_from(pages):
    """Return (inputs, correct outputs, number of tags that are recognition targets)
    tuple of training tensors."""
    xs = []
    ys = []
    num_targets = 0
    for page in pages:
        for tag in page['nodes']:
            xs.append(tag['features'])
            ys.append([1 if tag['isTarget'] else 0])  # Tried 0.1 and 0.9 instead. Was much worse.
            if tag['isTarget']:
                num_targets += 1
    return tensor(xs), tensor(ys), num_targets


def learn(learning_rate, iterations, x, y, validation=None, run_comment=''):
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
    with progressbar(range(iterations)) as bar:
        for t in bar:
            y_pred = model(x)  # Make predictions.
            loss = loss_fn(y_pred, y)
            writer.add_scalar('loss', loss, t)
            if validation:
                writer.add_scalar('validation_loss', loss_fn(model(validation_ins), validation_outs), t)
            writer.add_scalar('training_accuracy_per_tag', accuracy_per_tag(model, x, y), t)
            optimizer.zero_grad()  # Zero the gradients.
            loss.backward()  # Compute gradients.
            optimizer.step()

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


def accuracy_per_page(model, pages, verbose=False):
    """Return the accuracy 0..1 of the model on a per-page basis, assuming the
    model is looking for the equivalent of Fathom's ``max(the type)``."""
    successes = 0
    for page in pages:
        if not page['nodes']:
            print('No candidate nodes for {}.'.format(page['filename']))
            continue
        predictions = []
        for tag in page['nodes']:
            prediction = model(tensor(tag['features'])).sigmoid().item()
            predictions.append({'prediction': prediction,
                                'isTarget': tag['isTarget']})
        predictions.sort(key=lambda x: x['prediction'], reverse=True)
        succeeded = predictions[0]['isTarget']
        if verbose:
            print('{success_or_failure} on {file}. Confidence: {confidence}'.format(
                    file=page['filename'],
                    confidence=predictions[0]['prediction'],
                    success_or_failure='Success' if succeeded else 'FAILURE'))
        if succeeded:
            successes += 1
        else:
            if verbose:
                for i, p in enumerate(predictions):
                    if p['isTarget']:
                        print('    First target at index {index}: {confidence}'.format(
                                index=i,
                                confidence=p['prediction']))
                        break
    return successes / len(pages)


def pretty_output(model, feature_names):
    """Format coefficient and bias numbers for easy pasting into JS."""
    dict_params = {}
    for name, param in model.named_parameters():
        dict_params[name] = param.data.tolist()
    pretty_coeffs = '\n        '.join("['{k}', {v}],".format(k=k, v=v) for k, v in zip(feature_names, dict_params['0.weight'][0]))
    return """Coeffs: [
        {coeffs}
    ]
Bias: {bias}""".format(coeffs=pretty_coeffs, bias=dict_params['0.bias'][0])


@command()
@argument('training_file',
          type=File('r'))
@option('validation_file', '-a',
        type=File('r'),
        help="A file of validation samples from FathomFox's Vectorizer, used to graph validation loss so you can see when you start to overfit")
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
def main(training_file, validation_file, learning_rate, iterations, comment, verbose):
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
    x, y, num_yes = tensors_from(training_data['pages'])
    if validation_file:
        validation_data = data_from_file(validation_file)
        validation_ins, validation_outs, _ = tensors_from(validation_data['pages'])
        validation_arg = validation_ins, validation_outs
    else:
        validation_arg = None
    model = learn(learning_rate, iterations, x, y, validation=validation_arg, run_comment=full_comment)
    print(pretty_output(model, training_data['header']['featureNames']))
    print('Training accuracy per tag:', accuracy_per_tag(model, x, y))
    if validation_file:
        print('Validation accuracy per tag:', accuracy_per_tag(model, validation_ins, validation_outs))
    print('Training accuracy per page:', accuracy_per_page(model, training_data['pages'], verbose=verbose))
    if validation_file:
        print('Validation accuracy per page:', accuracy_per_page(model, validation_data['pages'], verbose=verbose))
    # TODO: Print "8000 elements. 7900 successes. 50 false positive. 50 false negatives."
