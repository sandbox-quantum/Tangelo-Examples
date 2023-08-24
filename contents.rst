.. |tag_intro| image:: https://img.shields.io/badge/-Introduction-green
.. |tag_exp| image:: https://img.shields.io/badge/-Experiment-7373e3
.. |tag_pd| image:: https://img.shields.io/badge/-Problem%20Decomp-red
.. |tag_vqa| image:: https://img.shields.io/badge/-VQA-yellow
.. |tag_chem| image:: https://img.shields.io/badge/-Chemistry-008080
.. |tag_qcloud| image:: https://img.shields.io/badge/-QEMIST%20Cloud-blue
.. |tag_qsim| image:: https://img.shields.io/badge/-Backends-AFEEEE
.. |tag_qalg| image:: https://img.shields.io/badge/-Quantum%20Algorithms-lavender
.. |tag_ft| image:: https://img.shields.io/badge/-Fault%20Tolerant-brown

.. |space| unicode:: U+0020 .. space
.. |nbspc| unicode:: U+00A0 .. non-breaking space
.. |tangerine| unicode:: U+1F34A .. tangerine emoji

In order to help you find content relevant to your interests, this page provides a table that associates each resource with a few tags describing the main topics they relate to. If you are new to Tangelo, we suggest you start with those tagged with |tag_intro|. Please enjoy your stay. |tangerine|

Tags
====

* |tag_intro| : great resource to get started
* |tag_chem| : great resource to learn more about chemistry
* |tag_qsim| : related to the simulation of quantum circuits
* |tag_exp| : related to experiments on quantum devices
* |tag_pd| : features problem decomposition (fragmentation) techniques
* |tag_vqa| : features Variational Quantum Algorithms
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
| `3. Noisy Simulation <examples/workflow_basics/3.noisy_simulation.ipynb>`_                                              | |tag_qsim|                   |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Symbolic Simulation <examples/workflow_basics/symbolic_simulator.ipynb>`_                                              | |tag_qsim|                   |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Quantum Chemistry Basics <examples/chemistry/qchem_modelling_basics.ipynb>`_                                           | |tag_chem|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Excited State methods <examples/chemistry/excited_states.ipynb>`_                                                      | |tag_qalg|                   | |tag_chem| |tag_vqa|                                                      |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `VQE <examples/variational_methods/vqe.ipynb>`_                                                                         | |tag_vqa|                    | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `VQE with custom ansatz and Hamiltonian <examples/variational_methods/vqe_custom_ansatz_hamiltonian.ipynb>`_            | |tag_vqa|                    |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Adapt VQE Solver <examples/variational_methods/adapt.ipynb>`_                                                          | |tag_vqa|                    |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Iterative Qubit Coupled Cluster with Clifford Circuits <examples/variational_methods/iqcc_using_clifford.ipynb>`_      | |tag_vqa|                    | |tag_qsim|                                                                |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Classical Shadows <examples/measurement_reduction/classical_shadows.ipynb>`_                                           | |tag_qalg|                   |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Density Matrix Embedding Theory <examples/problem_decomposition/dmet.ipynb>`_                                          | |tag_pd|                     | |                                                                         |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `DMET Unrestricted Hartree-Fock <examples/problem_decomposition/dmet_uhf.ipynb>`_                                       | |tag_pd|                     |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `MIFNO <examples/problem_decomposition/mifno.ipynb>`_                                                                   | |tag_pd|                     | |tag_qcloud|                                                              |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `ONIOM <examples/problem_decomposition/oniom.ipynb>`_                                                                   | |tag_pd|                     |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `End-to-End hardware experiment <examples/measurement_reduction/hardware_experiments/overview_endtoend.ipynb>`_         | |tag_exp|                    | |tag_pd|                                                                  |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Hardware Experiment using QEMIST Cloud <examples/hardware_experiments/qemist_cloud_hardware_experiment.ipynb>`_        | |tag_exp|                    | |tag_qcloud| |tag_intro|                                                  |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Berylium IBM Quantum experiment <examples/hardware_experiments/berylium_ibm_quantum.ipynb>`_                           | |tag_exp|                    | |tag_pd| |tag_qcloud|                                                     |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Umbrella inversion Braket <examples/hardware_experiments/umbrella_inversion.ipynb>`_                                   | |tag_exp|                    | |tag_pd| |tag_qcloud| |tag_ft|                                            |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `State Preparation with Quantum Signal Processing <examples/fault_tolerant/qsp_state_prep.ipynb>`_                      | |tag_ft|                     |                                                                           |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
