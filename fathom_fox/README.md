# FathomFox

A suite of tools for developing [Fathom](https://mozilla.github.io/fathom/) rulesets within Firefox:

* [Corpus collection and labeling tools](https://mozilla.github.io/fathom/samples.html) (which are likely all you will need)
* An Evaluator which can help you [drop into the JS debugger](https://mozilla.github.io/fathom/training.html#setting-breakpoints) inside your ruleset
* A Vectorizer, which you can ignore. (It persists, for now, as an optional manual alternative to simply letting `fathom-train` and other tools take care of vectorization automatically.)

For most use cases, it's better to run FathomFox from the commandline rather than installing it through the web. See [Fathom's installation page](https://mozilla.github.io/fathom/installing.html) for instructions.

## Full Documentation

See [the Fathom docs](https://mozilla.github.io/fathom/versions.html).

## Running FathomFox from a Source Checkout

This is necessary only if you are developing FathomFox itself.

1. Clone the [Fathom repository](https://github.com/mozilla/fathom/).
2. From within the checkout, inside the `fathom_fox` folder, install dependencies: `yarn run build`.
3. Run a clean copy of Firefox with FathomFox installed: `yarn run browser`.
4. Run `yarn run watch` in a separate terminal. This will keep your running copy of FathomFox up to date as you edit your ruleset.

## Thanks

Thanks to Treora for his excellent freeze-dry library!
