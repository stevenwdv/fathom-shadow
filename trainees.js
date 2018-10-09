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

/**
 * The default success function for a ruleset: succeed if the found element has
 * a data-fathom attribute equal to the traineeId. We arbitrarily use the first
 * found node if multiple are found.
 */
function foundLabelIsTraineeId(facts, traineeId) {
    const found = facts.get(traineeId);
    return found.length ? found[0].element.dataset.fathom === traineeId : false;
}

/** React to commands sent from the background script. */
async function dispatch(request) {
    switch (request.type) {
        case 'rulesetSucceeded':
            // Run the trainee ruleset of the given ID with the given coeffs
            // over the document, and report whether it found the right
            // element.
            const trainee = trainees.get(request.traineeId);
            const rules = trainee.rulesetMaker(request.coeffs);
            const facts = rules.against(window.document);
            const successFunc = trainee.successFunction || foundLabelIsTraineeId;
            return successFunc(facts, request.traineeId);
            break;  // belt, suspenders
    }
    return Promise.resolve({});
}

export function initContentScript() {
    browser.runtime.onMessage.addListener(dispatch);
}
