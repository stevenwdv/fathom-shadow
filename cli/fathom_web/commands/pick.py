import pathlib
from random import sample
from shutil import move

from click import argument, command, Path, UsageError


@command()
@argument('from_dir',
          type=Path(exists=True, file_okay=False, writable=True, dir_okay=True, allow_dash=True))
@argument('to_dir',
          type=Path(exists=True, file_okay=False, writable=True, dir_okay=True, allow_dash=True))
@argument('number', type=int)
def main(from_dir, to_dir, number):
    """Move a given number of HTML files and any extracted resources from one
    directory to another.

    Ignore hidden files.

    This is useful for dividing a corpus into training, validation, and testing
    parts.
    """
    # Make these strings into ``Path``s so they are easier to work with
    from_dir = pathlib.Path(from_dir)
    to_dir = pathlib.Path(to_dir)

    for file in sample(list(from_dir.glob('*.html')), number):
        # If the file has resources, we must move those as well:
        if (from_dir / 'resources' / file.stem).exists():
            # Make sure we don't overwrite an existing resources directory
            if (to_dir / 'resources' / file.stem).exists():
                raise UsageError(f'Tried to make directory {(to_dir / "resources" / file.stem).as_posix()}, but it'
                                 f' already exists. To protect against unwanted data loss, please move or remove the'
                                 f' existing directory.')
            move(from_dir / 'resources' / file.stem, to_dir / 'resources' / file.stem)
        move(file.as_posix(), to_dir)
