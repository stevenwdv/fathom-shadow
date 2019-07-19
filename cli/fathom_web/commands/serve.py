from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import pathlib
import ssl

from click import argument, command, option, Path


@command()
@option('--port', '-p', type=int, default=8000,
        help='The port to use (default: 8000)')
@argument('directory', type=Path(exists=True, file_okay=False))
def main(directory, port):
    """
    Serves the files in DIRECTORY over a local https server: https://localhost:PORT.

    The default PORT is 8000.

    This is useful for vectorizing samples using FathomFox. FathomFox expects you to provide,
    in the vectorizer page, an address to an https server that is serving your samples.
    """
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    server = HTTPServer(('localhost', port), handler)
    certfile = pathlib.Path(os.path.realpath(__file__)).parent / '..' / 'cert' / 'cert.pem'
    server.socket = ssl.wrap_socket(
        server.socket,
        certfile=certfile,
        server_side=True,
    )
    print(f'Serving {directory} over https://localhost:{port}')
    server.serve_forever()


if __name__ == '__main__':
    main()
