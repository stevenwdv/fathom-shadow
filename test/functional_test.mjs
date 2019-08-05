const { expect } = require('chai');
const firefox = require('selenium-webdriver/firefox');
const webdriver = require('selenium-webdriver'),
    By = webdriver.By,
    until = webdriver.until,
    Key = webdriver.Key;

describe('isVisible', () => {
    const options = new firefox.Options();
    // TODO: also add options.setBinary('path/to/binary'); get from englehardt
    options.headless();

    const driver = new webdriver.Builder()
        // TODO: can set version and platform in forBrowser
        .forBrowser('firefox')
        // .setFirefoxOptions(options)
        .build();
    describe('Unprivileged', () => {
        it('should return false when...TODO', async () => {
            // TODO: put actual checks here
            await driver.get('https://developer.mozilla.org/');
            await driver.findElement(By.id('home-q')).sendKeys('testing', Key.RETURN);
            await driver.wait(until.titleIs('Search Results for "testing" | MDN'));
            await driver.wait(async () => {
                const readyState = await driver.executeScript('return document.readyState');
                return readyState === 'complete';
            });
            const input = 2;
            const expected = 2;
            expect(input).to.deep.equal(expected);
        });
    });

    after(async () => driver.quit());
});
