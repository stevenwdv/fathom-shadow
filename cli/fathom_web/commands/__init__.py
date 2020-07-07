from .extract import extract
from .fox import fox
from .histogram import histogram
from .label import label
from .list import list
from .pick import pick
from .serve import serve
from .test import test
from .train import train

from click import group


@group()
def fathom():
    """Pass fathom COMMAND --help to learn more about an individual command."""


fathom.add_command(extract)
fathom.add_command(fox)
fathom.add_command(histogram)
fathom.add_command(label)
fathom.add_command(list)
fathom.add_command(pick)
fathom.add_command(serve)
fathom.add_command(test)
fathom.add_command(train)
