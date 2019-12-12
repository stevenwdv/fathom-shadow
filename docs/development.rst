===========
Development
===========

Tests and Examples
==================

`Our tests <https://github.com/mozilla/fathom/tree/master/test>`_, are replete with examples exercising every corner of Fathom.

To run the tests, run... ::

    make lint test

This will also run the linter and analyze test coverage. To render the coverage report human-legibly, run ``make coverage``. You can then find the coverage report in the ``coverage`` directory.

You can also run the linter or tests for just the code of one language at a time::

    make js_lint
    make js_test

    make py_lint
    make py_test

If you want to drop into the debugger in the middle of a JS test, add a ``debugger;`` statement at your desired breakpoint, then run... ::

    make debugtest

Docs
====

To build the docs... ::

    make doc
