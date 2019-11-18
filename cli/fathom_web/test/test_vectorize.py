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
            f'{test_dir}/resources/vectorize/',
            os.environ['FATHOM_FOX'],
            os.environ['FATHOM_TRAINEES'],
            '-o',
            f'{tmp_path.as_posix()}',
            '-s',
        ]
    )
    print(result.output)
    assert result.exit_code == 0
    assert (tmp_path / 'vectors.json').exists()
