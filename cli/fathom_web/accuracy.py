"""Routines to do with calculating or reporting accuracy"""


from math import floor, sqrt

from click import style
import numpy as np
import torch

from .utils import tensors_from


def accuracy_per_tag(y, y_pred):
    """Return the accuracy 0..1 of the model on a per-tag basis, given the
    correct output tensors and the prediction tensors from the model for the
    same samples."""
    # Use `torch.no_grad()` so the sigmoid on y_pred is not tracked by pytorch's autograd
    with torch.no_grad():
        # We turn our tensors into 1-D numpy arrays because its methods are faster
        y = y.numpy().flatten()
        y_pred_confidence = y_pred.sigmoid().numpy().flatten()

        absolute_confidence_error = np.abs(y_pred_confidence - y)
        successes = (absolute_confidence_error < 0.5).sum()
        false_negatives = ((absolute_confidence_error >= 0.5) & (y == 1)).sum()
        number_of_tags = len(y)
        false_positives = number_of_tags - successes - false_negatives
        return (successes / number_of_tags), false_positives, false_negatives


def per_tag_metrics(page, model):
    """Return the per-tag numbers to be templated into a human-readable report
    by ``print_per_tag_report``."""
    # Get scores for all tags:
    inputs, correct_outputs, _ = tensors_from([page])
    with torch.no_grad():
        try:
            scores = model(inputs).sigmoid().numpy().flatten()
        except RuntimeError:  # TODO: Figure out why we're having a mismatched-matrix-size error on pages with no tags, and do something that doesn't require a branch.
            scores = []

    cutoff = 0.5  # confidence cutoff
    true_negatives = 0
    tag_metrics = []
    for tag, score in zip(page['nodes'], scores):
        tag_metric = {}  # {filename: '123.html', markup: '<input id=', error_type='FP'|'FN'|'', score: 0.534876}
        is_target = tag['isTarget']
        predicted = score >= cutoff
        is_error = is_target ^ predicted
        if is_target or is_error:  # Otherwise, it's too boring to print.
            if not is_target and predicted:
                tag_metric['error_type'] = 'FP'
            elif is_target and not predicted:
                tag_metric['error_type'] = 'FN'
            elif is_target and predicted:
                tag_metric['error_type'] = ''
            tag_metric['score'] = score
            tag_metric['markup'] = tag.get('markup', 'Use a newer FathomFox to see markup.')
            tag_metrics.append(tag_metric)
        else:  # not is_target and not is_error: TNs
            true_negatives += 1
    return {'filename': page['filename'],
            'tags': tag_metrics,
            'true_negative_count': true_negatives}


def print_per_tag_report(metricses):
    """Given a list of results from multiple ``per_tag_metrics()`` calls,
    return a human-readable report."""
    FAT_COLORS = {'good': {'fg': 'black', 'bg': 'bright_green', 'bold': True},
                  'medium': {'fg': 'black', 'bg': 'bright_yellow'},
                  'bad': {'fg': 'white', 'bg': 'red', 'bold': True}}
    THIN_COLORS = {True: {'fg': 'green'},
                   False: {'fg': 'red'}}
    max_filename_len = max(len(metrics['filename']) for metrics in metricses)
    template = '{file_style}{file: >' + str(max_filename_len) + '}{style_reset}  {tag_style}{tag: <34}   {error_type: >2}{style_reset}   {score}'
    style_reset = style('', reset=True)
    for metrics in metricses:
        first = True
        all_right = not any(t['error_type'] for t in metrics['tags'])
        any_right = not all(t['error_type'] for t in metrics['tags'])
        file_color = 'good' if all_right else ('medium' if any_right else 'bad')
        for tag in metrics['tags']:
            print(template.format(
                file=metrics['filename'] if first else '',
                file_style=style('', **FAT_COLORS[file_color], reset=False),
                style_reset=style_reset,
                tag=tag['markup'],
                tag_style=style('', **THIN_COLORS[not bool(tag['error_type'])], reset=False),
                error_type=tag['error_type'],
                score=thermometer(tag['score'])))
            first = False
        if first:
            # There were no targets and no errors, so we didn't print tags.
            print(template.format(
                file=metrics['filename'],
                file_style=style('', **FAT_COLORS['good'], reset=False),
                style_reset=style_reset,
                tag='No targets found.',
                tag_style=style('', fg='green', reset=False),
                error_type='',
                score=''))


def confidence_interval(success_ratio, number_of_samples):
    """Return a 95% binomial proportion confidence interval."""
    z_for_95_percent = 1.96
    addend = z_for_95_percent * sqrt(success_ratio * (1 - success_ratio) / number_of_samples)
    return max(0., success_ratio - addend), min(1., success_ratio + addend)


def thermometer(ratio):
    """Return a graphical representation of a decimal with linear scale."""
    text = f'{ratio:.8f}'
    tenth = min(floor(ratio * 10), 9)  # bucket to [0..9]
    return (style(text[:tenth], bg='white', fg='black') +
            style(text[tenth:], bg='bright_white', fg='black'))


def pretty_accuracy(description, accuracy, number_of_samples, false_positives=None, false_negatives=None, positives=None):
    """Return a big printable block of numbers describing the accuracy and
    error bars of a model.

    :arg accuracy: The accuracy of the model, expressed as a ratio 0..1
    :arg number_of_samples: The number of tags considered while training or
        testing the model
    :arg false_positives: The number of positives the model yielded that should
        have been negative
    :arg false_negatives: The number of negatives the model yielded that should
        have been positive
    :arg positives: The number of real positive tags in the corpus

    """
    ci_low, ci_high = confidence_interval(accuracy, number_of_samples)
    if false_positives is not None:
        false_positive_ratio = false_positives / number_of_samples
        false_negative_ratio = false_negatives / number_of_samples
        fp_ci_low, fp_ci_high = confidence_interval(false_positive_ratio, positives)
        fn_ci_low, fn_ci_high = confidence_interval(false_negative_ratio, number_of_samples - positives)
        # https://en.wikipedia.org/wiki/Precision_and_recall#/media/File:Precisionrecall.svg
        # really helps when thinking about the Venn diagrams of these values.
        true_positives = positives - false_negatives
        precision = true_positives / (true_positives + false_positives)
        recall = true_positives / positives
        falses = ('\n'
                  f'                         FP:  {false_positive_ratio:.5f}    95% CI: ({fp_ci_low:.5f}, {fp_ci_high:.5f})\n'
                  f'                         FN:  {false_negative_ratio:.5f}    95% CI: ({fn_ci_low:.5f}, {fn_ci_high:.5f})\n'
                  f'                  Precision:  {precision:.5f}    Recall: {recall:.5f}\n')
    else:
        falses = ''
    return f'{description} {accuracy:.5f}    95% CI: ({ci_low:.5f}, {ci_high:.5f}){falses}'
