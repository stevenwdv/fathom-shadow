import pathlib
import re

from click import argument, command, File, option, Path


@command()
@argument('in_directory', type=Path(exists=True, file_okay=False))
@option('--base-dir', '-b', type=Path(exists=True, file_okay=False),
        help='The directory to create relative paths from.')
@option('--recursive', '-r', default=False, is_flag=True,
        help='Recursively list files from the IN_DIRECTORY and all subdirectories.')
@option('--out-file', '-o', type=File(mode='w'), default=None,
        help='A file for saving the printed filenames for easy future reference.')
@option('--show-urls', '-u', default=False, is_flag=True,
        help='Also show the original URL of each sample.')
def main(in_directory, base_dir, recursive, out_file, show_urls):
    """
    Lists relative paths of HTML files in a IN_DIRECTORY relative to BASE_DIR, one filename per line.
    If BASE_DIR is not specified, paths are relative to IN_DIRECTORY. Optionally saves output to OUT_FILE.
    Optionally performs the listing recursively.

    This is useful for vectorizing samples using FathomFox. FathomFox expects input filenames copied into a text box
    with one filename per line and relative to some path you are serving files from using fathom-serve.
    """
    if base_dir is None:
        base_dir = in_directory
    base_dir = pathlib.Path(base_dir)

    if recursive:
        path_iterator = pathlib.Path(in_directory).rglob('*.html')
    else:
        path_iterator = pathlib.Path(in_directory).glob('*.html')

    if out_file is not None:
        filenames_to_save = []

    there_were_no_files = True
    for file in path_iterator:
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
