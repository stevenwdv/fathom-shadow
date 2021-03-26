import os

from click.testing import CliRunner

from ..commands.train import exclude_indices, train, find_optimal_cutoff
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
