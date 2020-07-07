import os

from click.testing import CliRunner

from ..commands.train import exclude_indices, train


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
