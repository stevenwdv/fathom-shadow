===========
Development
===========

Tests and Examples
==================

`Our tests <https://github.com/mozilla/fathom/tree/master/test>`_, especially `demos.js <https://github.com/mozilla/fathom/blob/master/test/demos.js>`_, are replete with examples exercising every corner of Fathom.

To run the tests, run... ::

    make lint test

This will also run the linter and analyze test coverage. You can find the coverage report in the ``coverage`` directory and the HTML version under ``coverage/lcov-report/fathom/index.html``.

You can also run the linter or tests for just the code of one language at a time::

    make js_lint
    make js_test

    make py_lint
    make py_test

If you want to drop into the debugger in the middle of a JS test, add a ``debugger;`` statement at your desired breakpoint, then run... ::

    make debugtest

Docs
====

To build the docs, first install jsdoc and Sphinx::

    npm install jsdoc
    pip install 'sphinx-js>=1.3,<2.0' sphinx_rtd_theme

You may also have to mess with your ``$PATH`` so Sphinx can find jsdoc. Then, go into the docs dir, and build them::

    cd docs
    make html
