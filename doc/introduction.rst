.. SPDX-FileCopyrightText:  PyPSA-Earth and PyPSA-Eur Authors
..
.. SPDX-License-Identifier: CC-BY-4.0

.. _introduction:

##########################################
Introduction
##########################################

A short video explaining the logic of PyPSA-Eur which is similar to PyPSA-Earth:

.. raw:: html

    <iframe width="832" height="468" src="https://www.youtube.com/embed/ty47YU1_eeQ" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

For more details on PyPSA-Earth read the below milestone papers.

**For the power-only model**, please cite:
Parzen et al., "PyPSA-Earth. A new global open energy system optimization model demonstrated in Africa", Applied Energy, 2023.

**For the sector-coupled model**, please cite:
Abdel-Khalek et al., "PyPSA-Earth sector-coupled: A global open-source multi-energy system model showcased for hydrogen applications in countries of the Global South", Applied Energy, 2025.

For citations, please use the following BibTeX: ::

  @article{PyPSAEarth2023,
  author = {Maximilian Parzen and Hazem Abdel-Khalek and Ekaterina Fedotova and Matin Mahmood and Martha Maria Frysztacki and Johannes Hampp and Lukas Franken and Leon Schumm and Fabian Neumann and Davide Poli and Aristides Kiprakis and Davide Fioriti},
  title = {PyPSA-Earth. A new global open energy system optimization model demonstrated in Africa},
  journal = {Applied Energy},
  volume = {341},
  pages = {121096},
  year = {2023},
  issn = {0306-2619},
  doi = {https://doi.org/10.1016/j.apenergy.2023.121096},
  url = {https://www.sciencedirect.com/science/article/pii/S0306261923004609},
  }

  @article{PyPSAEarthSector2025,
  author = {Hazem Abdel-Khalek and Leon Schumm and Eddy Jalbout and Maximilian Parzen and Caspar Schauß and Davide Fioriti},
  title = {PyPSA-Earth sector-coupled: A global open-source multi-energy system model showcased for hydrogen applications in countries of the Global South},
  journal = {Applied Energy},
  volume = {383},
  pages = {125316},
  year = {2025},
  issn = {0306-2619},
  doi = {https://doi.org/10.1016/j.apenergy.2025.125316},
  url = {https://www.sciencedirect.com/science/article/pii/S0306261925000467},
  }


Workflow
========

The generation of the model is controlled by the workflow management system `Snakemake <https://snakemake.bitbucket.io/>`_. In a nutshell,
the ``Snakefile`` declares for each python script in the ``scripts`` directory a rule which describes which files the scripts consume and
produce (their corresponding input and output files). The ``snakemake`` tool then runs the scripts in the correct order according to the
rules' input/output dependencies. Moreover, it is able to track, what parts of the workflow have to be regenerated, when a data file or a
script is modified/updated. For example, by executing the following snakemake routine

.. code:: bash

    .../pypsa-earth % snakemake -j 1 networks/elec_s_128.nc

the following workflow is automatically executed.

.. image:: img/workflow_introduction.png
    :align: center

The **blocks** represent the individual rules which are required to create the file ``networks/elec_s_128.nc``.
Each rule requires scripts (e.g. Python) to convert inputs to outputs.
The **arrows** indicate the outputs from preceding rules which a particular rule takes as input data.

.. note::
    For reproducibility purposes, the image can be obtained through
    ``snakemake --dag networks/elec_s_128.nc | dot -Tpng -o workflow.png``
    using `Graphviz <https://graphviz.org/>`_


Folder structure
================

The content in this package is organized in folders as described below; for more details, please see the documentation.

- ``data``: Includes input data that is not produced by any ``snakemake`` rule.
- ``scripts``: Includes all the Python scripts executed by the ``snakemake`` rules.
- ``resources``: Stores intermediate results of the workflow which can be picked up again by subsequent rules.
- ``networks``: Stores intermediate, unsolved stages of the PyPSA network that describes the energy system model.
- ``results``: Stores the solved PyPSA network data, summary files and plots.
- ``benchmarks``: Stores ``snakemake`` benchmarks.
- ``logs``: Stores log files about solving, including the solver output, console output and the output of a memory logger.
- ``envs``: Stores the conda environment files to successfully run the workflow.


License
=======

PyPSA-Earth work is released under multiple licenses:

* All original source code is licensed as free software under `AGPL-3.0 License <https://github.com/pypsa-meets-earth/pypsa-earth/blob/main/LICENSES>`_.
* The documentation is licensed under `CC-BY-4.0 <https://creativecommons.org/licenses/by/4.0/>`_.
* Configuration files are mostly licensed under `CC0-1.0 <https://creativecommons.org/publicdomain/zero/1.0/>`_.
* Data files are licensed under different licenses as noted below.

Individual files contain license information in the header or in the `dep5 <.reuse/dep5>`_.
Additional licenses and urls of the data used in PyPSA-Earth:

.. csv-table::
   :header-rows: 1
   :file: configtables/licenses.csv


* *BY: Attribute Source*
* *NC: Non-Commercial Use Only*
* *SA: Share Alike*
