/**
 * Boilerplate factored out of fathom-trainees so, as much as possible, the
 * only thing left in that web extension is the ruleset developer's code
 */

/** Handle messages that come in from the FathomFox webext. */
function handleExternalMessage(request, sender, sendResponse) {
    if (request.type === 'rulesetSucceededOnTabs') {
        // Run a given ruleset on a given set of tabs, and return an array
        // of bools saying whether they got the right answer on each.
        return Promise.all(request.tabIds.map(
            tabId => browser.tabs.sendMessage(
                tabId,
                {type: 'rulesetSucceeded',
                 traineeId: request.traineeId,
                 coeffs: request.coeffs})));
    } else if (request.type === 'traineeKeys') {
        // Return an array of IDs of rulesets we can train.
        sendResponse(Array.from(trainees.keys()));
    } else if (request.type === 'trainee') {
        // Return all the properties of a trainee that can actually be
        // serialized and passed over a message.
        const trainee = Object.assign({}, trainees.get(request.traineeId));  // shallow copy
        delete trainee.rulesetMaker;  // unserializeable
        sendResponse(trainee);
    }
}

export function initBackgroundScript() {
    browser.runtime.onMessageExternal.addListener(handleExternalMessage);
}

/** React to commands sent from the background script. */
async function dispatch(request) {
    switch (request.type) {
        case 'rulesetSucceeded':
            // Run the trainee ruleset of the given ID with the given coeffs
            // over the document, and report whether it found the right
            // element.
            const rules = trainees.get(request.traineeId).rulesetMaker(request.coeffs);
            const facts = rules.against(window.document);
            // Assume the out() key and the data-fathom attr are both identical
            // to the key of the trainee in the map.
            const found = facts.get(request.traineeId);
            if (found.length >= 1) {
                const fnode = found[0];  // arbitrary pick
                if (fnode.element.getAttribute('data-fathom') === request.traineeId) {
                    return true;
                }
                //console.log(urlFilename(window.location.href), ": found wrong answer class=", fnode.element.getAttribute('class'), 'id=', fnode.element.getAttribute('id'));
            } else {
                //console.log(urlFilename(window.location.href), ": found nothing.");
            }
            return false;
            break;  // belt, suspenders
    }
    return Promise.resolve({});
}

export function initContentScript() {
    browser.runtime.onMessage.addListener(dispatch);
}
