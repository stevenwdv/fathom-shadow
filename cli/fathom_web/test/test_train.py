import os

from click.testing import CliRunner

from ..commands.train import exclude_indices, train, find_optimal_cutoff, single_cutoff
from ..utils import tensor


def test_exclude_indices():
    assert exclude_indices([0, 2, 3], ['a', 'b', 'c', 'd', 'e', 'f']) == ['b', 'e', 'f']  # omit first, last, and some consecutive
    assert exclude_indices([1], ['a', 'b', 'c', 'd']) == ['a', 'c', 'd']  # leave ends alone
    assert exclude_indices([], ['a', 'b', 'c']) == ['a', 'b', 'c']  # do nothing
    assert exclude_indices([0], ['a']) == []  # omit everything


def test_auto_vectorization_smoke(tmp_path):
    """Make sure we get through auto-vectorization of at least the training
    set."""
    test_dir = os.path.dirname(os.path.abspath(__file__))

    runner = CliRunner()
    result = runner.invoke(
        train,
        [
            f'{test_dir}/resources/train/',
            '--ruleset',
            f'{test_dir}/resources/train/vectorize_ruleset.js',
            '--trainee',
            'secret',
            '--training-cache',
            f'{tmp_path.as_posix()}/training_vectors.json',
        ]
    )
    assert result.exit_code == 0
    assert (tmp_path / 'training_vectors.json').exists()


def test_find_optimal_cutoff():
    y_pred = tensor([-2.1605, -0.5696, 0.4886, 0.8633, -1.3479, -0.5813, -0.5696, 0.5696, -0.5950, -0.5696])
    y_pred_confidence = y_pred.sigmoid().numpy().flatten()
    # [0.1033541  0.3613291  0.6197766  0.70334965 0.20621389 0.35863352, 0.3613291  0.63867086 0.35548845 0.3613291 ]
    y = tensor([0., 0., 1., 1., 0., 0., 0., 1., 0., 0.])

    optimal_cutoff = find_optimal_cutoff(y, y_pred, num_prunes=0)
    assert optimal_cutoff == 0.49


def test_find_optimal_cutoff_multiple_cutoffs():
    y_pred = tensor([-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.25, 2, 2.5])
    y_pred_confidence = y_pred.sigmoid().numpy().flatten()
    # [0.11920292 0.18242553 0.26894143 0.37754068 0.5  0.62245935, 0.7310586  0.7772999  0.880797   0.9241418 ]
    y = tensor([0., 1., 0., 1., 0., 1., 0., 1., 0., 1.])

    optimal_cutoff = find_optimal_cutoff(y, y_pred, num_prunes=0)
    assert optimal_cutoff == 0.56


def test_single_cutoff():
    cutoffs = [0.20, 0.30, 0.40]
    cutoff = single_cutoff(cutoffs)
    assert cutoff == 0.30

    cutoffs = [0.20, 0.39, 0.40]
    cutoff = single_cutoff(cutoffs)
    assert cutoff == 0.39

    cutoffs = [0.29, 0.31]
    cutoff = single_cutoff(cutoffs)
    assert cutoff == 0.29

    cutoffs = [0.1, 0.11, 0.15, 0.6]
    cutoff = single_cutoff(cutoffs)
    assert cutoff == 0.15

    cutoffs = [0.5]
    cutoff = single_cutoff(cutoffs)
    assert cutoff == 0.5

    cutoffs = [0.1, 0.4, 0.41, 0.42]
    cutoff = single_cutoff(cutoffs)
    assert cutoff == 0.4

    cutoffs = [0.15, 0.18, 0.41, 0.42]
    cutoff = single_cutoff(cutoffs)
    assert cutoff == 0.18

    cutoffs = [0.15, 0.32, 0.56, 0.75, 0.76, 0.77, 0.78, 0.8, 0.9]
    cutoff = single_cutoff(cutoffs)
    assert cutoff == 0.56

