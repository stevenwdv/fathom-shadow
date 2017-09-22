=========
Basic Use
=========

Where It Works
==============

Fathom works against the DOM API, so you can use it server-side with ``jsdom`` (which the test harness uses) or another implementation, or you can embed it in a browser and pass it a native DOM. You can also pass in a subtree of a DOM.

To use it in a `node.js <https://nodejs.org/en/>`_ project, add ``fathom-web`` to your package.json file as a dependency:

.. code-block:: js

   ...
   "dependencies": {
      "fathom-web": "^2.1.0"
   },
   ...

Run ``npm install`` to download any install Fathom, and then import the symbols you need:

.. code-block:: js

   const {rule, ruleset, dom, out, and, atMost, conserveScore, max, note, props, score, type, typeIn} = require('fathom-web');

All the public symbols are in the top-level fathom-web package.

Kate Hudson has put together `a Firefox add-on that lets you see the results of old Fathom 1.0 rulesets against the currently loaded page <https://github.com/k88hudson/ffmetadata>`_, as a new pane of the Developer Tools.

Michael Comella `got Fathom 1.0 running on Android <https://github.com/mcomella/fathom-android-experiments>`_, returning results to Java via a WebView.

The Language
============

Think of Fathom as a tiny programming language that recognizes the significant parts of DOM trees by means of its programs, Fathom rulesets. A ruleset is an unordered bag of rules, each of which takes in DOM nodes and annotates them with scores, types, and notes to influence future rules. At the end of the chain of rules, out pops one or more pieces of output—typically high-scoring nodes of certain types—to inform the surrounding imperative program.

This simple ruleset finds DOM nodes that could contain a useful page title and scores them according to how likely that is:

.. code-block:: js

   const rules = ruleset(
       // Give any title tag the (default) score of 1, and tag it as title-ish:
       rule(dom('title'), type('titley')),

       // Give any OpenGraph meta tag a score of 2, and tag it as title-ish as well:
       rule(dom('meta[property="og:title"]'), type('titley').score(2)),

       // Take all title-ish things, and punish them if they contain
       // navigational claptrap like colons or dashes:
       rule(type('titley'), score(fnode => containsColonsOrDashes(fnode.element) ? .5 : 1)),

       // Offer the max-scoring title-ish node under the output key "title":
       rule(type('titley').max(), out('title'))
   );

See below for a full definition of `type`, `score`, and the rest of the Fathom language.

Rules, Sides, and Flows
=======================

Each rule is shaped like ``rule(left-hand side, right-hand side)``. The *left-hand side* (LHS) pulls in one or more DOM nodes as input: either ones that match a certain CSS selector (:func:`dom()`) or ones tagged with a certain type by other rules (:func:`type()`). The *right-hand side* (RHS) then decides what to do with those nodes:

* Assigning an additional type
* Scaling the score
* Scribbling a note on it
* Or some combination thereof

Envision the rule as a pipeline, with the DOM flowing in one end, nodes being picked and passed along to RHSs which twiddle them, and then finally falling out right side, where they might flow into other rules whose LHSs pick them up. It's snakey sort of flow.

This rule, which takes in :term:`fnodes<fnode>` that have previously been identified as text containers and adds a word-count annotation... ::

    rule(type('textContainer'), type('countedWords').note(fnode => fnode.element.textContent.split(/\s+/).length))

...can be thought of as...

.. code-block:: none

    textContainer fnodes emitted        assign "countedWords" type
         from other rules          ->        and a word count        ->   changed nodes --\
                                                                                          |
     ____________________________________________________________________________________ /
    /
    |
    \->  other rules' LHSs         ->   ...                          ->   ...          -->  ...

Remember that Fathom's rulesets are unordered, so any rule's output can flow into any other rule, not just ones that happen to come lexically after it.

Pulling Out Answers
===================

Once the ruleset is defined, run a DOM tree through it:

.. code-block:: js

   const JSDOM = require('jsdom').JSDOM;  // jsdom v10 and up
   const dom = new JSDOM("<html><head>...</html>").window.document;
   // Tell the ruleset which DOM to run against, yielding a factbase about the document:
   const facts = rules.against(dom);

After running a tree or subtree through, pull the answers out of the factbase: in this case, we want the note containing the max-scoring title, which the ruleset conveniently stores under the "title" output key:

.. code-block:: js

   const bestTitleFnode = facts.get('title');

A more developed ruleset would expose the title itself using :func:`through`. But in this case, you would pull it out manually using the :doc:`methods on fnodes<fnodes>`.

If the ruleset doesn't anticipate the output you want, you can ask for it more explicitly by passing a full LHS to :func:`~BoundRuleset.get`. For example, if you simply want all the title-ish things so you can do further computation on them...

.. code-block:: js

   const allTitleFnodes = facts.get(type('titley'));

Or if you have a reference to a DOM element from elsewhere in your program, you can look up the scores, types, and notes Fathom attached to it:

.. code-block:: js

   const fnode = facts.get(dom.getElementById('aTitle'));

.. warning::

    jsdom likes to load external resources, like CSS and JS, referenced from the HTML you feed it. This is, of course, slow, a security leak, and unhelpful for our purposes. This longer spelling will keep it from doing that::

        const {jsdom} = require('jsdom/lib/old-api');
        const dom = jsdom.jsdom("<html><head>...</html>",
                                {features: {ProcessExternalResources: false}});

    We're targeting jsdom version 10 and up here: particularly, its `old API <https://github.com/tmpvar/jsdom/blob/master/lib/old-api.md>`_, which is so far the only one that lets you control resource loading.
