from os import mkdir
from os.path import basename, join
import re
from zipfile import ZipFile

from click import argument, command, Path, progressbar


def without_suffix(string, suffix):
    if string.endswith(suffix):
        return string[:-len(suffix)]


def make_extraction_dir(path):
    suffix = 0
    ideal_name = without_suffix(basename(path), '.zip')
    while True:
        try:
            dir_name = ideal_name + ((' ' + str(suffix)) if suffix else '')
            mkdir(dir_name)
        except FileExistsError:
            suffix += 1
        else:
            return dir_name


@command()
@argument('zip_file',
          type=Path(exists=True, dir_okay=False, allow_dash=True))
def main(zip_file):
    """Unzip a zip archive containing files with names too long for your
    filesystem. Rename the files as they emerge to get around that limit,
    retaining only leading numbers (though stripping leading zeroes) and the
    extension. If a file doesn't match that pattern, extract it with its
    original name."""
    dir_name = make_extraction_dir(zip_file)
    with ZipFile(zip_file) as archive:
        with progressbar(archive.namelist()) as bar:
            for name in bar:
                base = basename(name)
                match = re.match(r'0*(\d+) .*(\.[a-zA-Z0-9]+$)', base)
                if match:
                    extracted_name = match.group(1) + match.group(2)
                else:
                    extracted_name = base
                with open(join(dir_name, extracted_name), 'wb') as out_file:
                    out_file.write(archive.read(name))
