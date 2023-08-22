|tangelo_logo|

.. |tangelo_logo| image:: ./examples/img/tangelo_logo_gradient.png
   :width: 600
   :alt: tangelo_logo

|maintainer| |licence|

Launch this repository on Binder: |binder|

.. |maintainer| image:: https://img.shields.io/badge/Maintainer-GoodChemistry-blue
   :target: https://goodchemistry.com
.. |licence| image:: https://img.shields.io/badge/License-Apache_2.0-green
   :target: https://github.com/goodchemistryco/Tangelo/blob/main/LICENSE
.. |systems| image:: https://img.shields.io/badge/OS-Linux%20MacOS%20Windows-7373e3
.. |binder| image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/goodchemistryco/Tangelo-Examples/main

--------------------------------

.. |tag_intro| image:: https://img.shields.io/badge/-Introduction-green
.. |tag_exp| image:: https://img.shields.io/badge/-Experiment-7373e3
.. |tag_pd| image:: https://img.shields.io/badge/-Problem%20Decomp-red
.. |tag_vqe| image:: https://img.shields.io/badge/-VQE-yellow
.. |tag_chem| image:: https://img.shields.io/badge/-Chemistry-008080
.. |tag_qcloud| image:: https://img.shields.io/badge/-QEMIST%20Cloud-blue
.. |tag_qsim| image:: https://img.shields.io/badge/-Backends-AFEEEE
.. |tag_qalg| image:: https://img.shields.io/badge/-Quantum%20Algorithms-lavender
.. |tag_ft| image:: https://img.shields.io/badge/-Fault%20Tolerant-brown

.. |space| unicode:: U+0020 .. space
.. |nbspc| unicode:: U+00A0 .. non-breaking space
.. |tangerine| unicode:: U+1F34A .. tangerine emoji

Welcome traveler!

You have found the Github repository featuring the tutorials / examples notebooks and scripts created by the `Tangelo <https://github.com/goodchemistryco/Tangelo>`_ community. Most tutorials are not just about "code", but were designed to provide you with knowledge, references and insights about applying quantum computing to the simulation of electronic systems. Feel free to use any of these resources for educational purposes, or as a basis for your own projects. Any user can contribute to this repository and showcase their cool work, including you!

You can either explore this content directly through Github, or through GitHub-pages (automated web rendering). 
In order to help you find content relevant to your interests, this page provides a table that associates each resource with a few tags describing the main topics they relate to. If you are new to Tangelo, we suggest you start with those tagged with |tag_intro|. Please enjoy your stay. |tangerine|

|nbspc|

* |tag_intro| : great resource to get started
* |tag_chem| : great resource to learn more about chemistry
* |tag_qsim| : related to the simulation of quantum circuits
* |tag_exp| : related to experiments on quantum devices
* |tag_pd| : features problem decomposition (fragmentation) techniques
* |tag_vqe| : features the Variational Quantum Eigensolver
* |tag_ft| : features fault-tolerant approaches
* |tag_qalg| : discusses quantum algorithms more broadly
* |tag_qcloud| : related to QEMIST Cloud

|nbspc|

Contents
========

+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| Tutorial                                                                                                                | Main tag                     | Secondary tags                                                            |
+=========================================================================================================================+==============================+===========================================================================+
| `1. The basics <examples/workflow_basics/1.the_basics.ipynb>`_                                                          | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `2. QPU Connection <examples/workflow_basics/2.qpu_connection.ipynb>`_                                                  | |tag_qsim|                   | |tag_exp|                                                                 |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `3. Noisy Simulation <examples/workflow_basics/3.noisy_simulation.ipynb>`_                                              | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Symbolic Simulation <examples/workflow_basics/symbolic_simulator.ipynb>`_                                              | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Quantum Chemistry Basics <examples/chemistry/qchem_modelling_basics.ipynb>`_                                           | |tag_chem|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Excited State methods <examples/chemistry/excited_states.ipynb>`_                                                      | |tag_qalg|                   | |tag_chem| |tag_vqe|                                                      |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `VQE <examples/variational_methods/vqe.ipynb>`_                                                                         | |tag_vqe|                    | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `VQE with custom ansatz and Hamiltonian <examples/variational_methods/vqe_custom_ansatz_hamiltonian.ipynb>`_            | |tag_vqe|                    |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Adapt VQE Solver <examples/variational_methods/adapt.ipynb>`_                                                          | |tag_vqe|                    |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Iterative Qubit Coupled Cluster with Clifford Circuits <examples/variational_methods/iqcc_using_clifford.ipynb>`_      | |tag_vqe|                    | |tag_qsim|                                                                |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Classical Shadows <examples/measurement_reduction/classical_shadows.ipynb>`_                                           | |tag_qalg|                   |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Density Matrix Embedding Theory <examples/problem_decomposition/dmet.ipynb>`_                                          | |tag_pd|                     | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `DMET Unrestricted Hartree-Fock <examples/problem_decomposition/dmet_uhf.ipynb>`_                                       | |tag_pd|                     |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `MIFNO <examples/problem_decomposition/mifno.ipynb>`_                                                                   | |tag_pd|                     | |tag_intro| |tag_qcloud|                                                  |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `ONIOM <examples/problem_decomposition/oniom.ipynb>`_                                                                   | |tag_pd|                     | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `End-to-End hardware experiment <examples/measurement_reduction/hardware_experiments/overview_endtoend.ipynb>`_         | |tag_exp|                    | |tag_intro| |tag_pd|                                                      |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Hardware Experiment using QEMIST Cloud <examples/hardware_experiments/qemist_cloud_hardware_experiment.ipynb>`_        | |tag_exp|                    | |tag_qcloud|                                                              |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Berylium IBM Quantum experiment <examples/hardware_experiments/berylium_ibm_quantum.ipynb>`_                           | |tag_exp|                    | |tag_pd| |tag_qcloud|                                                     |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Umbrella inversion Braket <examples/hardware_experiments/umbrella_inversion.ipynb>`_                                   | |tag_exp|                    | |tag_pd| |tag_qcloud| |tag_ft|                                            |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `State Preparation with Quantum Signal Processing <examples/fault_tolerant/qsp_state_prep.ipynb>`_                      | |tag_ft|                     |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+

