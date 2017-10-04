/* Utilities for use solely by tests */
const {jsdom} = require('jsdom/lib/old-api');

/**
 * Parse an HTML doc, and return a DOM-compliant interface to it. Do not
 * execute any of its inline scripts.
 */
function staticDom(html) {
    return jsdom(html, {features: {ProcessExternalResources: false}});
}

module.exports = {
    staticDom
};
