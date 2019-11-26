"""Additional factored-up routines for which no clear pattern of organization
has yet emerged"""


from random import sample
from time import sleep

import torch
from torch.nn import Sequential, Linear


def tensor(some_list):
    """Cast a list to a tensor of the proper type for our problem."""
    return torch.tensor(some_list, dtype=torch.float)


def tensors_from(pages, shuffle=False):
    """Return (inputs, correct outputs, number of tags that are recognition
    targets) tuple.

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


def classifier(num_inputs, num_outputs):
    """Return a new model of the type Fathom uses.

    At present, this is a linear binary classifier modeled as a perceptron.

    :arg num_inputs: The number of input nodes (layer 0 of the net)
    :arg num_outputs: The number of outputs. So far, always 1 since it's a
        binary classifier. We may expand to multiclass someday, however.

    """
    return Sequential(
        Linear(num_inputs, num_outputs, bias=True)
    )


def wait_for_function(function, error, max_tries):
    """Try to execute a function some number of times before raising an error

    :arg function: A function that likely has some time dependency and you want
        to try executing it multiple times to wait for the time dependency to
        resolve.
    :arg error: An exception to raise if the function fails too many times.
    :arg max_tries: The number of time to try the function before raising the
        error.
    """
    for _ in range(max_tries):
        try:
            return function()
        except:
            sleep(1)
    else:
        raise error
