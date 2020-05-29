"""Routines to do with calculating or reporting accuracy"""


from itertools import repeat
from math import floor, inf, nan, sqrt

from click import get_terminal_size, style
import torch

from .utils import tensors_from, fit_unicode


def accuracy_per_tag(y, y_pred, cutoff, num_prunes):
    """Return the accuracy 0..1 of the model on a per-tag basis, given the
    correct output tensors and the prediction tensors from the model for the
    same samples.

    :arg num_prunes: The number of targets that didn't get matched by a dom()
        call: FNs, inevitably

    """
    # Use `torch.no_grad()` so the sigmoid on y_pred is not tracked by pytorch's autograd
    with torch.no_grad():
        # We turn our tensors into 1-D numpy arrays because its methods are faster
        y = y.numpy().flatten()
        y_pred_confidence = y_pred.sigmoid().numpy().flatten()

        predicted_positives = y_pred_confidence >= cutoff
        successes = (predicted_positives == y).sum()
        false_positives = (predicted_positives & (y == 0)).sum()
        number_of_tags = len(y) + num_prunes
        false_negatives = number_of_tags - successes - false_positives + num_prunes
        return (successes / number_of_tags), false_positives, false_negatives


def per_tag_metrics(page, model, cutoff):
    """Return the per-tag numbers to be templated into a human-readable report
    by ``print_per_tag_report``."""
    # Get scores for all tags:
    inputs, correct_outputs, _, num_prunes = tensors_from([page])
    with torch.no_grad():
        try:
            scores = model(inputs).sigmoid().numpy().flatten().tolist()
        except RuntimeError:  # TODO: Figure out why we're having a mismatched-matrix-size error on pages with no tags, and do something that doesn't require a branch.
            scores = []
    # All the prematurely pruned nodes are at the end of the vectorized node
    # list, so we can just pad out the scores with zeroes, and they'll align:
    scores.extend(repeat(0, num_prunes))
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
            tag_metric['score'] = 'pruned' if tag.get('pruned') else score
            tag_metric['markup'] = tag.get('markup', 'Use a newer FathomFox to see markup.')
            tag_metrics.append(tag_metric)
        else:  # not is_target and not is_error: TNs
            true_negatives += 1
    return {'filename': page['filename'],
            'tags': tag_metrics,
            'true_negative_count': true_negatives}


def max_default(iterable, default):
    try:
        return max(iterable)
    except ValueError:  # empty iterable
        return default


FAT_COLORS = {'good': {'fg': 'black', 'bg': 'bright_green', 'bold': True},
              'medium': {'fg': 'black', 'bg': 'bright_yellow'},
              'bad': {'fg': 'white', 'bg': 'red', 'bold': True}}


def print_per_tag_report(metricses):
    """Given a list of results from multiple ``per_tag_metrics()`` calls,
    return a human-readable report."""
    THIN_COLORS = {True: {'fg': 'green'},
                   False: {'fg': 'red'}}

    max_filename_len = max(len(metrics['filename']) for metrics in metricses)

    max_tag_len = max_default((len(tag['markup']) for metrics in metricses for tag in metrics['tags']),
                              inf)
    template_width_minus_tag = max_filename_len + 2 + 3 + 2 + 3 + 10
    tag_max_width = min(get_terminal_size()[0] - template_width_minus_tag, max_tag_len)

    template = '{file_style}{file: >' + str(max_filename_len) + '}{style_reset}  {tag_style}{tag_and_padding}   {error_type: >2}{style_reset}   {score}'
    style_reset = style('', reset=True)
    for metrics in sorted(metricses, key=lambda m: m['filename']):
        first = True
        true_negative_count = metrics['true_negative_count']
        all_right = not any(t['error_type'] for t in metrics['tags'])
        any_right = not all(t['error_type'] for t in metrics['tags']) or true_negative_count
        file_color = 'good' if all_right else ('medium' if any_right else 'bad')
        for tag in metrics['tags']:
            print(template.format(
                file=metrics['filename'] if first else '',
                file_style=style('', **FAT_COLORS[file_color], reset=False),
                style_reset=style_reset,
                tag_and_padding=fit_unicode(tag['markup'], tag_max_width),
                tag_style=style('', **THIN_COLORS[not bool(tag['error_type'])], reset=False),
                error_type=tag['error_type'],
                score='pruned' if tag['score'] == 'pruned' else thermometer(tag['score'])))
            first = False
        if first:
            # There were no targets and no errors, so we didn't print tags.
            print(template.format(
                file=metrics['filename'],
                file_style=style('', **FAT_COLORS['good'], reset=False),
                style_reset=style_reset,
                tag_and_padding=fit_unicode('No targets found.', tag_max_width),
                tag_style=style('', fg='green', reset=False),
                error_type='',
                score=''))
        else:
            # We printed some tags. Also show the TNs so we get credit for them.
            if true_negative_count:
                print(template.format(
                    file='',
                    file_style=style('', **FAT_COLORS[file_color], reset=False),
                    style_reset=style_reset,
                    tag_and_padding=fit_unicode(
                        f'   ...and {true_negative_count} correct negative'
                        + ('s' if true_negative_count > 1 else ''),
                        tag_max_width),
                    tag_style=style('', fg='green', reset=False),
                    error_type='',
                    score=''))


def confidence_interval(success_ratio, number_of_samples):
    """Return a 95% binomial proportion confidence interval."""
    z_for_95_percent = 1.96
    if number_of_samples:
        addend = z_for_95_percent * sqrt(success_ratio * (1 - success_ratio) / number_of_samples)
    else:
        addend = nan
    # max() and min() will pick the other arg if one of them is nan, giving us
    # the most conservative possible confidence interval. For example, if there
    # aren't any TPs to get wrong, we can't very well say anything about the FN
    # rate.
    return max(0., success_ratio - addend), min(1., success_ratio + addend)


def thermometer(ratio):
    """Return a graphical representation of a decimal with linear scale."""
    text = f'{ratio:.8f}'
    tenth = min(floor(ratio * 10), 9)  # bucket to [0..9]
    return (style(text[:tenth], bg='white', fg='black') +
            style(text[tenth:], bg='bright_white', fg='black'))


def pretty_accuracy(description, accuracy, number_of_samples, false_positives, false_negatives, positives):
    """Return a big printable block of numbers describing the accuracy and
    error bars of a model.

    :arg description: What kind of set this is: "Validation", "Training", etc.
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
    negatives = number_of_samples - positives
    # Think of this as the ratio of negatives we got wrong. If there were no
    # negatives, we can't have got any of them wrong:
    false_positive_rate = (false_positives / negatives) if negatives else 0
    false_negative_rate = (false_negatives / positives) if positives else 0
    fpr_ci_low, fpr_ci_high = confidence_interval(false_positive_rate, negatives)
    fnr_ci_low, fnr_ci_high = confidence_interval(false_negative_rate, positives)
    # https://en.wikipedia.org/wiki/Precision_and_recall#/media/File:Precisionrecall.svg
    # really helps when thinking about the Venn diagrams of these values.
    true_positives = positives - false_negatives
    true_negatives = negatives - false_positives
    if not true_positives + false_positives:
        # If the denominator is 0, the numerator is too, so we didn't get any
        # right.
        precision = 0
    else:
        precision = true_positives / (true_positives + false_positives)
    # Recall is the same as the true positive rate:
    recall = 1 - false_negative_rate
    mcc_denom = sqrt((true_positives + false_positives) * (true_positives + false_negatives) * (true_negatives + false_positives) * (true_negatives + false_negatives))
    if mcc_denom:
        mcc = (true_positives * true_negatives - false_positives * false_negatives) / mcc_denom
    else:
        # I figure "same as chance" value 0 is the worst you can get. Wikipedia
        # agrees.
        mcc = 0
    return ('\n'
            f'{description: >10} precision: {precision:.4f}   Recall: {recall:.4f}                           Predicted\n'
            f'            Accuracy: {accuracy:.4f}   95% CI: ({ci_low:.4f}, {ci_high:.4f})        ╭───┬── + ───┬── - ───╮\n'
            f'                 FPR: {false_positive_rate:.4f}   95% CI: ({fpr_ci_low:.4f}, {fpr_ci_high:.4f})   True │ + │ {true_positives: >6} │ {false_negatives: >6} │\n'
            f'                 FNR: {false_negative_rate:.4f}   95% CI: ({fnr_ci_low:.4f}, {fnr_ci_high:.4f})        │ - │ {false_positives: >6} │ {true_negatives: >6} │\n'
            f'                 MCC: {mcc:.4f}                                   ╰───┴────────┴────────╯')
