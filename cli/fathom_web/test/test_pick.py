from click.testing import CliRunner

from ..commands.pick import main as pick_main


def test_end_to_end(tmp_path):
    """
    Given a directory of three files, use ``fathom-pick`` to move two files, and
    check that the files and their potential resources directories have moved.
    """
    # Make temporary source and destination directories
    source = tmp_path / 'source'
    source.mkdir()
    destination = tmp_path / 'destination'
    destination.mkdir()

    # Add files to the source directory
    file_1 = source / '1.html'
    file_1.write_text('I am file 1')
    file_2 = source / '2.html'
    file_2.write_text('I am file 2')
    file_3 = source / '3.html'
    file_3.write_text('I am file 3')

    # Add resource directories for files 1 and 2
    resources = source / 'resources'
    resources.mkdir()
    file_1_resources = resources / '1'
    file_1_resources.mkdir()
    file_1_resource_1 = file_1_resources / '1.png'
    file_1_resource_1.write_text('I am resource 1 for file 1')
    file_1_resource_2 = file_1_resources / '2.css'
    file_1_resource_2.write_text('I am resource 2 for file 1')
    file_2_resources = resources / '2'
    file_2_resources.mkdir()
    file_2_resource_1 = file_2_resources / '1.png'
    file_2_resource_1.write_text('I am resource 1 for file 2')
    file_2_resource_2 = file_2_resources / '2.css'
    file_2_resource_2.write_text('I am resource 2 for file 2')

    # Run fathom-pick to move 2 files from source to destination
    runner = CliRunner()
    # Arguments to invoke() must be passed as strings (this isn't documented!!!)
    result = runner.invoke(pick_main, [source.as_posix(), destination.as_posix(), '2'])
    assert result.exit_code == 0

    # Check the correct number of files have moved
    files_in_source = list(source.glob('*.html'))
    assert len(files_in_source) == 1
    files_in_destination = list(destination.glob('*.html'))
    assert len(files_in_destination) == 2

    # Check any resource directories have moved
    if (destination / '1.html').exists():
        assert (destination / 'resources' / '1' / '1.png').exists()
        assert (destination / 'resources' / '1' / '2.css').exists()
    if (destination / '2.html').exists():
        assert (destination / 'resources' / '2' / '1.png').exists()
        assert (destination / 'resources' / '2' / '2.css').exists()

    # Make sure we didn't lose any files
    files_in_directories = {file.name for file in files_in_source} | {file.name for file in files_in_destination}
    assert {'1.html', '2.html', '3.html'} == files_in_directories
