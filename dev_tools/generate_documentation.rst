Generate the rendered documentation with Quarto
===============================================

This document is here to assist this project's maintainers in updating the `documentation <https://goodchemistryco.github.io/Tangelo-Examples/>`_ of this repository.
Notebooks are rendered using `Quarto <https://quarto.org/>`_, and the source files are deployed via github-pages.
The required step to render the documentation after significant changes, like the addition of a new notebook, are described below.

1. Installing Quarto
--------------------

The up-to-date information about the Quarto installation can be found in the `installation help <https://docs.posit.co/resources/install-quarto/>`_ and `download <https://quarto.org/docs/download/>`_ webpages.
On Ubuntu (or other Debian-based distributions), the relevant commands can be summarized as

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

There are two files which may require modifications

- `README.rst`
- `index.qmd`

2b. Regenerate the html files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is simply done by calling the following command in the root directory of the `Tangelo-Examples` folder.

.. code-block::

   quarto render

2c. Deployment on github-pages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

At the time of writing this tutorial, the only way of testing the new rendered documentation is to manually deploy from a branch.
This can be done by naviguating to the `Github repository <https://github.com/goodchemistryco/Tangelo-Examples>`_, and changing the branch in the `Settings / Pages / Build and deployment` option.
The screenshot below is an example of a deployment using the `dmet_uhf` branch.

|manual_deployment|

.. |manual_deployment| image:: ./manual_deployment.png
   :width: 600
   :alt: manual_deployment
