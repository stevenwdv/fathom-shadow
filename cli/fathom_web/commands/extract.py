import base64
import mimetypes
import pathlib
import shutil
import re
from urllib.parse import unquote
from urllib.request import pathname2url

from click import argument, command, option, Path, progressbar


BASE64_DATA_PATTERN = re.compile(r'(data:(?P<mime>[a-zA-Z0-9]+/[a-zA-Z0-9\-.+]+);(\s?charset=utf-8;)?base64,(?P<string>(?:[a-zA-Z0-9+/=]|%3D)+))')
BASE_TAG_PATTERN = re.compile(r'<base [^>]*>')
OLD_CSP = re.compile(r"default-src 'none'; img-src data:; media-src data:; style-src data: 'unsafe-inline'; font-src data:; frame-src data:")
NEW_CSP = r"default-src 'none'; img-src 'self' data:; media-src 'self' data:; style-src 'self' data: 'unsafe-inline'; font-src 'self' data:; frame-src 'self' data:"
# These are MIME types the `mimetypes` library doesn't recognize or gets wrong.
# Matches were found at:
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Complete_list_of_MIME_types
MIME_TYPE_TO_FILE_EXTENSION = {
    'application/font-woff': '.woff',
    'application/font-woff2': '.woff2',
    'application/vnd.ms-fontobject': '.eot',
    'font/opentype': '.otf',
    'font/ttf': '.ttf',
    'font/woff': '.woff',
    'font/woff2': '.woff2',
    'image/jpeg': '.jpg',
    'image/webp': '.webp',
    # From https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Complete_list_of_MIME_types:
    'audio/aac': '.aac',
    'application/gzip': '.gz',
    'text/javascript': '.js',
    'application/ld+json': '.jsonld',
    'audio/midi audio/x-midi': '.midi',
    'audio/opus': '.opus',
    'application/php': '.php',
    'application/vnd.rar': '.rar',
    'audio/wav': '.wav',
    # From sample pages we've collected:
    'application/x-font-ttf': '.ttf',
    'image/jpg': '.jpg',
    'image/xicon': '.ico',
    'image/x-icon': '.ico',
    'application/fontwoff2': '.woff2',
    'application/fontwoff': '.woff',
    'application/x-font-woff': '.woff',
    'application/font-ttf': '.ttf',
    'application/x-javascript': '.js',
    'application/font-sfnt': '.sfnt',
    'application/vnd.ms-opentype': 'otf',
    'application/x-mpegurl': '.m3u8',
}


@command()
@option('--preserve-originals/--no-preserve-originals',
        default=True,
        help='Save original HTML files in a newly created `originals`'
             ' directory in IN_DIRECTORY (default: True)')
@argument('in_directory', type=Path(exists=True, file_okay=False))
def main(in_directory, preserve_originals):
    """
    Extract resources from the HTML pages in IN_DIRECTORY and store the
    resources for each page in a newly created page-specific directory
    within a newly created resources directory in IN_DIRECTORY.
    For example, the resources for ``example.html`` would be stored in
    ``resources/example/``. This tool is used to prepare your samples for a
    git-LFS-enabled repository.
    """
    if preserve_originals:
        originals_dir = pathlib.Path(in_directory) / 'originals'
        try:
            originals_dir.mkdir(parents=True)
        except FileExistsError:
            raise RuntimeError(f'Tried to make directory {originals_dir.as_posix()}, but it already exists. To protect'
                               f' against unwanted data loss, please move or remove the existing directory.')
    else:
        originals_dir = None

    with progressbar(list(pathlib.Path(in_directory).iterdir())) as bar:
        for file in bar:
            if file == originals_dir:
                continue
            if file.is_dir():
                print(f'Skipping directory {file.name}/')
                continue
            if file.suffix != '.html':
                print(f'Skipping {file.name}; not an HTML file')
                continue

            html = extract_base64_data_from_html_page(file)

            if preserve_originals:
                shutil.move(file, originals_dir / file.name)

            with file.open('w', encoding='utf-8') as fp:
                fp.write(html)


def extract_base64_data_from_html_page(file: pathlib.Path):
    """
    Extract all base64 data from the given HTML page and store the data in
    separate files.

    We do this by building a new HTML string using the non-base64 data pieces
    from the original file and the filenames we will generate for each of the
    base64 data strings.

    Base64 data is found with regex matching. Each data string is decoded and
    saved as a separate file.
    """
    with file.open(encoding='utf-8') as fp:
        html = fp.read()

    # Make the subresources directory
    subresources_directory = file.parent / 'resources' / f'{file.stem}'
    subresources_directory.mkdir(parents=True, exist_ok=True)

    offset = 0
    new_html = ''

    filename_counter = 0
    # A cache for elements that are repeated (e.g. icons)
    saved_strings = {}

    # Remove any existing `<base>` tag
    html = BASE_TAG_PATTERN.sub('', html)

    # Add `'self'` to the Content Security Policy
    # so we can load our extracted resources
    html = OLD_CSP.sub(NEW_CSP, html)

    base64_data_matches = BASE64_DATA_PATTERN.finditer(html)
    for match in base64_data_matches:
        # Add the content before the base64 data
        new_html += html[offset:match.start(1)]

        base64_string = match.group('string')

        # Check to see if we have already encountered this base64 string.
        # If we haven't seen it, we'll go through the process of decoding,
        # saving, and adding it to our cache.
        file_path = saved_strings.get(base64_string)
        if file_path is None:
            mime_type = match.group('mime')
            filename_counter += 1
            filename = generate_filename(mime_type, str(filename_counter))
            binary_data = decode(base64_string)
            file_path = subresources_directory / filename
            with file_path.open('wb') as resource_file:
                resource_file.write(binary_data)
            saved_strings[base64_string] = file_path

        # "Replace" the old base64 data with the relative
        # path to the newly created file
        new_html += pathname2url(file_path.relative_to(file.parent).as_posix())

        # Move our offset to the end of the old base64 data
        offset = match.end(1)

    # Add the remainder of the content
    new_html += html[offset:]

    return new_html


def generate_filename(mime_type: str, filename: str) -> str:
    """
    Create a filename to use for saving the base64 data with the appropriate
    file extension.

    We can't necessarily get an appropriate filename from the HTML the base64
    data comes from, so we don't even try. Instead we just use an incrementing
    counter to ensure unique filenames.

    The appropriate extension comes from mapping the MIME type contained in the
    base64 data to an extension.
    """
    # `mimetypes` gets some extensions wrong (e.g. image/jpeg -> .jpe) and
    # doesn't work for some MIME types that freeze-dry gives so use our own
    # mapping first
    try:
        extension = MIME_TYPE_TO_FILE_EXTENSION[mime_type]
    except KeyError:
        extension = mimetypes.guess_extension(mime_type, strict=True)
        if extension is None:
            extension = input(f'\nWhat file extension should I use for a resource of type {mime_type}? ')
            if not extension.startswith('.'):
                extension = '.' + extension
            MIME_TYPE_TO_FILE_EXTENSION[mime_type] = extension
    return f'{filename}{extension}'


def decode(base64_string: str) -> bytes:
    """
    Decodes the base64 string into bytes.

    If as string has any additional encoding (ex. percent encoding of the
    padding characters), decode that first.

    We also check if the string is padded to a number of characters that is a
    multiple of four, which is what base64.b64decode() requires.
    """
    # Percent encoding
    if '%' in base64_string:
        base64_string = unquote(base64_string)
    # Padding check
    string_mod_4 = len(base64_string) % 4
    if string_mod_4 != 0:
        base64_string += '=' * (4 - string_mod_4)

    return base64.b64decode(base64_string)
