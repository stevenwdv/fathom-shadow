========
Training
========

Training is the process by which Fathom combines your handwritten rules with your labeled example pages to create the most accurate possible model. Training emits a set of numerical parameters:

* One *coefficient* per rule, which indicates the rule's relative weight
* One *bias* per type, which centers element's scores so they can be construed as 0..1 confidences

Collecting Samples
==================

Use `FathomFox <https://addons.mozilla.org/en-US/firefox/addon/fathomfox/>`_ to collect samples. It has both a bulk collector and a page-at-a-time method integrated into Firefox's developer tools. Typically, you'll use the latter. See the documentation on the aforementioned page for details.

The pages serialized by FathomFox will be large, on the order of 100-200MB each. So far, the best organizational approach we've found is to check them into git, along with your application and a ``rulesets.js`` file you create to hold your rulesets. The :command:`fathom-extract` tool makes this feasible; see `Storing Large Corpora in Version Control`_.

So far, a training set on the order of a few hundred samples has been sufficient to push validation accuracy above 99%. You'll want additional samples for a validation set (to let the trainer know when it's begun to overfit) and a test set (to come up with final accuracy numbers). We recommend a 60/20/20 split among training/validation/testing set. This gives you large enough validation and testing sets, at typical corpus sizes, while shunting as many samples as possible to the training set so you can mine them for rule ideas.

It's important to keep your sets mutually representative. If you have a bunch of samples sorted by some metric, like site popularity or when they were collected, don't use samples 1-100 for training and then 101-200 for validation. Instead, collect a set of samples, and then use :command:`fathom-pick` to proportionally assign them to sets: 60% to training and 20% to each of validation and testing. You can repeat this as you later come to need more samples.

Designing Rules
===============

Each rule should generally express one machine-learning feature—or "smell", to coin a metaphor. The score it applies—the return value of the callback passed to :func:`score`—should be a number from 0 to 1, inclusive, representing the probability that that smell is present. These smells are later balanced by the trainer.

.. note::

   For many smells, it's natural to return hard 0s or 1s (or trues and falses, if that's more convenient). If you have fuzzier values to return—as from a rule that expresses something subjectively defined like "image is big"—:func:`linearScale` and :func:`sigmoid` will help you clamp down extreme values. Make the choice based on whether two adjacent extreme values should still have distinguishable outputs. If they should, go with sigmoid().

Sources of Signal
-----------------

What sorts of rules should you write? In short, ones that express simple, atomic smells that tend to be found in—or lacked by—target elements. For example, if you are trying to recognize the images of products for sale on shopping sites, the target image might have smells like...

* Large size
* Position near the top of the page
* Position near the left of the page
* IDs or class names that contain the strings "hero" or "product"

Don't worry about expressing boolean combinations of smells except as a last resort. It's generally sufficient to let Fathom optimize a linear combination of them. Also, Fathom will determine on its own whether to give a positive or negative weight to a smell; you don't need to tell it.

Since the primitives exposed by Fathom are thus far geared to the measurement of DOM properties (rather than, say, natural language processing), the best bang for your buck is generally rules that consider...

* CSS classes and IDs. Begin by simply testing for inclusion of signal-bearing strings. It is probably unnecessary to apply tokenization.
* Rendered size or position of elements
* Alignment or proximity of elements to each other. So far, the state of the art is to program a bit of "look around" into the scoring callback. It is also possible to get ahold of the :class:`BoundRuleset` object and try to pair up the examined node with another of a certain type, but so far it's a manual process.
* Font sizes
* Colors and borders
* Visibility
* Any of the above in :func:`ancestor<ancestors>` elements of the target

A useful technique is to look at some of the pages in your corpus and blur your eyes slightly. This shows you the page as Fathom sees it: you can't read the text, but you can likely still recognize the target elements. Write rules that express the smells you are using to do so.

Computed CSS properties are worth a special mention: `getComputedStyle() <https://developer.mozilla.org/en-US/docs/Web/API/Window/getComputedStyle>`_ is the most robust way to retrieve style information about an element, since most properties are inherited through the complex interplay of stylesheets. Don't try to look at ``style`` attributes directly or otherwise painstakingly reason out styles.

Rules of Thumb
--------------

* Lots of simple rules are better than fewer, more complex ones. Not only are they easier to write, but the further you can break up your guesses into separately optimizable pieces, the more good the trainer can do.
* Your rules don't all have to be good. If you have an idea for a smell, code it up. If it was a bad idea, the trainer will give it a coefficient near 0, and you can prune it away.
* :func:`when()` is good for early pruning: hard, yes/no decisions on what should be considered. Scores are for gradations. Pruning makes your vector files smaller and training faster.
* Many good rule ideas come out of labeling samples. If you are not labeling samples yourself, at least study them in depth so you can notice patterns.
* Rubrics are vital for labeling. If samples are labeled inconsistently, they will push the trainer in conflicting directions, and your accuracy will suffer. Also, keep your rubrics up to date. Whenever you encounter a case where you have to make a new decision—something the rubric doesn't already clearly decide—edit the rubric to codify that decision so you are consistent with it in the future. Check your rubrics into version control.
* Include some samples that are missing the thing you're trying to recognize so your ruleset learns to avoid false positives. We call these "negative" samples, and they should generally make up 20-50% of your corpus.

Suggested Directory Structure
=============================

We've mentioned a number of items to check into version control. Here is a directory structure that works well:

.. code-block:: none

    runs/             -- TensorBoard data emitted by the trainer
    samples/
        unused/
            3.html   -- A positive sample, which contains an example of what we're looking for
            10.html
            14.html
            n4.html  -- A negative sample: one that does NOT contain what we're looking for
            n7.html
            n11.html
            ...
        training/
            1.html
            n2.html
            5.html
            ...
        validation/
        testing/
        rubric.txt
    rulesets.js       -- Ruleset code
    vectors/          -- Feature vectors cached by fathom-train and fathom-test
        training_yourTraineeIdHere.json
        validation_yourTraineeIdHere.json
        testing_yourTraineeIdHere.json

A few notes:

* The negative samples' numerical IDs are in the same namespace as the positive ones, but we prefix them with an n. This is so that, when the trainer says it assumed a sample was negative because it had no labeled target elements, we can tell at a glance whether it was correct.
* Samples start in the ``unused`` folder. From there, they should be divided among the training, validation, and testing ones using :command:`fathom-pick`, which randomly moves a given number of files from one directory to another to keep the sets mutually representative.

Installing Fathom's Commandline Tools
=====================================

Fathom's commandline tools are Python 3 programs. If you don't already have Python 3.7 or better, download it from https://www.python.org/downloads/. Then, install the Fathom tools by running... ::

    pip3 install fathom-web

It's possible your Python package manager ("pip") is called simply "pip" rather than "pip3". Give that a try if the above fails.

Storing Large Corpora in Version Control
========================================

Fathom corpora often bump up against the limits imposed by git hosting services like GitHub. Thus, we recommend using `Git Large File Storage (LFS) <https://git-lfs.github.com/>`_ to store samples. This is facilitated by a tool called :command:`fathom-extract`, which breaks large subresources like images back out of the HTML. As a bonus, your HTML files will shrink drastically and become feasible to diff.

Using fathom-extract
--------------------

:command:`fathom-extract` pulls the inlined data URLs representing subresources (like images and CSS) out of your samples, converts them into images and CSS files, places them in a newly created sample-specific directory within a newly created resources directory, and replaces the data URLs with references to the new files. This let you use Git-LFS to store the new subresource files.

For example, if you have this directory of samples: ::

    samples/
        unused/
            3.html
            10.html
            14.html
            ...

Running... ::

    fathom-extract samples/unused

will change your directory to: ::

    samples/
        unused/
            originals/
            resources/
                3/
                    1.png
                    2.css
                    3.css
                    ...
                10/
                    1.css
                    2.jpg
                    3.jpg
                    ...
                14/
                    1.css
                    2.png
                    3.jpg
                    ...
                ...
            3.html
            10.html
            14.html
            ...

Once you are comfortable that your samples extracted correctly, you can delete the ``originals`` directory.

Configuring Git-LFS
-------------------

With your extracted samples directory, you can follow the `Git-LFS Getting Started steps <https://git-lfs.github.com/>`_ to track your new resources directory. In step 2, instead of running the ``git lfs track`` command, you may find it easier to directly edit the ``.gitattributes`` file. For our resources directory, you would add the line: ::

    samples/**/resources/** filter=lfs diff=lfs merge=lfs -text

The first ``/**`` ensures all sample directories (``unused``, ``training``, etc.) are tracked, and the second ``/**`` ensures the subdirectories are tracked.

Running the Trainer
===================

.. note::

   Fathom has had several trainers over its evolution. Both the Corpus Framework and the trainer built into old versions of FathomFox are obsoleted by :command:`fathom-train`, described herein.

Once your samples are collected and at least several rules are written, you're ready to do some initial training. Training is done for one type at a time. If you have types that depend on other types (an advanced case), train the other types first.

Run the trainer. A simple beginning, using just a training set, is... ::

    fathom-train samples/training --ruleset rulesets.js --trainee yourTraineeId

...yielding something like... ::

    {"coeffs": [
            ['nextAnchorIsJavaScript', 1.1627885103225708],
            ['nextButtonTypeSubmit', 4.613410949707031],
            ['nextInputTypeSubmit', 4.374269008636475],
            ['nextInputTypeImage', 6.867544174194336],
            ['nextLoginAttrs', 0.07278082519769669],
            ['nextButtonContentContainsLogIn', -0.6560719609260559],
            ],
         "bias": -3.9029786586761475}

    Training accuracy per tag:  0.97173    95% CI: (0.95808, 0.98539)
                          FPR:  0.01163    95% CI: (0.00150, 0.02176)
                          FNR:  0.08088    95% CI: (0.03506, 0.12671)
                    Precision:  0.96154    Recall: 0.91912
                     F1 Score:  0.93985

    Time per page (ms): 2 |▁▃█▅▂▁    | 34    Average per tag: 8.3

    Training per-tag results:
       AR_534.html  <input type="password" class="form-control pass" autocomplete="off" id="password        1.00000000
       CS_474.html  <input type="password" data-placeholder="register.password1" placeholder="Heslo"        1.00000000
                    <input type="password" data-placeholder="register.password2" placeholder="Heslo         1.00000000
       CZ_36n.html  No targets found.
       DA_177.html  <input data-validation-match="#UserModel_VerifyPassword" id="UserModel_ActionMod        0.99999964
       ...

Viewing the TensorBoard graphs with ``tensorboard --logdir runs/`` will quickly show you whether the loss function is oscillating. If you see oscilloscope-like wiggles rather than a smooth descent, the learning rate is too high: the trainer is taking steps that are too big and overshooting the optimum it's chasing. Decrease the learning rate by a factor of 10 until the graph becomes monotonically decreasing::

    fathom-train samples/training  --ruleset rulesets.js --trainee yourTraineeId --learning-rate 0.1 -c tryingToRemoveOscillations

Comments (with ``-c``) are your friend, as a heap of anonymous TensorBoard runs otherwise quickly becomes indistinguishable.

.. note::

   Fathom currently uses the `Adam <https://en.wikipedia.org/wiki/Stochastic_gradient_descent#Adam>`_ optimization algorithm, which is good at tuning its own learning rates. Even if the loss graph oscillates at the start, it will eventually flatten out, given enough iterations. However, it's best to tamp down oscillations from the beginning so you can use validation-guided early stopping. Adam seems to dial in the learning rate quickly enough, as long as you get it within a power of 10.

   Incidentally, it's not the end of the world if some scores go slightly outside [0, 1]. Limited tests have gotten away with values up to about 10 without measurable harm to training speed or accuracy. However, when feature values differ in magnitude by a factor of 1000, annoying oscillations dominate early iterations. Stick to [0, 1] for a trouble-free experience.

Once you've tamped down oscillations, use validation samples and early stopping to keep Fathom from overfitting::

    fathom-train samples/training --ruleset rulesets.js --trainee yourTraineeId --validation-set samples/validaton --stop-early -c tryingEarlyStopping

The trainer comes with a variety of adjustment knobs to ensure a good fit and a good tradeoff between false positives and false negatives. Here is its online help, to give you a sense of its full capabilities:

.. code-block:: none

    % fathom-train --help

    Usage: fathom-train [OPTIONS] TRAINING_SET_FOLDER

      Compute optimal numerical parameters for a Fathom ruleset.

      There are a lot of options, but the usual invocation is something like...

        fathom-train samples/training --validation-set samples/validation
        --stop-early --ruleset rulesets.js --trainee new

      TRAINING_SET_FOLDER is a directory of labeled training pages. It can also
      be, for backward compatibility, a JSON file of vectors from FathomFox's
      Vectorizer.

      To see graphs of the results, install TensorBoard, then run this:
      tensorboard --logdir runs/. These will tell you whether you need to adjust
      the --learning-rate.

      Some vocab used in the output messages:

        target -- A "right answer" DOM node, one that should be recognized

        candidate -- Any node (target or not) brought into the ruleset, by a
        dom() call, for consideration

        negative sample -- A sample with no intended target nodes, used to bait
        the recognizer into a false-positive choice

    Options:
      -a, --validation-set FOLDER     Either a folder of validation pages or a
                                      JSON file made manually by FathomFox's
                                      Vectorizer. Validation pages are used to
                                      avoid overfitting.

      -r, --ruleset FILE              The rulesets.js file containing your rules.
                                      The file must have no imports except from
                                      fathom-web, so pre-bundle if necessary.

      --trainee ID                    The trainee ID of the ruleset you want to
                                      train. Usually, this is the same as the type
                                      you are training for.

      --training-cache FILE           Where to cache training vectors to speed
                                      future training runs. Any existing file will
                                      be overwritten. [default:
                                      vectors/training_yourTraineeId.json next to
                                      your ruleset]

      --validation-cache FILE         Where to cache validation vectors to speed
                                      future training runs. Any existing file will
                                      be overwritten. [default:
                                      vectors/validation_yourTraineeId.json next
                                      to your ruleset]

      --show-browser                  Show browser window while vectorizing.
                                      (Browser runs in headless mode by default.)

      -s, --stop-early                Stop 1 iteration before validation loss
                                      begins to rise, to avoid overfitting. Before
                                      using this, check Tensorboard graphs to make
                                      sure validation loss is monotonically
                                      decreasing.

      -l, --learning-rate FLOAT       The learning rate to start from  [default:
                                      1.0]

      -i, --iterations INTEGER        The number of training iterations to run
                                      through  [default: 1000]

      -p, --pos-weight FLOAT          The weighting factor given to all positive
                                      samples by the loss function. See: https://p
                                      ytorch.org/docs/stable/nn.html#bcewithlogits
                                      loss

      -c, --comment TEXT              Additional comment to append to the
                                      Tensorboard run name, for display in the web
                                      UI

      -q, --quiet                     Hide per-tag diagnostics that may help with
                                      ruleset debugging.

      -t, --confidence-threshold FLOAT
                                      Threshold at which a sample is considered
                                      positive. Higher values decrease false
                                      positives and increase false negatives.
                                      [default: 0.5]

      -y, --layer INTEGER             Add a hidden layer of the given size. You
                                      can specify more than one, and they will be
                                      connected in the given order. EXPERIMENTAL.

      -x, --exclude TEXT              Exclude a rule while training. This helps
                                      with before-and-after tests to see if a rule
                                      is effective.

      --help                          Show this message and exit.

Workflow
========

A sane authoring process is a feedback loop something like this:

1. Collect samples. Observe patterns in the :term:`target` nodes as you do.
2. Write a few rules based on your observations.
3. Run the trainer. Start with 10-20 training pages and an equal number of validation ones.
4. If accuracy is insufficient, examine the failing training pages. The trainer will point these out on the commandline, but FathomFox's Evaluator will help you track down ones that are hard to distinguish from their tag excerpts. Remediate by changing or adding rules. If there are smells Fathom is missing—positive or negative—add rules that score based on them.
5. Go back to step 3.
6. Once *validation accuracy* is sufficient, use the :command:`fathom-test` tool on a fresh set of *testing* samples. This is your *testing accuracy* and should reflect real-world performance, assuming your sample size is large and representative enough. The computed 95% confidence intervals should help you decide the former.
7. If testing accuracy is too low, imbibe the testing pages into your training set, and go back to step 3. As typical in supervised learning systems, testing samples should be considered "burned" once they are measured against a single time, as otherwise you are effectively training against them. Samples are precious.
8. If testing accuracy is sufficient, you're done! Make sure the latest ruleset and coefficients are in your finished product, and ship it.
