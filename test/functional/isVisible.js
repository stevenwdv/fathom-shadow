const { expect } = require('chai');
const firefox = require('selenium-webdriver/firefox');
const webdriver = require('selenium-webdriver');
const { ancestors, isDomElement, isVisible, toDomElement } = require('../../utilsForFrontend');

const WAIT_MS = 10000;
const TEST_PAGE_URL = 'http://localhost:8000/isVisible.html';

describe('isVisible', () => {
    const options = new firefox.Options();
    options.headless();

    const driver = new webdriver.Builder()
        .forBrowser('firefox')
        .setFirefoxOptions(options)
        .build();

    describe('Unprivileged', () => {
        it('Should return false when an element is hidden', async () => {
            const hiddenElementIds = [
                'not-visible-1',
                'not-visible-2',
                'not-visible-3',
                'not-visible-4',
                'not-visible-5',
                'not-visible-6',
                'not-visible-7',
                'not-visible-8',
                'not-visible-9',
                'not-visible-10',
                'not-visible-11',
                'not-visible-12',
            ];
            await driver.get(TEST_PAGE_URL);
            await driver.wait(async () => {
                const readyState = await driver.executeScript('return document.readyState');
                return readyState === 'complete';
            }, WAIT_MS, `Page did not finish loading after ${WAIT_MS} ms`);

            for (const id of hiddenElementIds) {
                const isElementVisible = await driver.executeScript(`
                    ${ancestors}
                    ${isDomElement}
                    ${toDomElement}
                    return ${isVisible}(document.getElementById('${id}'));
                `);
                expect(
                    isElementVisible,
                    `isVisible should return false for element with id '${id}'.`
                ).to.be.false;
            }
        });
    });

    after(async () => driver.quit());
});
