==================================
The Fathom Trainer and Other Tools
==================================

This is the commandline trainer for `Fathom <https://mozilla.github.io/fathom/>`_, which itself is a supervised-learning system for recognizing parts of web pages. It also includes other commandline tools for ruleset development, like ``fathom-unzip``, ``fathom-pick``, and ``fathom-list``. `See docs for the trainer here <http://mozilla.github.io/fathom/training.html#running-the-trainer>`_.

Version History
===============

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
