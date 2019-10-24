# `fathom-do-everything`

Usage: `fathom-do-everything trainees.js /path/to/training_samples
/path/to/validation_samples -o /path/to/save/vectors/to`

The arguments for the samples can change as we continue to solidify how the
samples are stored.

The output directory for the vectors would default to the current working
directory.

### What `fathom-do-everything` will do:
* Build the FathomFox and Fathom Trainees addons
* Serve the training samples via an HTTP server
    * Possibly `fathom-serve`
* Use `fathom-list` to get the list of filenames
* Launch a headless Firefox instance
* Load the FathomFox and Fathom Trainees addons
* Go to the vectorizer page
* Fill in the necessary information into the Vectorizer page
* Run the Vectorizer
    * Display some sort of progress information back to the terminal
* Wait until the Vectorizer page shows all of the files as having been
vectorized and there is a vector file present
* Switch to serving the validation samples via an HTTP server
* Use `fathom-list` to get the list of filenames
* Fill in the necessary information into the Vectorizer page
* Run the Vectorizer
* Wait until the Vectorizer page shows all of the files as having been
vectorized and there is a vector file present
* Close the headless Firefox instance

### Additional considerations:
* Trainer could be a part of this
* The program can check for changes in the ruleset and the contents of the
samples directories and skip vectorization
if possible
    * Save a hash of `trainees.js` and the output of `fathom-list`?
* The program will have local copies of the FathomFox and Fathom Trainees
repositories. Only the built version of the FathomFox addon is currently needed
but when Fathom Trainees goes away, the FathomFox source will be needed to
build the addon with the trainees file (I'm assuming that's how it will work).
