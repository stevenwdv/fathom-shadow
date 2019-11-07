import os
import pathlib
import shutil
import subprocess
import time
import zipfile

from click import argument, command, option, Path, progressbar
from selenium import webdriver


# TODO: ctrl+c'ing out of this on the command prompt doesn't stop the subprocesses???
@command()
@argument('trainees_file', type=str)
@argument('samples_directory', type=Path(exists=True, file_okay=False))
@option('--output-directory', '-o', type=Path(exists=True, file_okay=False), default=os.getcwd())
@option('--show-browser', '-s', default=False, is_flag=True)
def main(trainees_file, samples_directory, output_directory, show_browser):
    sample_filenames = run_fathom_list(samples_directory)
    fathom_fox, fathom_trainees = build_fathom_addons(trainees_file)
    file_server = run_file_server(samples_directory)
    firefox = configure_firefox(fathom_fox, fathom_trainees, output_directory, show_browser)
    firefox = run_vectorizer(firefox, sample_filenames)
    teardown(firefox, file_server)


def run_fathom_list(samples_directory):
    print('Running fathom-list to get list of sample filenames...', end='', flush=True)
    result = subprocess.run(['fathom-list', samples_directory, '-r'], capture_output=True)
    sample_filenames = result.stdout.decode()
    print('Done')
    return sample_filenames


# TODO: Get rid of these paths
def build_fathom_addons(trainees_file):
    print('Building fathom addons for Firefox...', end='', flush=True)
    fathom_fox = create_xpi_for(pathlib.Path('C:/Users/Daniel/code/fathom-fox/addon'), 'fathom-fox')
    # TODO: Assume the file is called ruleset.js
    shutil.copyfile(trainees_file, 'C:/Users/Daniel/code/fathom-trainees/src/ruleset_factory.js')
    # TODO: Cannot get this to run without using `shell=True`
    subprocess.run('yarn --cwd C:/Users/Daniel/code/fathom-trainees/ build', shell=True, capture_output=True)
    fathom_trainees = create_xpi_for(pathlib.Path('C:/Users/Daniel/code/fathom-trainees/addon'), 'fathom-trainees')
    print('Done')
    return fathom_fox, fathom_trainees


def create_xpi_for(directory, name):
    xpi_path = pathlib.Path(f'{name}.xpi')
    with zipfile.ZipFile(xpi_path, 'w', compression=zipfile.ZIP_DEFLATED) as xpi:
        for file in directory.rglob('*'):
            xpi.write(file, file.relative_to(directory))
    return str(xpi_path.absolute())


def run_file_server(samples_directory):
    print('Starting HTTPS file server...', end='', flush=True)
    # TODO: Refactor the serving code to a thread and use the thread here
    file_server = subprocess.Popen(
        ['fathom-serve', '-d', samples_directory],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print('Done')
    return file_server


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
    return firefox


def run_vectorizer(firefox, sample_filenames):
    print('Configuring Vectorizer...', end='', flush=True)
    # Navigate to the vectorizer page
    # TODO: Give the prefs.js file time to update with the fathom addon info
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


def teardown(firefox, file_server):
    firefox.quit()
    # TODO: This doesn't actually stop fathom-serve from running on my machine???
    file_server.terminate()
    file_server.kill()
    file_server.wait()
