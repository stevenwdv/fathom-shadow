import pathlib
from random import sample
from shutil import move

from click import argument, command, Path, UsageError


@command()
@argument('from_dir',
          type=Path(exists=True, file_okay=False, writable=True, dir_okay=True))
@argument('to_dir',
          type=Path(exists=True, file_okay=False, writable=True, dir_okay=True))
@argument('number', type=int)
def pick(from_dir, to_dir, number):
    """
    Randomly move samples to a training, validation, or test set.

    Move a random selection of HTML files and their extracted resources, if
    any, from one directory to another. Ignore hidden files.

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
