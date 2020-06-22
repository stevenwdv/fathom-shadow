from contextlib import contextmanager
from zipfile import ZipFile

import click
from click import command, option, pause

from ..utils import path_or_none
from ..vectorizer import fathom_fox_addon, fathom_zip, running_firefox


@command()
@option('--ruleset', '-r',
        type=click.Path(exists=True, dir_okay=False, resolve_path=True),
        callback=path_or_none,
        help='The rulesets.js file containing your rules. The file must have no imports except from fathom-web, so pre-bundle if necessary. [default: the demo ruleset included with FathomFox]')
def main(ruleset):
    """Launch a fresh instance of Firefox with a blank profile and FathomFox
    installed.

    This is an easy way to set up an environment for labeling samples.

    """
    with ruleset_or_default(ruleset) as ruleset_file:
        with fathom_fox_addon(ruleset_file) as addon_and_geckodriver:
            addon_path, geckodriver_path = addon_and_geckodriver
            with running_firefox(addon_path, True, geckodriver_path):
                pause(info='Press any key to quit.')


@contextmanager
def ruleset_or_default(ruleset_path_or_none):
    """Yield the ruleset file-like object to use.

    This allows us to conditionally call various needed context managers.

    """
    if ruleset_path_or_none:
        with ruleset_path_or_none.open('rb') as ruleset_file:
            yield ruleset_file
    else:
        # Go get the default demo ruleset:
        with fathom_zip() as zip_file:
            zip = ZipFile(zip_file)
            # Opens in binary mode:
            with zip.open('fathom_fox/src/rulesets.js') as default_ruleset:
                yield default_ruleset
