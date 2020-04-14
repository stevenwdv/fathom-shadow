from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import os
import pathlib
import platform
import shutil
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import zipfile

from click import argument, command, option, Path, progressbar
from selenium import webdriver
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver.support.ui import Select

from .list import samples_from_dir
from ..utils import wait_for_function


class GracefulError(RuntimeError):
    """Raised when encountering error that allows for a graceful shutdown."""


class UngracefulError(RuntimeError):
    """Raised when encountering error that does not allow for a graceful shutdown."""


class SilentRequestHandler(SimpleHTTPRequestHandler):
    """A request handler that will not output the log for each request to the terminal."""
    def log_message(self, format, *args):
        pass


@command()
@argument('ruleset_file', type=str)
@argument('fathom_type', type=str)
@argument('samples_directory', type=Path(exists=True, file_okay=False))
@argument('fathom_fox_dir', type=Path(exists=True, file_okay=False))
@option('--output-directory', '-o', type=Path(exists=True, file_okay=False), default=os.getcwd(),
        help='Directory to save the vector file in (default: current working directory')
@option('--show-browser', '-s', default=False, is_flag=True,
        help='Flag to show browser window while running. Browser is run in headless mode by default.')
def main(ruleset_file, fathom_type, samples_directory, fathom_fox_dir, output_directory, show_browser):
    """
    Create feature vectors for a directory of training samples using a Fathom Ruleset.

    \b
    RULESET_FILE: Path to the ruleset.js file. The file must be pre-bundled, if necessary (containing no import statements).
    FATHOM_TYPE: The Fathom type to create vectors for
    SAMPLES_DIRECTORY: Path to the directory containing the sample pages
    FATHOM_FOX_DIR: Path to the FathomFox source directory
    FATHOM_TRAINEES_DIR: Path to the Fathom Trainees source directory

    \b
    This tool will run an instance of Firefox to use the Vectorizer within the
    FathomFox adddon. Required for this tool to work are:
      * node
      * yarn
      * A FathomFox repository checkout
      * A Fathom Trainees repository checkout
      * A copy of Firefox
      * geckodriver downloaded and accessible in your PATH environment variable

    Please note that this utility is considered experimental due to the use of os.kill() when shutting down while the
    vectorization is occurring. We are working on fixing this. Repeatedly stopping this program while vectorization is
    happening may cause problems with other currently running Firefox processes.
    """
    # TODO: Try a class based approach so I don't need these =None statements or need to pass the temp_dir around
    firefox = None
    firefox_pid = None
    geckodriver_pid = None
    server = None
    server_thread = None
    graceful_shutdown = False
    try:
        sample_filenames = [str(sample.relative_to(samples_directory))
                            for sample in samples_from_dir(samples_directory)]
        with TemporaryDirectory() as temp_dir:
            temp_dir = pathlib.Path(temp_dir)
            fathom_fox = build_fathom_addons(ruleset_file, fathom_fox_dir, temp_dir)
            server = run_file_server(samples_directory)
            firefox, firefox_pid, geckodriver_pid = configure_firefox(fathom_fox, output_directory, show_browser, temp_dir)
            firefox = run_vectorizer(firefox, fathom_type, sample_filenames)
        graceful_shutdown = True
    # TODO: How to set the exit code here?
    except KeyboardInterrupt:
        # Swallow the KeyboardInterrupt here so we can perform our teardown
        # instead of letting Click do something with it.
        pass
    except UngracefulError as e:
        print(f'\n\n{e}')
    except GracefulError as e:
        print(f'\n\n{e}')
        graceful_shutdown = True
    finally:
        teardown(firefox, firefox_pid, geckodriver_pid, server, graceful_shutdown)


def build_fathom_addons(ruleset_file, fathom_fox_dir, temp_dir):
    """
    Create .xpi files for fathom addons to load into Firefox.

    The Firefox webdriver requires we load custom addons using .xpi files. We
    need to load both FathomFox and Fathom Trainees. For Fathom Trainees, we
    also need to run yarn to package up the addon with the user's ruleset.js.
    """
    print('Building fathom addons for Firefox...', end='', flush=True)
    shutil.copyfile(ruleset_file, f'{fathom_fox_dir}/src/rulesets.js')  # XXX: escape fathom_fox_dir

    if platform.system() == 'Windows':
        # This is because of Windows. Running yarn through the Command Prompt will
        # cause a cancellation prompt to appear if the user presses ctrl+c during
        # yarn's execution. We do not want this. We want this program to stop
        # immediately when a user hits ctrl+c. The work around is to execute yarn
        # through node using yarn.js. To find this file we use `which`.
        # See: https://stackoverflow.com/questions/39085380/how-can-i-suppress-terminate-batch-job-y-n-confirmation-in-powershell
        # TODO: Better error message for not having which or yarn
        # TODO: Do we need to call `which` on plain, Cygwin-less Windows? We
        #       don't on the Mac.
        yarn_dir = subprocess.run(['which', 'yarn'], capture_output=True).stdout.decode().strip()[:-4]
        if sys.platform == 'cygwin':
            # Under cygwin, `where` returns a cygwin path, so we need to
            # transform this into a proper Windows path:
            yarn_dir = subprocess.run(['cygpath', '-w', yarn_dir], capture_output=True).stdout.decode().strip()
        # TODO: Better error message for not having node or rollup
        # XXX: escape yarn_dir. It could contain spaces, etc.
        yarn_cmd = ['node', f'{yarn_dir}/yarn.js']
    else:
        yarn_cmd = ['yarn']
    subprocess.run([*yarn_cmd, '--cwd', fathom_fox_dir, 'run', 'build'], capture_output=True, check=True)
    fathom_fox = create_xpi_for(pathlib.Path(fathom_fox_dir) / 'addon', 'fathom-fox', temp_dir)
    print('Done')
    return fathom_fox


def create_xpi_for(directory, name, dest_dir):
    """Create an .xpi archive for a directory and returns its absolute path."""
    xpi_path = dest_dir / f'{name}.xpi'
    with zipfile.ZipFile(xpi_path, 'w', compression=zipfile.ZIP_DEFLATED) as xpi:
        for file in directory.rglob('*'):
            xpi.write(file, file.relative_to(directory))
    return str(xpi_path.absolute())


def run_file_server(samples_directory):
    """
    Create a local HTTP server for the samples.
    """
    print('Starting HTTP file server...', end='', flush=True)
    RequestHandler = partial(SilentRequestHandler, directory=samples_directory)
    server = ThreadingHTTPServer(('localhost', 8000), RequestHandler)
    server_thread = Thread(target=server.serve_forever)
    server_thread.start()
    print('Done')
    return server


def configure_firefox(fathom_fox, output_directory, show_browser, temp_dir):
    """
    Configures and launches Firefox to run the vectorizer with.

    Sets headless mode, sets the download directory to the desired output
    directory, turns off page caching, and installs FathomFox and Fathom
    Trainees.

    We return the webdriver object, and the process IDs for both the Firefox
    process and the geckodriver process so we can shutdown either
    gracefully or ungracefully.
    """
    print('Configuring Firefox...', end='', flush=True)
    options = webdriver.FirefoxOptions()
    options.headless = not show_browser

    profile = webdriver.FirefoxProfile()
    profile.set_preference('browser.download.folderList', 2)
    profile.set_preference('browser.download.dir', str(pathlib.Path(output_directory).absolute()))
    profile.set_preference('browser.cache.disk.enable', False)
    profile.set_preference('browser.cache.memory.enable', False)
    profile.set_preference('browser.cache.offline.enable', False)

    firefox = webdriver.Firefox(
        options=options,
        firefox_profile=profile,
        service_log_path=temp_dir / 'geckodriver.log',
    )

    firefox.install_addon(fathom_fox, temporary=True)
    print('Done')
    return firefox, firefox.capabilities['moz:processID'], firefox.service.process.pid


def run_vectorizer(firefox, fathom_type, sample_filenames):
    """
    Set up the vectorizer and run it, creating the vectors file.

    Navigate to the vectorizer page of FathomFox, paste the sample filenames
    into the text area and hit the vectorize button.

    We monitor the status text area for errors and to see how many samples
    have been vectorized, so we know when the vectorizer has stopped running.
    """
    print('Configuring Vectorizer...', end='', flush=True)
    # Navigate to the vectorizer page
    fathom_fox_uuid = get_fathom_fox_uuid(firefox)
    firefox.get(f'moz-extension://{fathom_fox_uuid}/pages/vector.html')

    # TODO: Before selecting, check if the page is reporting an error about no ruleset present. If there is, raise a GracefulError.
    ruleset_dropdown_selector = Select(firefox.find_element_by_id('ruleset'))
    ruleset_dropdown_selector.select_by_visible_text(fathom_type)

    pages_text_area = firefox.find_element_by_id('pages')
    pages_text_area.send_keys('\n'.join(sample_filenames))

    downloads_dir = pathlib.Path(firefox.profile.default_preferences['browser.download.dir'])
    vector_files_before = set(downloads_dir.glob('vector*.json'))
    number_of_samples = len(sample_filenames)
    status_box = firefox.find_element_by_id('status')
    vectorize_button = firefox.find_element_by_id('freeze')
    completed_samples = 0
    print('Done')

    with progressbar(length=number_of_samples, label='Running Vectorizer...') as bar:
        vectorize_button.click()
        while completed_samples < number_of_samples:
            try:
                status_box_text = status_box.text
            except NoSuchWindowException:
                raise UngracefulError('Vectorization aborted: Firefox window closed during vectorization')
            try:
                failure_detected = 'failed' in status_box_text
            except TypeError:
                raise UngracefulError('Vectorization aborted: Firefox window closed during vectorization')
            if failure_detected:
                error = extract_error_from(status_box_text)
                raise UngracefulError(f'Vectorization failed with error:\n{error}')
            now_completed_samples = len([line for line in status_box_text.splitlines() if line.endswith(': vectorized')])
            bar.update(now_completed_samples - completed_samples)
            completed_samples = now_completed_samples
            # TODO: Is this a busy loop? Sleep.

    new_file = look_for_new_vector_file(downloads_dir, vector_files_before)
    print(f'Vectors saved to {str(new_file)}')
    return firefox


def get_fathom_fox_uuid(firefox):
    """
    Try to get the internal UUID for FathomFox from `prefs.js`.

    We use a loop to try multiple times because the `prefs.js` file needs a
    little time to update before the fathom addon information appears. Five
    seconds seems adequate since one second has always worked for me (Daniel).
    """
    def get_uuid():
        prefs = (pathlib.Path(firefox.capabilities.get('moz:profile')) / 'prefs.js').read_text().split(';')
        uuids = next((line for line in prefs if 'extensions.webextensions.uuids' in line)).split(',')
        fathom_fox_uuid = next((line for line in uuids if '{954efd86-8f62-49e7-8a65-80016051e382}' in line)).split('\\"')[3]
        return fathom_fox_uuid

    error = GracefulError('Could not find UUID for FathomFox. No entry in the prefs.js file.')
    return wait_for_function(get_uuid, error, max_tries=5)


def vector_files_present(firefox):
    """Return the number of vector-y files present in Firefox's download dir."""
    download_dir = pathlib.Path(firefox.profile.default_preferences['browser.download.dir'])
    vector_files = download_dir.glob('vector*.json')
    return len(list(vector_files))


def extract_error_from(status_text):
    """
    Look for errors in the vectorizer's status text.

    If there is an error, raise an exception causing an ungraceful shutdown.
    """
    lines = status_text.splitlines()
    for line in lines:
        if 'failed:' in line:
            return line
    raise UngracefulError(f'There was a vectorizer error, but we could not find it in {status_text}')


# TODO: Remove the need for this terrible thing.
def look_for_new_vector_file(downloads_dir, vector_files_before):
    """
    Look for a new vector file in the downloads directory.

    We use a loop to try multiple times because the file system needs a little
    little time to update before the file appears. Five seconds seems adequate
    since one second has always worked for me (Daniel).
    """
    def get_vector_file():
        vector_files_after = set(downloads_dir.glob('vector*.json'))
        new_file = (vector_files_after - vector_files_before).pop()
        return new_file

    error_string = f'Could not find vectors file in {downloads_dir.as_posix()}.'
    if vector_files_before:
        files_present = '\n'.join(file.as_posix() for file in vector_files_before)
        error_string += f' Files present were:\n{files_present}'
    error = GracefulError(error_string)
    return wait_for_function(get_vector_file, error, max_tries=5)


def teardown(firefox, firefox_pid, geckodriver_pid, server, graceful_shutdown):
    """
    Close Firefox and the HTTP server.

    There is a graceful shutdown path and an ungraceful shutdown path. If the
    vectorizer has started running, we use the ungraceful shutdown path. This
    is because Firefox becomes unresponsive to the call to `quit()`.
    """
    if graceful_shutdown:
        firefox.quit()
        server.shutdown()
        server.server_close()  # joins threads in 
    else:
        # This is the only way I could get killing the program with ctrl+c to work properly.
        if server:
            server.shutdown()
            server.server_close()
        if firefox:
            if os.name == 'nt':
                signal_for_killing = signal.CTRL_C_EVENT
            else:
                signal_for_killing = signal.SIGTERM
            try:
                os.kill(firefox_pid, signal_for_killing)
            except SystemError:
                pass
            os.kill(geckodriver_pid, signal_for_killing)


if __name__ == '__main__':
    main()
