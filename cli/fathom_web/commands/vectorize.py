import pathlib
import subprocess
import time
import zipfile

from selenium import webdriver


def main(trainees_file, samples_directory, output_directory, headless_browser):
    sample_filenames = run_fathom_list(samples_directory)
    fathom_fox, fathom_trainees = build_fathom_addons(trainees_file)
    file_server = run_file_server(samples_directory)
    firefox = configure_firefox(fathom_fox, fathom_trainees, output_directory, headless_browser)
    firefox = set_up_vectorizer(firefox, sample_filenames)
    firefox = run_vectorizer(firefox)
    teardown(firefox, file_server)


def run_fathom_list(samples_directory):
    result = subprocess.run(['fathom-list', samples_directory, '-r'], capture_output=True)
    sample_filenames = result.stdout.decode()
    return sample_filenames


def build_fathom_addons(trainees_file):
    fathom_fox = create_xpi_for(pathlib.Path('C:/Users/Daniel/code/fathom-fox/addon'), 'fathom-fox')
    # TODO: Copy the trainees file into the trainees repo
    fathom_trainees = create_xpi_for(pathlib.Path('C:/Users/Daniel/code/fathom-trainees/addon'), 'fathom-trainees')
    return fathom_fox, fathom_trainees


def create_xpi_for(directory, name):
    xpi_path = pathlib.Path(f'{name}.xpi')
    with zipfile.ZipFile(xpi_path, 'w', compression=zipfile.ZIP_DEFLATED) as xpi:
        for file in directory.rglob('*'):
            xpi.write(file, file.relative_to(directory))
    return str(xpi_path.absolute())


def run_file_server(samples_directory):
    file_server = subprocess.Popen(
        ['fathom-serve', '-d', samples_directory],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    return file_server


def configure_firefox(fathom_fox, fathom_trainees, output_directory, headless_browser):
    options = webdriver.FirefoxOptions()
    options.headless = headless_browser
    # TODO: Use a profile with page caching disabled
    profile = webdriver.FirefoxProfile(r'C:\Users\Daniel\code\fathom\cli\fathom_web')
    profile.set_preference("browser.download.dir", output_directory)
    firefox = webdriver.Firefox(options=options, firefox_profile=profile)
    firefox.install_addon(fathom_fox, temporary=True)
    firefox.install_addon(fathom_trainees, temporary=True)
    return firefox


def set_up_vectorizer(firefox, sample_filenames):
    # Navigate to the vectorizer page
    # TODO: Give the prefs.js file time to update with the fathom addon info
    time.sleep(1)
    prefs = (pathlib.Path(firefox.capabilities.get('moz:profile')) / 'prefs.js').read_text().split(';')
    uuids = next((line for line in prefs if 'extensions.webextensions.uuids' in line)).split(',')
    fathom_fox_uuid = next((line for line in uuids if 'fathomfox@mozilla.com' in line)).split('\\"')[3]
    firefox.get(f'moz-extension://{fathom_fox_uuid}/pages/vector.html')

    pages_text_area = firefox.find_element_by_id('pages')
    pages_text_area.send_keys(sample_filenames)

    return firefox


def run_vectorizer(firefox):
    vectorize_button = firefox.find_element_by_id('freeze')
    vectorize_button.click()

    # TODO: Monitor progress
    # TODO: Wait until the vector file appears
    time.sleep(10)

    return firefox


def teardown(firefox, file_server):
    firefox.quit()
    # TODO: This doesn't actually stop fathom-serve from running on my machine???
    # TODO: Try to Popen something else (while True) and then kill it
    file_server.terminate()
    file_server.kill()
    file_server.wait()


if __name__ == '__main__':
    # TODO: Real CLI arguments
    main(
        trainees_file=None,
        samples_directory='C:/Users/Daniel/code/fathom-smoot/shopping/samples/training',
        output_directory=r'C:\Users\Daniel\temp_vectors',
        headless_browser=False,
    )
