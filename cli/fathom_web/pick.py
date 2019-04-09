from os import listdir
from os.path import join
from random import sample
from shutil import move

from click import argument, command, Path


@command()
@argument('from_dir',
          type=Path(exists=True, file_okay=False, writable=True, dir_okay=True, allow_dash=True))
@argument('to_dir',
          type=Path(exists=True, file_okay=False, writable=True, dir_okay=True, allow_dash=True))
@argument('number', type=int)
def main(from_dir, to_dir, number):
    """Move a given number of random things from one directory to another.

    Ignore hidden files.

    This is useful for dividing a corpus into training, validation, and testing
    parts.

    """
    files = [f for f in listdir(from_dir) if not f.startswith('.')]
    for file in sample(files, number):
        move(join(from_dir, file), to_dir)
