from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import pathlib
import shutil
import signal
import subprocess
from threading import Thread
import time
import zipfile

from click import argument, command, option, Path, progressbar
from selenium import webdriver


class GracefulError(RuntimeError):
    """Raised when encountering error that allows for a graceful shutdown."""
    pass


class UngracefulError(RuntimeError):
    """Raised when encountering error that does not allow for a graceful shutdown."""
    pass


class SilentRequestHandler(SimpleHTTPRequestHandler):
    """A request handler that will not output the log for each request to the terminal."""
    def log_message(self, format, *args):
        pass


@command()
@argument('ruleset_file', type=str)
@argument('samples_directory', type=Path(exists=True, file_okay=False))
@argument('fathom_fox_dir', type=Path(exists=True, file_okay=False))
@argument('fathom_trainees_dir', type=Path(exists=True, file_okay=False))
@option('--output-directory', '-o', type=Path(exists=True, file_okay=False), default=os.getcwd(),
        help='Directory to save the vector file in (default: current working directory')
@option('--show-browser', '-s', default=False, is_flag=True,
        help='Flag to show browser window while running. Browser is run in headless mode by default.')
def main(ruleset_file, samples_directory, fathom_fox_dir, fathom_trainees_dir, output_directory, show_browser):
    """
    Create feature vectors for a directory of training samples using a Fathom Ruleset.

    RULESET_FILE: Path to the ruleset.js file
    SAMPLES_DIRECTORY: Path to the directory containing the sample pages
    FATHOM_FOX_DIR: Path to the FathomFox source directory
    FATHOM_TRAINEES_DIR: Path to the Fathom Trainees source directory

    This tool will run an instance of Firefox to use the Vectorizer within the
    FathomFox adddon. Required for this tool to work are:
      * node
      * yarn
      * A FathomFox repository checkout
      * A Fathom Trainees repository checkout
    """
    firefox = None
    firefox_pid = None
    geckoview_pid = None
    server = None
    server_thread = None
    graceful_shutdown = False
    try:
        sample_filenames = run_fathom_list(samples_directory)
        fathom_fox, fathom_trainees = build_fathom_addons(ruleset_file, fathom_fox_dir, fathom_trainees_dir)
        server, server_thread = run_file_server(samples_directory)
        firefox, firefox_pid, geckoview_pid = configure_firefox(fathom_fox, fathom_trainees, output_directory, show_browser)
        firefox = run_vectorizer(firefox, sample_filenames)
        graceful_shutdown = True
    # TODO: How to set the exit code here?
    except (KeyboardInterrupt, UngracefulError):
        # Swallow the KeyboardInterrupt here so we can perform our teardown
        # instead of letting Click do something with it.
        pass
    except GracefulError as e:
        print(f'\n\nEncountered error during setup: {e}')
        graceful_shutdown = True
    finally:
        teardown(firefox, firefox_pid, geckoview_pid, server, server_thread, graceful_shutdown)


def run_fathom_list(samples_directory):
    """Use fathom-list to get a string of the filenames to run through the vectorizer."""
    print('Running fathom-list to get list of sample filenames...', end='', flush=True)
    # TODO: Better error message for not having fathom-list
    result = subprocess.run(['fathom-list', samples_directory, '-r'], capture_output=True)
    sample_filenames = result.stdout.decode()
    print('Done')
    return sample_filenames


def build_fathom_addons(ruleset_file, fathom_fox_dir, fathom_trainees_dir):
    """
    Create .xpi files for fathom addons to load into Firefox.

    The Firefox webdriver requires we load custom addons using .xpi files. We
    need to load both FathomFox and Fathom Trainees. For Fathom Trainees, we
    also need to run yarn to package up the addon with the user's ruleset.js.
    """
    print('Building fathom addons for Firefox...', end='', flush=True)
    fathom_fox = create_xpi_for(pathlib.Path(fathom_fox_dir) / 'addon', 'fathom-fox')
    shutil.copyfile(ruleset_file, f'{fathom_trainees_dir}/src/trainees.js')

    # This is because of Windows. Running yarn through the Command Prompt will
    # cause a cancellation prompt to appear if the user presses ctrl+c during
    # yarn's execution. We do not want this. We want this program to stop
    # immediately when a user hits ctrl+c. The work around is to execute yarn
    # through node using yarn.js. To find this file we use `which`, but on
    # Windows, if the user is using cygwin, this command returns a cygwin path,
    # so we need to transform this into a real Windows path.
    # See: https://stackoverflow.com/questions/39085380/how-can-i-suppress-terminate-batch-job-y-n-confirmation-in-powershell
    # TODO: Better error message for not having which or yarn
    yarn_dir = subprocess.run(['which', 'yarn'], capture_output=True).stdout.decode().strip()[:-4]
    if 'cygdrive' in yarn_dir:
        yarn_dir = subprocess.run(['cygpath', '-w', yarn_dir], capture_output=True).stdout.decode().strip()
    # TODO: Better error message for not having node or rollup
    subprocess.run(['node', f'{yarn_dir}/yarn.js', '--cwd', fathom_trainees_dir, 'build'], capture_output=True)

    fathom_trainees = create_xpi_for(pathlib.Path(fathom_trainees_dir) / 'addon', 'fathom-trainees')
    print('Done')
    return fathom_fox, fathom_trainees


def create_xpi_for(directory, name):
    """Create an .xpi archive for a directory and returns its absolute path."""
    xpi_path = pathlib.Path(f'{name}.xpi')
    with zipfile.ZipFile(xpi_path, 'w', compression=zipfile.ZIP_DEFLATED) as xpi:
        for file in directory.rglob('*'):
            xpi.write(file, file.relative_to(directory))
    return str(xpi_path.absolute())


def run_file_server(samples_directory):
    """
    Create a local HTTP server for the samples.

    We return both the server and the thread to handle a graceful or forced
    shutdown.
    """
    print('Starting HTTP file server...', end='', flush=True)
    RequestHandler = partial(SilentRequestHandler, directory=samples_directory)
    server = HTTPServer(('localhost', 8000), RequestHandler)
    server_thread = Thread(target=server.serve_forever)
    server_thread.start()
    print('Done')
    return server, server_thread


def configure_firefox(fathom_fox, fathom_trainees, output_directory, show_browser):
    """
    Configures and launches Firefox to run the vectorizer with.

    Sets headless mode, sets the download directory to the desired output
    directory, turns off page caching, and installs FathomFox and Fathom
    Trainees.

    We return the webdriver object, and the process IDs for both the Firefox
    process and the geckoview driver process so we can shutdown either
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
    firefox = webdriver.Firefox(options=options, firefox_profile=profile)
    firefox.install_addon(fathom_fox, temporary=True)
    firefox.install_addon(fathom_trainees, temporary=True)
    print('Done')
    return firefox, firefox.capabilities['moz:processID'], firefox.service.process.pid


def run_vectorizer(firefox, sample_filenames):
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

    pages_text_area = firefox.find_element_by_id('pages')
    pages_text_area.send_keys(sample_filenames)

    downloads_dir = pathlib.Path(firefox.profile.default_preferences['browser.download.dir'])
    vector_files_before = set(downloads_dir.glob('vector*.json'))
    number_of_samples = len(sample_filenames.splitlines())
    status_box = firefox.find_element_by_id('status')
    vectorize_button = firefox.find_element_by_id('freeze')
    completed_samples = 0
    print('Done')

    with progressbar(length=number_of_samples, label='Running Vectorizer...') as bar:
        vectorize_button.click()
        while completed_samples < number_of_samples:
            if 'failed:' in status_box.text:
                error = extract_error_from(status_box.text)
                print(f'Vectorization failed with error:\n{error}')
                break
            now_completed_samples = len([line for line in status_box.text.splitlines() if line.endswith(': vectorized')])
            bar.update(now_completed_samples - completed_samples)
            completed_samples = now_completed_samples

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
    for _ in range(5):
        prefs = (pathlib.Path(firefox.capabilities.get('moz:profile')) / 'prefs.js').read_text().split(';')
        uuids = next((line for line in prefs if 'extensions.webextensions.uuids' in line)).split(',')
        try:
            fathom_fox_uuid = next((line for line in uuids if 'fathomfox@mozilla.com' in line)).split('\\"')[3]
            return fathom_fox_uuid
        except StopIteration:
            time.sleep(1)
    else:
        raise GracefulError('Could not find UUID for FathomFox. No entry in the pres.js file.')


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


def look_for_new_vector_file(downloads_dir, vector_files_before):
    """
    Look for a new vector file in the downloads directory.

    We use a loop to try multiple times because the file system needs a little
    little time to update before the file appears. Five seconds seems adequate
    since one second has always worked for me (Daniel).
    """
    for _ in range(5):
        vector_files_after = set(downloads_dir.glob('vector*.json'))
        try:
            new_file = (vector_files_after - vector_files_before).pop()
            return new_file
        except KeyError:
            time.sleep(1)
    else:
        raise GracefulError(f'Could not find vectors file in {downloads_dir.as_posix()}.\n{vector_files_before} were already present.')


def teardown(firefox, firefox_pid, geckoview_pid, server, server_thread, graceful_shutdown):
    """
    Close Firefox and the HTTP server.

    There is a graceful shutdown path and an ungraceful shutdown path. If the
    vectorizer has started running, we use the ungraceful shutdown path. This
    is because Firefox becomes unresponsive to the call to `quit()`.
    """
    if graceful_shutdown:
        firefox.quit()
        server.shutdown()
        server_thread.join()
    else:
        # This is the only way I could get killing the program with ctrl+c to work properly.
        if server:
            server.shutdown()
            server_thread.join()
        if firefox:
            try:
                os.kill(firefox_pid, signal.CTRL_C_EVENT)
            except SystemError:
                pass
            os.kill(geckoview_pid, signal.CTRL_C_EVENT)
    # TODO: Remove .xpi files


if __name__ == '__main__':
    main()
