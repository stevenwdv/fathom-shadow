import {assert} from 'chai';

import {dom, out, props, rule, ruleset, type} from '../index';
import {numberOfMatches, page, sigmoid, staticDom, sum} from '../utils';


describe('Design-driving demos', function () {
    it('handles a simple series of short-circuiting rules', function () {
        // TODO: Short-circuiting isn't implemented yet. The motivation of this
        // test is to inspire engine so it's smart enough to run the highest-
        // possible-scoring type-chain of rules first and, if it succeeds,
        // omit the others.
        const doc = staticDom(`
            <meta name="hdl" content="HDL">
            <meta property="og:title" content="OpenGraph">
            <meta property="twitter:title" content="Twitter">
            <title>Title</title>
        `);
        const typeAndNote = type('titley').note(fnode => fnode.element.getAttribute('content'));
        const rules = ruleset([
            rule(dom('meta[property="og:title"]'),
                 typeAndNote.score(40)),
            rule(dom('meta[property="twitter:title"]'),
                 typeAndNote.score(30)),
            rule(dom('meta[name="hdl"]'),
                 typeAndNote.score(20)),
            rule(dom('title'),
                 typeAndNote.score(10).note(fnode => fnode.element.text)),
            rule(type('titley').max(), out('bestTitle'))
        ]);
        const facts = rules.against(doc);
        const node = facts.get('bestTitle')[0];
        assert.equal(node.scoreFor('titley'), sigmoid(40));
        assert.equal(node.noteFor('titley'), 'OpenGraph');
    });
});

// Right now, I'm writing features and using optimization algos to find their coefficients. Someday, we can stop writing features and have deep learning come up with them. TODO: Grok unsupervised learning, and apply it to OpenCrawl.
