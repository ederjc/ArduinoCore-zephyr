Contributing
*************

We welcome community contributions! If you have a suggestion that would make
this better, please fork the repo and create a pull request for your changes
as described below. You can also simply open a feature request issue.

1. `Fork <https://github.com/Infineon/ArduinoCore-zephyr/fork>`_ this repository.
2. Create your feature branch (``git checkout -b feature/amazing-feature``).
3. Commit your changes, following the commit title format below.
4. Push to the branch (``git push origin feature/amazing-feature``).
5. Open a `pull request <https://github.com/Infineon/ArduinoCore-zephyr/pulls>`_.

Before submitting a pull request, please check the
`code of conduct <https://github.com/Infineon/ArduinoCore-zephyr/blob/main/CODE_OF_CONDUCT.md>`_.

Commit and PR title format
============================

Commit titles and PR titles should follow the pattern ``<scope>: <description>``.

Examples of valid titles:

- ``edge: register PSOC Edge E84 board``
- ``edge: add PSOC Edge E84 variant``

Examples of invalid titles:

- ``Edge support``
- ``fix issue``

Additionally, the following sections might be helpful for developing and
testing your contributions:

- :doc:`env-setup`
- :doc:`run-tests`

Documentation
=============

This documentation is written with `Sphinx <https://www.sphinx-doc.org>`_ and
lives in the ``docs/`` folder.

Building locally
----------------

Install `Graphviz <https://graphviz.org/download/>`_ for the diagrams, then
build the HTML pages:

.. code-block:: bash

   python -m pip install -r docs/requirements.txt
   python -m sphinx -W --keep-going -b html docs docs/_build/html

Open ``docs/_build/html/index.html`` in a browser to review the result. Pull
requests that change the documentation are built the same way, so the check
fails on any new Sphinx warning. The built HTML is attached to the workflow
run as the ``docs-html`` artifact.

Published versions
------------------

The documentation is published on GitHub Pages. Every branch and every release
tag that contains ``docs/conf.py`` gets its own version of the documentation,
which is updated on every push:

.. list-table::
   :header-rows: 1

   * - URL path
     - Content
   * - ``/<version>/``
     - The branch or tag ``<version>``. The name is lowercased and characters
       such as ``/`` are replaced by ``-``, e.g. branch ``feature/new-board``
       is published to ``/feature-new-board/``.
   * - ``/latest/``
     - The default branch.
   * - ``/stable/``
     - The newest release, i.e. the highest version tag such as ``1.2.0`` or
       ``v1.2.0``. Pre-release tags such as ``1.2.0-rc1`` are published under
       their own name but never become ``stable``.
   * - ``/``
     - Redirects to ``stable``, or to ``latest`` before the first release.

The version switcher lists all published versions. Branches and releases
other than the latest stable release show a banner linking to stable.

Deleting a branch or tag also removes its documentation. Automatic builds
require the workflow to be present in the branch or tag. To publish an older
ref, run the *Documentation* workflow manually from the default branch and
enter the branch or tag name. Older documentation without the version
switcher remains navigable through the site home page.

Refs that produce the same slug, and the reserved names ``latest`` and
``stable``, cannot be published together; the workflow reports an error
instead of overwriting an existing version.

The published versions are collected in the ``gh-pages`` branch, which is
managed by the *Documentation* workflow and must not be edited by hand.
For another repository, set its GitHub Pages source to *GitHub Actions* and
backfill any existing refs through the manual workflow.
