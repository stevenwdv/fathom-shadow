==================================
The Fathom Trainer and Other Tools
==================================

This is the commandline trainer for `Fathom <https://mozilla.github.io/fathom/>`_, which itself is a supervised-learning system for recognizing parts of web pages. It also includes other commandline tools for ruleset development, like ``fathom-unzip``, ``fathom-pick``, and ``fathom-list``. `See docs for the trainer here <http://mozilla.github.io/fathom/training.html#running-the-trainer>`_.

Version History
===============

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
