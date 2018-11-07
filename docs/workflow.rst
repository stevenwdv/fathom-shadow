==================
Authoring Workflow
==================

As a bridge between the language introduction and the API reference, here is a high-level overview of how to develop a Fathom ruleset.

Sources of Signal
=================

What sorts of rules should you write? In short, ones that express simple, atomic "smells" that lead Fathom by the nose to the target element. For example, if you are trying to recognize the images of products for sale on shopping sites, the target image might have smells like...

* Large size
* Position near the top of the page
* Position near the left of the page
* IDs or class names that contain the strings "hero" or "product"

Don't worry about expressing boolean combinations of smells except as a last resort. It's generally sufficient to let Fathom optimize a linear combination of them.

Since the primitives exposed by Fathom are thus far geared to the measurement of DOM properties (rather than, say, natural language processing), the best bang for your buck is rules that consider...

* CSS classes and IDs. Simply test for inclusion of signal-bearing strings. It is generally unnecessary to resort to tokenizing.
* Rendered size or position of elements
* Alignment or proximity of elements to each other
* Font sizes
* Colors and borders
* Visibility
* Any of the above in ancestor elements of the target

A useful technique is to look at some of the pages in your corpus and blur your eyes slightly. This shows you the page as Fathom sees it: you can't read the text, but you can likely still recognize the target elements. Write rules that express the smells you are using to sniff them out.

.. note::

   Computed CSS properties are worth a special mention: `getComputedStyle() <https://developer.mozilla.org/en-US/docs/Web/API/Window/getComputedStyle>`_ is the most robust way to retrieve style information about an element, since most properties are inherited through the complex interplay of stylesheets. Don't try to look at ``style`` attributes directly or otherwise painstakingly reason out styles.

Workflow
========

Your authoring process can vary, but this is a good place to start.

1. Set up `FathomFox <https://addons.mozilla.org/en-US/firefox/addon/fathomfox/>`_ as per its Quick Start.
2. Write some rules. Set the initial coefficients all to 4. (1 also works fine, though I suspect that setting them a bit higher lets the trainer more quickly find solutions that require deemphasizing one or two bad rules.)
3. Do a training run in FathomFox. Start with 10-20 pages.
4. If accuracy is insufficient, examine the failing pages. Remediate by changing or adding rules. If there are patterns Fathom is missing, add rules that give score bonuses for them. If there are certain kinds of elements Fathom is choosing spuriously, add rules that punish them in terms of score.
5. Go to 3.
6. Once *testing accuracy* is sufficient, copy the coefficients into your ruleset, and run the trainer on a fresh set of samples, just until the first set of accuracy numbers appears. This is your *testing accuracy* and should reflect real-world performance, assuming your sample size is large and representative enough. The computed 95% confidence intervals should help you decide the former.
7. If testing accuracy is too low, imbibe the testing pages into your training corpus, and go back to step 3. As typical in supervised learning systems, testing samples should be considered "burned" once they are measured against a single time, as otherwise you are effectively training against them. Samples are precious.
8. If testing accuracy is sufficient, you're done! Copy the ruleset and coefficients out of fathom-trainees into your finished product, and ship it.

Fuzzy Logic
===========

A few rulesets have experimented with constraining the returned subscores from individual scoring callbacks to the range (0, 1), a la fuzzy logic. Early results have been promising. The advantages are...

1. Capping them keeps subscores (which are multiplied together) from ballooning without limit. This allows the application of static thresholds for confidence floors and for performance-motivated early pruning. (Though note that you would need to take the nth root of an optimized score before treating it as a raw confidence, n being the sum of the coefficients for scores on that type.)
2. Using (0, 1) provides an intuitive interpretation of each subscore as a probability. This often makes a nice sanity check. `Trapezoid functions <https://github.com/mozilla/fathom-trainees/blob/6a0ca6b59ff70fcf05eb13906829b62856133a10/src/trainees.js#L180>`_ are a great tool for keeping values in range.

When returning fuzzy-logic subscores from a scoring callback, raise the (0, 1) value to the coefficient's power rather than multiplying it. See `this example <https://github.com/mozilla/fathom-trainees/blob/6a0ca6b59ff70fcf05eb13906829b62856133a10/src/trainees.js#L101>`_. This keeps the final returned value between 0 and 1. The ``ZEROISH`` and ``ONEISH`` `constants from that example <https://github.com/mozilla/fathom-trainees/blob/6a0ca6b59ff70fcf05eb13906829b62856133a10/src/trainees.js#L52>`_ are also good choices with wide applicability.

.. note::

   If you do use fuzzy-logic subscores, note that the range is exclusive: returning a hard 0 or 1 is bad news. Since subscores get multiplied together, a 0 will obliterate a score with no chance at redemption. Conversely, a 1 cannot be softened by the trainer by raising it to the power of a coefficient.

Tips
====

* Lots of simple rules are better than fewer, more complex ones. Not only are they easier to write, but the further you can break up your guesses into separately optimizable pieces, the more good the trainer can do.
* Your rules don't all have to be good. If you have an idea for a smell, code it up. If it was a bad idea, the trainer will give it a weak coefficient, and you can prune it away.
* :func:`when()` is good for early pruning: hard, yes/no decisions on what should be considered. Scores are for gradations.
* Many good rule ideas come out of labeling samples. If you are not labeling samples yourself, at least study them in depth so you can notice patterns.
* Rubrics are vital for labeling. If samples are labeled inconsistently, they will push the trainer in conflicting directions, and your accuracy will be poor. Also, keep your rubrics up to date. Whenever you encounter a case where you have to make a new decision—something the rubric doesn't already clearly decide—edit the rubric to codify that decision so you are consistent with it in the future.
