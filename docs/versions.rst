===============
Version History
===============

unreleased
==========
* Make vectorization automatic. This largely obsoletes :command:`fathom-list` and :command:`fathom-serve`. We also remove the need to have 3 terminal tabs open, running :command:`yarn watch`, :command:`yarn browser`, and :command:`fathom-serve`. We remove the error-prone hardlinking of the ruleset into FathomFox, which breaks when git changes to a new branch with a different rulesets.js. We eliminate the possibility of forgetting to revectorize after changing a ruleset or samples. And finally, we pave the way to dramatically simplify our teaching and documentation.

  I tried to hew to the CLI design of the previous version of the trainer to keep things familiar. Basically, where you used to pass in a vector file, now feel free to pass in a directory of samples instead. Of course, if you do this, you'll also need to pass in your ruleset and the trainee ID so we can turn the dir into vectors. You can also keep passing in vector files if you want more control in some niche situation, like if you're trying to reproduce results from an old branch.

  Aggressive caching is in place to remove every possible impediment to using the auto-vectorization. We hash the ruleset and the sample HTML files (though not their resources) and compare them with stored hashes in a cached vector file, all of which takes well under a second. In addition, we cache the built FathomFox artifact so we need run npm or yarn or hit the network only when the user upgrades to a new version of the Fathom CLI tools.
* Add an ``--exclude`` option to the trainer to help with feature ablation.
* Fix an issue where the trainer would read vectors as non-UTF-8 on Windows.
* In the trainer output, make tag excerpts that contain wide Unicode chars fit in their columns.
* Don't show tag excerpts in :command:`fathom-test` by default.
* Add application/x-javascript and application/font-sfnt to :command:`fathom-extract`'s list of known MIME types.
* Merge FathomFox into the Fathom repo.
* Always use in-project virtualenvs. Drop support for external ones.

3.3
===
* Add to the trainer a readout of the average time per candidate tag examined.
* Replace trainer's per-page metrics, which were increasingly incoherent in Fathom 3, with per-tag ones. Per-page results were most useful back before Fathom could emit confidences. Now, most problems are concerned with per-tag accuracy, and problems that innately concern the page as a whole model it by scoring the ``<html>`` tag. Thus, we swap out the old per-page report for a per-tag one. This is a superset of the per-page report.
* Add a confidence-threshold customization option to fathom-train.
* Add :func:`element`, which lets you efficiently classify a single element. This is useful for applications in which you want Fathom to classify an element the user has selected, rather than scanning the whole page for candidates.

3.2.1
=====
* Make the cache that powers :func:`fnodeForElement` a ``WeakMap`` instead of a ``Map``. This will save memory if you keep a :class:`BoundRuleset` around a long time and DOM elements it has recognized get deleted from the page.
* Tweak some indentation in the trainer coefficient output.
* Upgrade Jinja to fix a security bug during doc build.

3.2
===
* Add :command:`fathom-test` tool for computing test-corpus accuracies.
* Add :command:`fathom-extract` to break down frozen pages into small enough pieces to check into GitHub.
* Add :command:`fathom-serve` to dodge the CORS errors that otherwise happen when loading extracted pages.
* Add a test harness for the Python code.
* Make :func:`isVisible` more correct and, in Firefox, 13% less janky.
* Add in-browser test harness for routines that need a real DOM.
* Revamp build process.
    * The makefile is now the One True Entrypoint for build stuff. There are no more npm scripts.
    * ``make test`` now runs all the tests, even the browser ones.
    * The browser tests now work on Windows.
    * ``make lint`` lints all languages. ``make py_lint`` and ``make js_lint`` lint 1 each.
    * ``make py_test`` and ``make js_test`` test 1 language each.
    * ``make`` takes care of making a venv for you (in the top level of the checkout) whenever it needs one. If you have an existing one activated before you make, it'll use yours instead.
    * New Python dependencies are automatically installed at the next ``make`` whenever they're added to requirements files or setup.py. Note that you'll see occasional spurious package installation attempts after you change branches, because the branch change causes the mod dates of files to be reset to the current time. But the attempts are reasonably quick and idempotent.
    * ``npm install`` is run automatically whenever package.json has been updated.
    * ``make doc`` from the top level now builds the docs.
    * A failing doc build will now fail the CI tests, so we don't get surprised on master anymore.
    * As a bonus, pip-installing fathom-web now works on Windows.
* Remove the Readability tests, which were too slow for their small utility.
* Remove the old optimizer, which was used only by the Readability tests.
* Add confidence intervals for false positives and false negatives in trainer.
* Add precision and recall numbers to trainer.
* Redesign Fathom bundle.
    * It now works as a part of Firefox itself.
    * It provides a way to access submodules like ``utils`` and ``clusters``, which node would typically import via filesystem paths.
    * Removed wu, the sole runtime dependency.
    * Drop unminified size from 237K to 105K.
* Add optional positive-sample weighting in trainer, for trading off between precision and recall.
* Add experimental support for deeper neural networks in trainer.
* Add recognition-time speed metrics to trainer.

.. warning::
   Backward-incompatible change: The ``clusters`` symbol exported from Fathom's top level is now a module containing all the :doc:`clustering` routines, not :func:`clusters` itself. The :func:`clusters` function is now at ``clusters.clusters``.

3.1
===
* Make BAD-element-labeling reliable when using FathomFox to debug rulesets.
* Add :command:`fathom-list` tool.
* Further optimize trainer: about 17x faster for a 60-sample corpus, with superlinear improvements for larger ones.

3.0
===
3.0 brings to bear simple neural nets, yielding...

* Faster training by several orders of magnitude
* More accurate training, guaranteed to converge to at least a local minimum
* Lower RAM use during training, by several orders of magnitude, uncapping corpus size. You should now be able to train on a corpus of 200,000 samples in 1GB of RAM.
* Confidence calculations for free. A score now represents the probability that a node belongs to a given type, informed by statistics (binary cross-entropy) run over the training corpus. If you've been using 0..1 fuzzy-logic value in your scoring callbacks, you're already most of the way there. Just strip away any manual weighting, and you're done.
* Coefficients have been moved into the framework: no more multiplying or exponentiating yourself. Bias values have been added to make confidences work out.

Essentially, 3.0 recasts the Fathom recognition problem as a classification one, turning each Fathom type into a perceptron and each rule into one of its input features. (We were close already, mathematically; we just had to switch multiplicative mixing to additive and add a bias.) Besides gaining the advantage of a great deal of existing literature and off-the-shelf tooling, it means Fathom is no longer practically limited to grabbing the single most likely member of a class from a page. It can grab all that exist, and confidence calculations inform the caller when to stop believing its guesses.

Backward-incompatible changes
-----------------------------

* :func:`conserveScore` is gone, at least for now.
* :func:`ruleset` takes its rules in an array rather than as varargs, making room to pass in coefficients and biases.
* Scores are no longer multiplied together. They are now added and then run through a :func:`sigmoid` function, which, combined with the math in the new trainer, makes them probabilities.

Other specific changes
----------------------

* The annealing optimizer is deprecated. Training is now purview of the commandline :command:`fathom-train` tool.
* Add :command:`fathom-unzip` and :command:`fathom-pick` tools for corpus management.
* Fix the bad-element labeling in FathomFox (by fixing a file compiled into fathom-trainees).
* Add utility functions :func:`isVisible`, :func:`rgbaFromString`, :func:`saturation`, :func:`sigmoid`, and :func:`linearScale`.
* Allow :func:`euclidean` to take HTML elements in addition to fnodes.
* Accept boolean return values from :func:`score` callbacks, which get cast to 0 or 1.


2.8
===
* Add the ability to label wrongly recognized elements to fathom-trainees imports, for use with FathomFox 2.3 and above.

2.7
===
* Add support for pluggable success functions in fathom-trainees.

2.6
===
* Factor some boilerplate out of the fathom-trainees web extension into Fathom
  itself. Now, after you fork fathom-trainees, you'll rarely have to change
  anything to stay up to date.

2.5
===
* Add experimental :func:`nearest` function, our first primitive for tying together compound entities.
* Add :func:`euclidean` distance function, a strong source of signal on rendered pages.
* Improve speed of :func:`rootElement`.

2.4
===
* Fathom is now a `dual-mode <https://medium.com/@giltayar/native-es-modules-in-nodejs-status-and-future-directions-part-i-ee5ea3001f71>`_ package, exposing both ES6 modules and equivalent CommonJS ones. This lets us ``import`` Fathom into modern ES6 projects and enjoy rollup's dead-code elimination while still remaining ``require()``-able by old CommonJS code.
* Nudge people toward `FathomFox <https://addons.mozilla.org/en-US/firefox/addon/fathomfox/>`_ rather than writing custom code against the optimization framework.

.. warning::
   Backward-incompatible change: There is no longer a ``utils`` property exported by Fathom's top level. Instead, add imports like ``import {ancestors} from 'fathom-web/utilsForFrontend';`` or ``import {staticDom} from 'fathom-web/utilsForBackend';`` or the equivalent ``require()`` calls. There still exists a combined ``utils`` module importable from ``fathom-web/utils`` as well, though rollup's dead-code elimination has trouble with it.

2.3
===
* Add Corpus Framework to further assist you in doing ruleset optimization.
* Improve the optimizer's speed by about 4x.
* Change jsdom from a devDependency to a proper dependency. It's still used only from :func:`staticDom`, which is generally used only while authoring a ruleset. Bundlers (used to pack Fathom into a webextension, for instance) should throw it away in their dead code elimination phase. See, for example, the included experimental `rollup <https://rollupjs.org/>`_ configuration.

.. warning::
   Backward-incompatible change: :func:`attributesMatch` now takes an HTML element as its first parameter, not a :class:`Fnode`. This makes it usable in more situations. Bring your uses up to date by sticking ``.element`` after your first params.

2.2
===
* Generalize the computation of rule prerequisites, eliminating many special cases. As a bonus, `and(type('A')) -> type('A')` now gets an optimal query plan.
* Add an `additionalCost` coefficient to :func:`distance` so you can hook your own math into it.
* Add :func:`when` call for filtering by arbitrary conditions in left-hand sides.
* Add :func:`attributesMatch` utility function for applying tests to element attribute values.
* Update to the latest (backward-incompatible) version of jsdom in the test harness, and modify callsite accordingly.
* Exclude documentation source from the built package, dropping its unpacked size by 90K.

2.1
===
Clustering as a first-class construct, full docs, and automatic optimization of score coefficients headline this release.

Clustering
----------
* Make clustering available *within* a ruleset rather than just as an imperative sidecar, via :func:`bestCluster`.
* Let costs be passed into :func:`distance` and :func:`clusters` so we can tune them per ruleset.
* Make clustering about 26% faster.
* Let :func:`clusters` and :func:`distance` optionally take :term:`fnodes<fnode>` instead of raw DOM nodes.
* Revise clustering :func:`distance` function to not crash if node A is within node B and to return MAX_VALUE if there is any container relationship. This should make Readability-like clustering algorithms work out nicely, since we're interested only in the outer nodes. Pushing the inner ones off to the edge of the world removes them from being considered when we go to paste the largest cluster back together.
* Skip the expensive stride node computation during clustering if you pass 0 as its coefficient.

More
----
* Add nice documentation using Sphinx.
* Add score optimization machinery based on simulated annealing. This seems to do well on stepwise functions, where Powell's and other continuous methods get hung up on the flats.
* Add a Readability-alike content-extraction ruleset as an example.
* Add .babelrc file so Fathom can be used as a dep in webpack/Babel projects. (jezell)
* Add :func:`allThrough`, which comes in handy for sorting the nodes of a cluster.
* Get the Chrome debugger working with our tests again (``make debugtest``).
* Officially support operating on DOM subtrees (which did work previously).
* Fix :func:`linkDensity` utility function that wouldn't run. Remove hard-coded type from it.

2.0
===
The focii for 2.0 are syntactic sugar and support for larger, more powerful rulesets that can operate at higher levels of abstraction. From these priorities spring all of the following:

* "Yankers" or aggregate functions are now part of the ruleset: :func:`max` and :func:`and` for now, with more in a later release. This in-ruleset mapping from the fuzzy domain of scores back to the boolean domain of types complements the opposite mapping provided by :func:`score` and lets ruleset authors choose between efficiency and completeness. It also saves imperative programming where maxima are referenced from more than one place. Finally, it opens the door to automatic optimization down the road.
* Answers are computed lazily, running only the necessary rules each time you call :func:`~BoundRuleset.get` and caching intermediate results to save work on later calls. We thus eschew 1.x's strategy of emitting the entire scored world for the surrounding imperative program to examine and instead expose a factbase that acts like a lazy hash of answers. This allows for large, sophisticated rulesets that are nonetheless fast and can be combined to reuse parts (see :func:`Ruleset.rules()`). Of course, if you still want to imbibe the entire scored corpus of nodes in your surrounding program, you can simply yank all nodes of a type using the :func:`type` yanker: just point it to :func:`out`, and the results will be available from the outside: ``rule(type('foo'), out('someKey'))``.
* We expand the domain of concern of a ruleset from a single dimension ("Find just the ads!") to multiple ones ("Find the ads and the navigation and the products and the prices!"). This is done by making scores and notes per-type.
* The rule syntax has been richly sugared
  to…

    * be shorter and easier to read in most cases
    * surface more info declaratively so the query planner can take advantage of it (:func:`props` is where the old-style ranker functions went, but avoid them when you don't need that much power, and you'll reap a reward of concision and efficiently planned queries)
    * allow you to concisely factor up repeated parts of complex LHSs and RHSs
* The new experimental :func:`and` combinator allows you to build more powerful abstractions upon the black boxes of types.
* Test coverage is greatly improved, and eslint is keeping us from doing overtly stupid things.

Backward-incompatible changes
-----------------------------

* RHSs (née ranker functions) can no longer return multiple facts, which simplifies both syntax and design. For now, use multiple rules, each emitting one fact, and share expensive intermediate computations in notes. If this proves a problem in practice, we'll switch back, but I never saw anyone return multiple facts in the wild.
* Scores are now per-type. This lets you deliver multiple independent scores per ruleset. It also lets Fathom optimize out downstream rules in many cases, since downstream rules' scores no longer back-propagate to upstream types. Per-type scores also enable complex computations with types as composable units of abstraction, open the possibility of over-such-and-such-a-score yankers, and make non-multiplication-based score components a possibility. However, the old behavior remains largely available via :func:`conserveScore`.
* Flavors are now types.

1.1.2
=====
* Stop assuming querySelectorAll() results conform to the iterator protocol. This fixes compatibility with Chrome.
* Add test coverage reporting.

1.1.1
=====
* No changes. Just bump the version in an attempt to get the npm index page to update.

1.1
===
* Stop using ``const`` in ``for...of`` loops. This lets Fathom run within Firefox, which does not allow this due to a bug in its ES implementation.
* Optimize DistanceMatrix.numClusters(), which should make clustering a bit faster.

1.0
===
* Initial release
