===========
Development
===========

Tests and Examples
==================

`Our tests <https://github.com/mozilla/fathom/tree/master/fathom/test>`_ are replete with examples exercising every corner of Fathom.

To run the tests, run... ::

    make lint test

This will also run the linter and analyze test coverage. To render the coverage report human-legibly, run ``make coverage``. You can then find the coverage report in the ``coverage`` directory.

You can also run the linter or tests for just one subproject at a time. For example, to test the CLI tools... ::

    cd cli
    make lint test

If you want to drop into the debugger in the middle of a JS test, add a ``debugger;`` statement at your desired breakpoint, then run ``make debugtest`` in the ``fathom`` subproject::

    cd fathom
    make debugtest

Docs
====

To build the docs... ::

    make docs

Gotchas
=======

If you are developing the CLI tools and your changes to their embedded copy of the Fathom JS framework don't seem to be taking effect, commit first. The make target that builds ``fathom.zip`` uses ``git archive`` to pull from ``HEAD``.
