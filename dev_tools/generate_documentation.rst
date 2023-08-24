How to generate and update the GitHub-pages documentation
=========================================================

This document is here to assist this project maintainers in updating the `documentation <https://goodchemistryco.github.io/Tangelo-Examples/>`_ of this repository.
Notebooks are rendered using `Quarto <https://quarto.org/>`_, and the source files are deployed via github-pages.
We describe below how to re-generate this documentation after changes in the repository, such as the modification or addition of new notebooks.

1. Installing Quarto
--------------------

The up-to-date information about the Quarto installation can be found in the `installation help <https://docs.posit.co/resources/install-quarto/>`_ and `download <https://quarto.org/docs/download/>`_ webpages.
On Ubuntu (or other Debian-based distributions), the relevant commands can be currently summarized as

.. code-block::

   # Download the lastest Quarto release
   curl -LO https://quarto.org/download/latest/quarto-linux-amd64.deb

   # The recommended way is to installed it with the Gdebi app
   sudo apt-get install gdebi-core
   sudo gdebi quarto-linux-amd64.deb


2. Updating the documentation
-----------------------------

2a. Updating the relevant files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two files which may require modifications, on top of the other generated files (html, json, ...)

- `README.rst`: A README update for users visiting the GitHub page.
- `index.qmd`: The main page of the rendered documentation, listing and tying together all the other rendered html files.

2b. Locally regenerating the html files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is simply done by calling the following command in the root directory of the `Tangelo-Examples` folder:

.. code-block::

   quarto render

Rendered files have been generated, and they can be navigated in the `_site` folder.
This step regenerates the html documentation locally to ensure notebooks render as they should, and that the navigation works as expected.

2c. Deployment on github-pages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Deployment is automatically done in the `gh-pages` branch by GitHub actions, and this happens everytime changes are pushed to the `main` branch.
Therefore, any merged pull request will trigger the GitHub actions to deploy a new website for the documentation.
For more information on how it is set up, see the `Quarto - GitHub Pages <https://quarto.org/docs/publishing/github-pages.html>`_ webpage.
