const { expect } = require('chai');
const firefox = require('selenium-webdriver/firefox');
const webdriver = require('selenium-webdriver');
const { ancestors, isDomElement, isVisible, toDomElement } = require('../../utilsForFrontend');

describe('isVisible', () => {
    const options = new firefox.Options();
    options.headless();

    const driver = new webdriver.Builder()
        .forBrowser('firefox')
        .setFirefoxOptions(options)
        .build();
    describe('Unprivileged', () => {
        it('should return true when an element is visible', async () => {
            // TODO: put actual checks here
            await driver.get('http://localhost:8000/functional_test.html');
            await driver.wait(async () => {
                const readyState = await driver.executeScript('return document.readyState');
                return readyState === 'complete';
            });
            const isElementVisible = await driver.wait(async () => {
                return driver.executeScript(`
                    ${ancestors}
                    ${isDomElement}
                    ${toDomElement}
                    return (${isVisible}(document.getElementById("image")));
                `);
            });
            const expected = true;
            expect(isElementVisible).to.deep.equal(expected);
        });
    });

    after(async () => driver.quit());
});
