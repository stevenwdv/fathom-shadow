import os

from click.testing import CliRunner

from ..commands.vectorize import main as vectorize_main


def test_end_to_end(tmp_path):
    test_dir = os.path.dirname(os.path.abspath(__file__))

    runner = CliRunner()
    result = runner.invoke(
        vectorize_main,
        [
            f'{test_dir}/resources/vectorize/vectorize_ruleset.js',
            'secret',
            f'{test_dir}/resources/vectorize/',
            f'{tmp_path.as_posix()}/my_vectors.json',
        ]
    )
    assert result.exit_code == 0
    assert (tmp_path / 'my_vectors.json').exists()
