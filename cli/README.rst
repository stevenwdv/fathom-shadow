========================
Fathom Commandline Tools
========================

This is the commandline trainer for `Fathom <https://mozilla.github.io/fathom/>`_, which itself is a supervised-learning system for recognizing parts of web pages. This package also includes other tools for ruleset development, like ``fathom-extract``, ``fathom-pick``, and ``fathom-test``. `See docs for the trainer here <http://mozilla.github.io/fathom/training.html#running-the-trainer>`_.

Version History
===============

3.5
  * Add ``fathom-histogram`` tool for examining the shapes of individual rule values.
  * Notice prematurely pruned elements during vectorization, and take them into account in training and testing metrics. Tag-level diagnostics in the trainer will show "pruned" for these elements so you can adjust your ``dom()`` calls if desired.
  * Replace F1 score with the Matthews Correlation Coefficient. MCC doesn't assume same-sized classes (which Fathom problems never have) and also is not sensitive to which side of the problem you call "positive".
  * Default to early stopping whenever a validation corpus is provided to ``fathom-train``. After all, if you provide a validation corpus, it makes sense that we do something useful with it.
  * Add some ``fathom-extract`` MIME types we discovered in a recent corpus.
  * Fix remaining divide-by-zero corner cases in the metrics code. (These would show up in toy corpora that were entirely lacking either positive or negative samples.)

3.4.1
  * Add confusion matrices to ``fathom-train`` and ``fathom-test`` readouts.
  * Catch JS syntax errors and other compile-time errors, and report them in ``fathom-train`` and ``fathom-test``.
  * Catch errors due to the absence of prerequisite commands like ``npm``.
  * Catch and nicely report HTTP server errors during autovectorization rather than just spewing tracebacks. Add ``--delay`` option to ``fathom-train`` and ``fathom-test`` to work around them.
  * Don't spit out ``nan`` for precision or F1 when we don't get any samples right.

3.4
  * Make vectorization automatic. This largely obsoletes ``fathom-list`` and ``fathom-serve``. We also remove the need to have 3 terminal tabs open, running ``yarn watch``, ``yarn browser``, and ``fathom-serve``. We remove the error-prone hardlinking of the ruleset into FathomFox, which breaks when git changes to a new branch with a changed ruleset file. We eliminate the possibility of forgetting to revectorize after changing a ruleset or samples. And finally, we pave the way to dramatically simplify our teaching and documentation.

    We tried to hew to the CLI design of the previous version of the trainer to keep things familiar. Basically, where you used to pass in a vector file, now feel free to pass in a directory of samples instead. If you do, you'll also need to pass in your ruleset file and the trainee ID so we can turn the samples into vectors behind the scenes. You can also keep passing in vector files manually if you want more control in some niche situation, like if you're trying to reproduce results from an old branch.

    Aggressive caching is in place to remove every possible impediment to using auto-vectorization. We store hashes of the ruleset and samples so we can tell when revectorizing is necessary. We also cache a built copy of FathomFox (embedded in the Python package) so we don't need to run npm or yarn or hit the network again until you upgrade to a new version of the Fathom CLI tools.
  * Add an ``--exclude`` option to the trainer to help with feature ablation.
  * Fix an issue where the trainer would read vectors as non-UTF-8 on Windows.
  * In the trainer output, make tag excerpts that contain wide Unicode chars fit in their columns.
  * Don't show tag excerpts in ``fathom-test`` by default.
  * Add application/x-javascript and application/font-sfnt to ``fathom-extract``'s list of known MIME types.
  * ``fathom-list``, though no longer needed in most cases, is now always recursive. It has also learned to ignore ``resources`` directories.
  * ``fathom-unzip`` is gone.

3.3
  * Add to the trainer a readout of the average time per candidate tag examined.
  * Replace trainer's per-page metrics, which were increasingly incoherent in Fathom 3, with per-tag ones. Per-page results were most useful back before Fathom could emit confidences. Now, most problems are concerned with per-tag accuracy, and problems that innately concern the page as a whole model it by scoring the ``<html>`` tag. Thus, we swap out the old per-page report for a per-tag one. This is a superset of the per-page report.
  * Add a confidence-threshold customization option to fathom-train.

3.2
  * Add ``fathom-test`` tool for computing test-corpus accuracies.
  * Add ``fathom-extract`` to break down frozen pages into small enough pieces to check into GitHub.
  * Add ``fathom-serve`` to dodge the CORS errors that otherwise happen when loading extracted pages.
  * Add a test harness for the Python code.
  * Add confidence intervals for false positives and false negatives in trainer.
  * Add precision and recall numbers to trainer.
  * Add optional positive-sample weighting in trainer, for trading off between precision and recall.
  * Add experimental support for deeper neural networks in trainer.
  * Add recognition-time speed metrics to trainer.

3.1
  * Add ``fathom-list`` tool.
  * Further optimize trainer: about 17x faster for a 60-sample corpus, with superlinear improvements for larger ones.

3.0
  * Move to Fathom repo.
  * Add ``fathom-unzip`` and ``fathom-pick``.
  * Switch to the Adam optimizer, which is significantly more turn-key, to the point where it doesn't need its learning-rate decay set manually.
  * Tolerate pages for which no candidate nodes were collected.
  * Add 95% CI for per-page training accuracy.
  * Add validation-guided early stopping.
  * Revise per-page accuracy calculation and display.
  * Shuffle training samples before training.
  * Add false-positive and false-negative numbers to per-tag metrics.

3.0a1
  * First release, intended for use with Fathom itself 3.0 or later
