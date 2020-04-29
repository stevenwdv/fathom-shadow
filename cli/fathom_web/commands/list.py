import re

from click import argument, command, File, option, Path

from ..utils import samples_from_dir


@command()
@argument('in_directory', type=Path(exists=True, file_okay=False))
@option('--base-dir', '-b', type=Path(exists=True, file_okay=False),
        help='The directory to create relative paths from.')
@option('--out-file', '-o', type=File(mode='w'), default=None,
        help='A file for saving the printed filenames for easy future reference.')
@option('--show-urls', '-u', default=False, is_flag=True,
        help='Also show the original URL of each sample.')
def main(in_directory, base_dir, out_file, show_urls):
    """
    Recursively list paths of HTML files in IN_DIRECTORY relative to BASE_DIR,
    one path per line. If BASE_DIR is not specified, paths are relative to
    IN_DIRECTORY. Optionally saves output to OUT_FILE.

    This is useful for vectorizing samples using FathomFox. FathomFox expects
    input filenames copied into a text box with one filename per line and
    relative to some path you are serving files from using fathom-serve.
    """
    if base_dir is None:
        base_dir = in_directory

    if out_file is not None:
        filenames_to_save = []

    there_were_no_files = True
    for file in samples_from_dir(in_directory):
        there_were_no_files = False
        relative_path = file.relative_to(base_dir)
        if show_urls:
            with file.open() as open_file:
                print(relative_path, original_url(open_file))
        else:
            print(relative_path)

        if out_file is not None:
            filenames_to_save.append(relative_path.as_posix() + '\n')

    if out_file is not None:
        if there_were_no_files:
            print(f'No .html files found in {in_directory}. Did not create {out_file.name}.')
        else:
            out_file.writelines(filenames_to_save)


def original_url(open_file):
    """Return the original URL that FathomFox embedded in a given sample."""
    # I started to write a clever loop to read only as much from each file as
    # we needed, but it turns out reading 67 entire unextracted samples takes
    # only 1.2s on my laptop.
    match = re.search('<link rel="original" href="([^"]+)">', open_file.read())
    if not match:
        return ''
    return match.group(1)
