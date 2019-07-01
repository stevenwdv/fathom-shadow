from click import argument, command, File, option, Path
import pathlib


@command()
@option('--out_file', '-o', type=File(mode='w'), default=None,
        help='A file for saving the printed filenames for easy future reference.')
@argument('in_directory', type=Path(exists=True, file_okay=False, allow_dash=True))
def main(in_directory, out_file):
    """
    Lists filenames in a IN_DIRECTORY, one filename per line. Optionally saves output to OUT_FILE.

    Ignores hidden files.

    This is useful for vectorizing samples using fathom-fox. Fathom-fox expects input filenames copied into a text box
    with one filename per line.
    """
    if out_file is not None:
        filenames_to_save = []

    for file in pathlib.Path(in_directory).iterdir():
        # Ignore hidden files
        if file.name.startswith('.'):
            continue

        print(file.name)

        if out_file is not None:
            filenames_to_save.append(file.name + '\n')

    if out_file is not None:
        out_file.writelines(filenames_to_save)
