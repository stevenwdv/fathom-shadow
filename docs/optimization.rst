============
Optimization
============

Selecting the optimal :func:`score` coefficients in a complex ruleset is tricky, but it can have a huge effect on accuracy. Manual tweaking, supported by a laboriously constructed test harness, becomes untenable with more than a few coefficients, so we recommend letting the machine figure them out.

The Annealer
============

To prepare your ruleset for automatic optimization, replace its scoring and other scaling constants with JS variables, and wrap it in a function which takes a series of values and plops them into those variables:

   .. code-block:: js
      :emphasize-lines: 13,21,23

      /**
       * @return A ruleset for extracting the paragraph with the most textual
       * content.
       */
      function tunedRuleset(coeffLength = 3,
                            coeffParagraphTag = 2,
                            coeffLinkDensity = 5) {
          // If you use the best coefficients you've found so far as default
          // arg values, it makes tunedRuleset() a convenient production API
          // while allowing for future optimization runs.

          function scoreByLength(fnode) {
              const length = inlineTextLength(fnode.element) * coeffLength;
              return {score: length};
          }

          return ruleset(
              rule(dom('p,div,li,code,blockquote,pre,h1,h2,h3,h4,h5,h6'),
                   props(scoreByLength).type('paragraphish')),
              rule(type('paragraphish'),
                   score(fnode => (1 - linkDensity(fnode)) * coeffLinkDensity)),
              rule(dom('p'),
                   score(coeffParagraphTag).type('paragraphish')),
              rule(type('paragraphish').max(),
                   out('longestParagraph'))
          );
      }

Fathom provides a numerical optimizer based on `simulated annealing <https://en.wikipedia.org/wiki/Simulated_Annealing>`_. This algorithm is a particularly good fit for the `staircase functions <https://en.wikipedia.org/wiki/Step_function>`_ that commonly come up when measuring the efficacy of Fathom output [1]_. Continuous methods like `Powell's <https://en.wikipedia.org/wiki/Powell%27s_method>`_ tend to sit in the middle of a stair, look to the right, look to the left, see no improvement, and declare premature victory, while annealing has enough randomness to shake itself out of such local minima.

Fathom's optimizer is exposed as an abstract class in ``fathom-web/optimizers``:

.. autoclass:: Annealer
   :members:

The last 3 methods are yours to fill in. Don't try to be clever about them; it's better to come up with something that runs quickly, because the annealer runs many thousand iterations by default. These simple parametrizations are not unreasonable for the toy ruleset above:

   .. code-block:: js

      const {Annealer} = require('../optimizers');

      class LongestParagraphTuner extends Annealer {
          initialSolution() {
              return [1, 1, 1];
          }

          /** Nudge a random coefficient in a random direction by 0.5. */
          randomTransition(coeffs) {
              const ret = coeffs.slice();  // Make a copy.
              ret[Math.floor(Math.random() * coeffs.length)] += Math.floor(Math.random() * 2) ? -.5 : .5;
              return ret;
          }

          /**
           * Loop through a list of documents whose longest paragraphs (or whatever
           * you're looking for) we already know, run the ruleset over them, and bump
           * up the cost each time it comes up with something different.
           */
          solutionCost(coeffs) {
              let cost = 0;
              for (let [doc, knownBestParagraph] of aListOfKnownGoodSolutions) {
                  if (tunedRuleset(...coeffs)
                          .against(doc)
                          .get('longestParagraph')
                          .textContent !== knownBestParagraph) {
                      cost += 1;
                  }
              }
              return cost;
          }
      }

Then all you have to do is run the annealer, and go have a sandwich:

   .. code-block:: js

      const annealer = new LongestParagraphTuner();
      const coeffs = annealer.anneal();
      console.log('Tuned coefficients:', coeffs);

For a more complex, real-world example, see `readability.js in the examples folder <https://github.com/mozilla/fathom/blob/master/examples/readability.js>`_.

The Corpus Framework
====================

Of course, this leaves open the question of how to loop over a collected corpus, the ``aListOfKnownGoodSolutions`` above. Fortunately, Fathom also includes a hierarchy of inversion-of-control classes that help frame your answer to this: :class:`Run`, :class:`Corpus`, and :class:`Sample`.

We assume that your corpus is a folder of folders on disk, one inner folder for each member, or *sample*, of the corpus. The folder's name is considered the name of the sample. ::

    theCorpus
        sampleOne
            source.html
            ...
        sampleTwo
            source.html
            ...
        sampleThree
            source.html
            ...
        ...

Each sample folder contains these files:

``source.html``
  The HTML of the captured page, UTF-8 encoded. Ideally, this should "hold still", in that it shouldn't have any JS that will run and mutate the page when you're trying to examine it while designing your rules. JS will not, of course, be executed as the optimization harness itself runs over your corpus.

``whateverOtherFilesYouLike.foo``
  You can add additional inputs if you like, like known-correct answers or captured metadata that is not expressed in ``source.html`` alone. You pull these into properties of your :class:`Sample` by overriding its constructor.

The job of your annealer's ``solutionCost`` method is then to do a *run* over all the samples in your corpus, which can be represented like this:

   .. code-block:: js

      // Load the corpus from disk.
      constructor() {
          super();
          this.corpus = new LongestParagraphCorpus();
      }

      // Do a run over it, and see how the current coefficients determined by the
      // annealer scored.
      solutionCost(coeffs) {
          return new LongestParagraphRun(this.corpus, coeffs).score();
      }

It's up to you to implement the subclasses of :class:`Corpus` and :class:`Run`, as described below.

Corpus Framework Reference
--------------------------

.. autoclass:: Run
   :members: *, score, humanScore

.. autoclass:: Corpus
   :members:

.. autoclass:: Sample
   :members:


.. [1] This assumes a cost function which has sudden jumps, like when measuring the hard-edged inclusion or exclusion of nodes in the final output. If you can contrive a smoother one which, for instance, examines scores on nodes before they pass through hard-edged thresholds like :func:`max()`, you may be able to take advantage of a continuous optimization method to get better or quicker results.
