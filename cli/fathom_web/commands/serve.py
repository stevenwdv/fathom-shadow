from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import pathlib
import ssl

from click import command, option, Path


@command()
@option('--port', '-p', type=int, default=8000,
        help='The port to use (default: 8000)')
@option('--directory', '-d', type=Path(exists=True, file_okay=False), default=os.getcwd(),
        help='The directory to serve files from (default: current working directory')
def main(directory, port):
    """
    Serves the files in DIRECTORY over a local https server: https://localhost:PORT.

    The default PORT is 8000.
    The default DIRECTORY is the directory this program is executed from.

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
    print('Press Ctrl+C to stop')
    server.serve_forever()


if __name__ == '__main__':
    main()
