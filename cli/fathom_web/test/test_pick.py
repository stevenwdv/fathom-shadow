from click.testing import CliRunner

from ..commands.pick import pick


def test_end_to_end(tmp_path):
    """
    Given a directory of three files, use ``fathom pick`` to move two files, and
    check that the files and their potential resources directories have moved.
    """
    # Make temporary source and destination directories
    source = tmp_path / 'source'
    source.mkdir()
    destination = tmp_path / 'destination'
    destination.mkdir()

    # Add files to the source directory
    (source / '1.html').touch()
    (source / '2.html').touch()
    (source / '3.html').touch()

    # Add resource directories for files 1 and 2
    (source / 'resources' / '1').mkdir(parents=True)
    (source / 'resources' / '1' / '1.png').touch()
    (source / 'resources' / '1' / '2.css').touch()
    (source / 'resources' / '2').mkdir(parents=True)
    (source / 'resources' / '2' / '1.png').touch()
    (source / 'resources' / '2' / '2.css').touch()

    # Run fathom pick to move 2 files from source to destination
    runner = CliRunner()
    # Arguments to invoke() must be passed as strings (this isn't documented!!!)
    result = runner.invoke(pick, [source.as_posix(), destination.as_posix(), '2'])
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


def test_resource_directory_path_collision(tmp_path):
    """
    Ensure an exception is raised when moving a resource directory
    if that directory already exists in the destination directory.
    """
    # Make temporary source and destination directories
    source = tmp_path / 'source'
    source.mkdir()
    destination = tmp_path / 'destination'
    destination.mkdir()

    # Add the file to the source directory
    (source / '1.html').touch()

    # Add the resource directory for our file
    (source / 'resources' / '1').mkdir(parents=True)
    (source / 'resources' / '1' / '1.png').touch()
    (source / 'resources' / '1' / '2.css').touch()

    # Add a resource directory for the same file in the destination directory
    (destination / 'resources' / '1').mkdir(parents=True)

    # Run fathom pick to move the only file from source to destination
    runner = CliRunner()
    # Arguments to invoke() must be passed as strings (this isn't documented!!!)
    result = runner.invoke(pick, [source.as_posix(), destination.as_posix(), '1'])

    # Assert the program exited with a UsageError and our error message is in the program output
    assert result.exit_code == 2
    assert 'Error: Tried to make directory' in result.output

    # Check that our files haven't moved
    files_in_source = list(source.glob('*.html'))
    assert len(files_in_source) == 1
    assert (source / 'resources' / '1' / '1.png').exists()
    assert (source / 'resources' / '1' / '2.css').exists()
    files_in_destination = list(destination.glob('*.html'))
    assert len(files_in_destination) == 0
    assert (destination / 'resources' / '1').exists()
