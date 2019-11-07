"""Routines to do with calculating or reporting accuracy"""


from math import floor, sqrt

from click import style
import numpy as np
import torch

from .utils import tensor


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
    text = f'{ratio:.8f}'
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


def pretty_accuracy(description, accuracy, number_of_samples, false_positives=None, false_negatives=None, number_of_positives=None):
    ci_low, ci_high = confidence_interval(accuracy, number_of_samples)
    if false_positives is not None:
        false_positive_ratio = false_positives / number_of_samples
        false_negative_ratio = false_negatives / number_of_samples
        fp_ci_low, fp_ci_high = confidence_interval(false_positive_ratio, number_of_positives)
        fn_ci_low, fn_ci_high = confidence_interval(false_negative_ratio, number_of_samples - number_of_positives)
        falses = ('\n'
                  f'                         FP:  {false_positive_ratio:.5f}    95% CI: ({fp_ci_low:.5f}, {fp_ci_high:.5f})\n'
                  f'                         FN:  {false_negative_ratio:.5f}    95% CI: ({fn_ci_low:.5f}, {fn_ci_high:.5f})\n')
    else:
        falses = ''
    return f'{description} {accuracy:.5f}    95% CI: ({ci_low:.5f}, {ci_high:.5f}){falses}'
