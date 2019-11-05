/**
 * Boilerplate factored out of fathom-trainees so, as much as possible, the
 * only thing left in that web extension is the ruleset developer's code
 */
import {type} from './side';

/** Handle messages that come in from the FathomFox webext. */
function handleBackgroundScriptMessage(request, sender, sendResponse) {
    if (request.type === 'rulesetSucceededOnTabs') {
        // Run a given ruleset on a given set of tabs, and return an array
        // of bools saying whether they got the right answer on each.
        return Promise.all(request.tabIds.map(
            tabId => browser.tabs.sendMessage(
                tabId,
                {type: 'rulesetSucceeded',
                 traineeId: request.traineeId,
                 coeffs: request.coeffs})));
    } else if (request.type === 'vectorizeTab') {
        const vector = browser.tabs.sendMessage(request.tabId, request);
        sendResponse(vector);
    } else if (request.type === 'labelBadElement') {
        // Just forward these along to the correct tab:
        browser.tabs.sendMessage(request.tabId, request)
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
    browser.runtime.onMessageExternal.addListener(handleBackgroundScriptMessage);
}

/**
 * The default success function for a ruleset: succeed if the found element has
 * a data-fathom attribute equal to the traineeId. We arbitrarily use the first
 * found node if multiple are found.
 *
 * Meanwhile (and optionally), if the wrong element is found, return it in
 * ``moreReturns.badElement`` so the tools can show it to the developer. If
 * there's a finer-grained cost than simply a did-succeed boolean, return it in
 * ``moreReturns.cost``--though beware that this cost should include the
 * success or failure as a high-order component, since the optimizer looks only
 * at cost.
 */
function foundLabelIsTraineeId(facts, traineeId, moreReturns) {
    // TODO: Replace with the guts of successAndScoreGap if it proves good.
    const found = facts.get(traineeId);
    if (found.length) {
        const firstFoundElement = found[0].element;
        if (firstFoundElement.dataset.fathom === traineeId) {
            return true;
        } else {
            moreReturns.badElement = firstFoundElement;
            return false;
        }
    }
}

/**
 * A mindless factoring-out over the rulesetSucceeded and labelBadElement
 * content-script messages
 */
function runTraineeOnThisDocument(traineeId, serializedCoeffs, moreReturns) {
    // Run the trainee ruleset of the given ID with the given coeffs
    // over the document, and report whether it found the right
    // element.
    const trainee = trainees.get(traineeId);
    const facts = trainee.rulesetMaker('dummy').against(window.document);
    facts.setCoeffsAndBiases(serializedCoeffs);
    const successFunc = trainee.successFunction || foundLabelIsTraineeId;
    const didSucceed = successFunc(facts, traineeId, moreReturns);
    return {didSucceed, cost: moreReturns.cost || (1 - didSucceed)};
}

/** React to commands sent from the background script. */
async function handleContentScriptMessage(request) {
    if (request.type === 'rulesetSucceeded') {
        try {
            return runTraineeOnThisDocument(request.traineeId, request.coeffs, {});
        } catch(exc) {
            throw new Error('Error on ' + window.location + ': ' + exc);
        }
    } else if (request.type === 'labelBadElement') {
        // Run the ruleset on this document, and, if it fails, stick an
        // attr on the element it spuriously found, if any. This seems the
        // least bad way of doing this. Actually constructing a path to the
        // element to pass back to the caller would require attaching
        // simmer.js to the page in the trainee extension and then removing
        // it again, as well as a great deal of messaging. You have to have
        // the devtools panel open to freeze the page, so you'll be staring
        // right at the BAD labels, not adding them undetectably.
        const moreReturns = {};
        const results = runTraineeOnThisDocument(request.traineeId, request.coeffs, moreReturns);

        // Delete any old labels saying "BAD [this trainee]" that might be
        // lying around so we don't mix the old with the quite-possibly-
        // revised:
        const badLabel = 'BAD ' + request.traineeId;
        for (const oldBadNode of document.querySelectorAll('[data-fathom="' + badLabel.replace(/"/g, '\\"') + '"]')) {
            delete oldBadNode.dataset.fathom;
        }

        if (!results.didSucceed && moreReturns.badElement) {
            if (!('fathom' in moreReturns.badElement.dataset)) {
                // Don't overwrite any existing human-provided labels, lest we
                // screw up future training runs.
                moreReturns.badElement.dataset.fathom = badLabel;
            }
        }
    } else if (request.type === 'vectorizeTab') {
        // Return an array of unweighted scores for each element of a type,
        // plus an indication of whether it is a target element. This is useful
        // to feed to an external ML system. The return value looks like this:
        //
        //     {filename: '3.html',
        //      isTarget: true,
        //      features: [['ruleName1', 4], ['ruleName2', 3]]}
        //
        // We assume, for the moment, that the type of node you're interested
        // in is the same as the trainee ID.
        const traineeId = request.traineeId;
        const trainee = trainees.get(traineeId);
        const boundRuleset = trainee.rulesetMaker('dummy').against(window.document);
        const fnodes = boundRuleset.get(type(trainee.vectorType));
        const path = window.location.pathname;
        const perNodeStuff = fnodes.map(function featureVectorForFnode(fnode) {
            const scoreMap = fnode.scoresSoFarFor(trainee.vectorType);
            return {
                isTarget: fnode.element.dataset.fathom === traineeId,
                // Loop over ruleset.coeffs in order, and spit out each score:
                features: Array.from(trainee.coeffs.keys()).map(ruleName => scoreMap.get(ruleName))
            };
        });
        return {filename: path.substr(path.lastIndexOf('/') + 1),
                nodes: perNodeStuff};
    }
    return Promise.resolve({});
}

export function initContentScript() {
    browser.runtime.onMessage.addListener(handleContentScriptMessage);
}
