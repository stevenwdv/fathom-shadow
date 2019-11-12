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


class SilentRequestHandler(SimpleHTTPRequestHandler):
    """This request handler will not output log each request to the terminal"""
    def log_message(self, format, *args):
        pass


@command()
@argument('trainees_file', type=str)
@argument('samples_directory', type=Path(exists=True, file_okay=False))
@argument('fathom_fox_dir', type=Path(exists=True, file_okay=False))
@argument('fathom_trainees_dir', type=Path(exists=True, file_okay=False))
@option('--output-directory', '-o', type=Path(exists=True, file_okay=False), default=os.getcwd())
@option('--show-browser', '-s', default=False, is_flag=True)
def main(trainees_file, samples_directory, fathom_fox_dir, fathom_trainees_dir, output_directory, show_browser):
    firefox = None
    firefox_pid = None
    geckoview_pid = None
    server = None
    server_thread = None
    graceful_shutdown = False
    try:
        sample_filenames = run_fathom_list(samples_directory)
        fathom_fox, fathom_trainees = build_fathom_addons(trainees_file, fathom_fox_dir, fathom_trainees_dir)
        server, server_thread = run_file_server(samples_directory)
        firefox, firefox_pid, geckoview_pid = configure_firefox(fathom_fox, fathom_trainees, output_directory, show_browser)
        firefox = run_vectorizer(firefox, sample_filenames)
        graceful_shutdown = True
    except KeyboardInterrupt:
        # Swallow the KeyboardInterrupt here so we can perform our teardown
        # instead of letting Click do something with it.
        pass
    finally:
        teardown(firefox, firefox_pid, geckoview_pid, server, server_thread, graceful_shutdown)


def run_fathom_list(samples_directory):
    print('Running fathom-list to get list of sample filenames...', end='', flush=True)
    result = subprocess.run(['fathom-list', samples_directory, '-r'], capture_output=True)
    sample_filenames = result.stdout.decode()
    print('Done')
    return sample_filenames


def build_fathom_addons(trainees_file, fathom_fox_dir, fathom_trainees_dir):
    print('Building fathom addons for Firefox...', end='', flush=True)
    fathom_fox = create_xpi_for(pathlib.Path(fathom_fox_dir) / 'addon', 'fathom-fox')
    shutil.copyfile(trainees_file, f'{fathom_trainees_dir}/src/ruleset.js')
    # TODO: Cannot get this to run without using `shell=True`
    # TODO: Handle KeyboardInterrupt on this command. Perhaps getting rid of the shell part would do it?
    subprocess.run(f'yarn --cwd {fathom_trainees_dir} build', shell=True, capture_output=True)
    fathom_trainees = create_xpi_for(pathlib.Path(fathom_trainees_dir) / 'addon', 'fathom-trainees')
    print('Done')
    return fathom_fox, fathom_trainees


def create_xpi_for(directory, name):
    xpi_path = pathlib.Path(f'{name}.xpi')
    with zipfile.ZipFile(xpi_path, 'w', compression=zipfile.ZIP_DEFLATED) as xpi:
        for file in directory.rglob('*'):
            xpi.write(file, file.relative_to(directory))
    return str(xpi_path.absolute())


def run_file_server(samples_directory):
    print('Starting HTTP file server...', end='', flush=True)
    # TODO: Allow user to specify port?
    RequestHandler = partial(SilentRequestHandler, directory=samples_directory)
    server = HTTPServer(('localhost', 8000), RequestHandler)
    server_thread = Thread(target=server.serve_forever)
    server_thread.start()
    print('Done')
    return server, server_thread


def configure_firefox(fathom_fox, fathom_trainees, output_directory, show_browser):
    print('Configuring Firefox...', end='', flush=True)
    options = webdriver.FirefoxOptions()
    options.headless = not show_browser
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2)
    profile.set_preference("browser.download.dir", str(pathlib.Path(output_directory).absolute()))
    profile.set_preference("browser.cache.disk.enable", False)
    profile.set_preference("browser.cache.memory.enable", False)
    profile.set_preference("browser.cache.offline.enable", False)
    firefox = webdriver.Firefox(options=options, firefox_profile=profile)
    firefox.install_addon(fathom_fox, temporary=True)
    firefox.install_addon(fathom_trainees, temporary=True)
    print('Done')
    return firefox, firefox.capabilities['moz:processID'], firefox.service.process.pid


def run_vectorizer(firefox, sample_filenames):
    print('Configuring Vectorizer...', end='', flush=True)
    # Navigate to the vectorizer page
    # This sleep gives the prefs.js file time to update with the fathom addon info
    # TODO: Is there a less fragile way to ensure the file has been updated?
    time.sleep(1)
    prefs = (pathlib.Path(firefox.capabilities.get('moz:profile')) / 'prefs.js').read_text().split(';')
    uuids = next((line for line in prefs if 'extensions.webextensions.uuids' in line)).split(',')
    fathom_fox_uuid = next((line for line in uuids if 'fathomfox@mozilla.com' in line)).split('\\"')[3]
    firefox.get(f'moz-extension://{fathom_fox_uuid}/pages/vector.html')

    pages_text_area = firefox.find_element_by_id('pages')
    pages_text_area.send_keys(sample_filenames)

    # TODO: Look for new vector*.json file
    file_to_look_for = pathlib.Path(firefox.profile.default_preferences['browser.download.dir']) / 'vectors.json'
    number_of_samples = len(sample_filenames.splitlines())
    status_box = firefox.find_element_by_id('status')
    vectorize_button = firefox.find_element_by_id('freeze')
    completed_samples = 0
    print('Done')

    with progressbar(length=number_of_samples, label='Running Vectorizer...') as bar:
        vectorize_button.click()
        while not file_to_look_for.exists():
            if 'failed:' in status_box.text:
                error = extract_error_from(status_box.text)
                print(f'Vectorization failed with error:\n{error}')
                break
            now_completed_samples = len([line for line in status_box.text.splitlines() if line.endswith(': vectorized')])
            bar.update(now_completed_samples - completed_samples)
            completed_samples = now_completed_samples

    print(f'Vectors saved to {str(file_to_look_for)}')
    return firefox


def extract_error_from(status_text):
    lines = status_text.splitlines()
    for line in lines:
        if 'failed:' in line:
            return line
    raise RuntimeError(f'There was a vectorizer error, but we could not find it in {status_text}')


def teardown(firefox, firefox_pid, geckoview_pid, server, server_thread, graceful_shutdown):
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
