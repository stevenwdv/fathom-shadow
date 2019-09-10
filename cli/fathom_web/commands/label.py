from functools import partial
from html.parser import HTMLParser
import multiprocessing
import os
import pathlib
import shutil

from click import argument, command, option, Path, progressbar, STRING


@command()
@option('--preserve-originals/--no-preserve-originals',
        default=True,
        help='Save original HTML files in a newly created `originals`'
             ' directory in IN_DIRECTORY (default: True)')
@option('--number-of-workers',
        default=multiprocessing.cpu_count(),
        help='Use the specified number of workers to speed up the labeling'
             ' process (default: the number of logical cores the machine has)')
@argument('in_directory', type=Path(exists=True, file_okay=False))
@argument('in_type', type=STRING)
def main(in_directory, in_type, preserve_originals, number_of_workers):
    """
    Add the ``data-fathom`` attribute with a value of IN_TYPE to the
    opening tag of any ``<html>`` elements in the HTML pages in
    IN_DIRECTORY. This tool is used to label an entire webpage (e.g.
    IN_TYPE could be "article" for article webpages).
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

    list_of_items = os.listdir(in_directory)

    print_statements = []  # Capture any print statements to log at the end.

    # Make a pool of workers. Each worker is in its own process. We use a scaling factor to account for the overhead of
    # setting up all of the processes.
    pool = multiprocessing.Pool(number_of_workers)
    # Curry ``task``, so we can pass more than one argument into pool.imap_unordered.
    task = partial(label_task, in_directory, in_type, originals_dir, preserve_originals)

    with progressbar(pool.imap_unordered(task, list_of_items),
                     label='Labeling pages',
                     length=len(list_of_items)) as bar:
        for result in bar:
            if result is not None:
                print_statements.append(result)

    for statement in print_statements:
        print(statement)


def label_task(in_directory, in_type, originals_dir, preserve_originals, filename):
    file = pathlib.Path(in_directory) / filename
    if file == originals_dir:
        return
    if file.is_dir():
        return f'Skipped directory {file.name}/'
    if file.suffix != '.html':
        return f'Skipped {file.name}; not an HTML file'

    with file.open(encoding='utf-8') as fp:
        html = fp.read()

    new_html = label_html_tags_in_html_string(html, in_type)

    if preserve_originals:
        shutil.move(file, originals_dir / file.name)

    with file.open('w', encoding='utf-8') as fp:
        fp.write(new_html)


def label_html_tags_in_html_string(html: str, in_type: str) -> str:
    """
    Finds all opening ``html`` tags in the HTML string and adds a
    ``' data-fathom="${in_type}"'`` substring to each one.

    We do this by building a new HTML string with the inserted substring(s).

    The ``html`` tags are found using the HTMLParser class in Python's
    built-in html.parser library.
    """
    parser = HTMLParserSubclass(in_type)
    parser.feed(html)

    new_html = html

    for (original_html_tag, new_html_tag) in parser.html_tags_list:
        new_html = new_html.replace(original_html_tag, new_html_tag, 1)

    return new_html


class HTMLParserSubclass(HTMLParser):
    def __init__(self, in_type, **kwargs):
        self.in_type = in_type
        self.html_tags_list = []
        super().__init__(**kwargs)

    def handle_starttag(self, tag, attrs):
        if tag == 'html':
            original_html_tag = self.get_starttag_text()
            new_html_substring = f'html data-fathom="{self.in_type}"'
            new_html_tag = original_html_tag.replace('html', new_html_substring, 1)
            self.html_tags_list.append((original_html_tag, new_html_tag))
