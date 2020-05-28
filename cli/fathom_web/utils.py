"""Additional factored-up routines for which no clear pattern of organization
has yet emerged"""

import io
from os import walk
from pathlib import Path
from random import sample
from unicodedata import east_asian_width

from more_itertools import ilen, pairwise
from numpy import array, histogram
from sklearn.preprocessing import minmax_scale
import torch
from torch.nn import Sequential, Linear, ReLU


def tensor(some_list):
    """Cast a list to a tensor of the proper type for our problem."""
    return torch.tensor(some_list, dtype=torch.float)


def tensors_from(pages, shuffle=False):
    """Return (inputs, correct outputs, number of tags that are recognition
    targets, number of tags that were prematurely pruned) tuple.

    Can also shuffle to improve training performance.

    """
    xs = []
    ys = []
    num_targets = num_prunes = 0
    maybe_shuffled_pages = sample(pages, len(pages)) if shuffle else pages
    for page in maybe_shuffled_pages:
        for tag in page['nodes']:
            if tag.get('pruned'):
                num_prunes += 1
            else:
                xs.append(tag['features'])
                ys.append([1 if tag['isTarget'] else 0])  # Tried 0.1 and 0.9 instead. Was much worse.
            if tag['isTarget']:
                num_targets += 1
    return tensor(xs), tensor(ys), num_targets, num_prunes


def classifier(num_inputs, num_outputs, hidden_layer_sizes=None):
    """Return a new model of the type Fathom uses.

    At present, this is a linear binary classifier modeled as a perceptron.

    :arg num_inputs: The number of input nodes (layer 0 of the net)
    :arg num_outputs: The number of outputs. So far, always 1 since it's a
        binary classifier. We may expand to multiclass someday, however.
    :arg hidden_layer_sizes: For each hidden layer, the number of nodes in it.
        Fully-connectedness is assumed.

    """
    if hidden_layer_sizes is None:
        hidden_layer_sizes = []
    sizes = [num_inputs] + hidden_layer_sizes

    layers = []
    for i, o in pairwise(sizes):
        layers.append(Linear(i, o, bias=True))
        layers.append(ReLU())  # Sigmoid does worse, Tanh about the same.
    layers.append(Linear(sizes[-1], num_outputs, bias=True))

    return Sequential(*layers)


def mini_histogram(data):
    """Return a histogram of a list of numbers with min and max numbers
    labeled."""
    chars = ' ▁▂▃▄▅▆▇█'
    data_array = array(data)
    counts, _ = histogram(data_array, bins=10)
    indices = minmax_scale(counts, feature_range=(0, 8)).round()
    chart = ''.join(chars[int(i)] for i in indices)
    return '{min} |{chart}| {max}'.format(min=data_array.min(),
                                          chart=chart,
                                          max=data_array.max())


def speed_readout(pages):
    """Return human-readable metrics on ruleset-running speed based on
    benchmarks taken by the Vectorizer."""
    num_unpruned_nodes = sum(ilen(n for n in p['nodes'] if not n.get('pruned')) for p in pages)
    average = sum(p['time'] for p in pages) / num_unpruned_nodes
    histogram = mini_histogram([p['time'] for p in pages])
    return f'\nTime per page (ms): {histogram}    Average per tag: {average:.0f}'


def fit_unicode(string, width):
    """Truncate or pad a string to width, taking into account that some unicode
    chars are double-width."""
    width_so_far = 0
    for num_chars, char in enumerate(string, start=1):
        width_so_far += 2 if east_asian_width(char) == 'W' else 1
        if width_so_far == width:
            break
        elif width_so_far > width:
            num_chars -= 1
            width_so_far -= 2
            break
    return string[:num_chars] + (' ' * (width - width_so_far))


def samples_from_dir(in_dir):
    """Return an iterable of Paths to samples found in ``in_dir``,
    recursively."""
    for dir_path, dirs, files in walk(in_dir):
        try:
            # Skip resources/ folders. Sometimes they contain .html files, and
            # those aren't samples.
            dirs.remove('resources')
        except ValueError:
            pass
        yield from (Path(dir_path) / file for file in files
                    if file.endswith('.html'))


def read_chunks(file, size=io.DEFAULT_BUFFER_SIZE):
    """Yield pieces of data from a file-like object until EOF."""
    while True:
        chunk = file.read(size)
        if not chunk:
            break
        yield chunk


def path_or_none(ctx, param, value):
    return None if value is None else Path(value)
