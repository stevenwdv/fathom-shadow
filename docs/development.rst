===========
Development
===========

Source
======

It's on `GitHub <https://github.com/mozilla/fathom>`_.

Tests and Examples
==================

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

If you are developing the CLI tools and your changes to their embedded copy of the Fathom JS framework don't seem to be taking effect, commit first. The make target that builds ``fathom.zip`` uses ``git archive`` to pull from ``HEAD``. In this scenario, we tend to use a single local commit we amend with ``git commit --amend --no-edit`` when we want to test our changes.

Windows Considerations
======================

Fathom uses `Makefiles <https://www.gnu.org/software/make/manual/make.html>`_ to do its builds and run its tests. These Makefiles rely on Unix commands. Therefore, if you are developing on Windows, you need access to these Unix commands through something like `Cygwin <https://www.cygwin.com/>`_. You can build and test Fathom using `Windows Subsystem for Linux <https://docs.microsoft.com/en-us/windows/wsl/>`_, but just know that you are technically building and testing Fathom in Linux when you do.
