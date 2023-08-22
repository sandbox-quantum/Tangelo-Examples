|tangelo_logo|

.. |tangelo_logo| image:: ./examples/img/tangelo_logo_gradient.png
   :width: 600
   :alt: tangelo_logo

|maintainer| |licence| |systems|

Launch this repository on Binder: |binder|

.. |maintainer| image:: https://img.shields.io/badge/Maintainer-GoodChemistry-blue
   :target: https://goodchemistry.com
.. |licence| image:: https://img.shields.io/badge/License-Apache_2.0-green
   :target: https://github.com/goodchemistryco/Tangelo/blob/main/LICENSE
.. |systems| image:: https://img.shields.io/badge/OS-Linux%20MacOS%20Windows-7373e3
.. |binder| image:: https://mybinder.org/badge_logo.svg
 :target: https://mybinder.org/v2/gh/goodchemistryco/Tangelo-Examples/main

----

Test badges

.. |tag_intro| image:: https://img.shields.io/badge/-Introduction-green
.. |tag_exp| image:: https://img.shields.io/badge/-Experiment-7373e3
.. |tag_pd| image:: https://img.shields.io/badge/-Problem%20Decomp-red
.. |tag_vqe| image:: https://img.shields.io/badge/-VQE-yellow
.. |tag_chem| image:: https://img.shields.io/badge/-Chemistry-008080
.. |tag_qcloud| image:: https://img.shields.io/badge/-QEMIST%20Cloud-blue
.. |tag_qsim| image:: https://img.shields.io/badge/-Backends-orange


.. |example_repo| https://github.com/goodchemistryco/Tangelo-Examples/blob/main/examples/

|tag_intro| 
|tag_exp|
|tag_pd|
|tag_vqe|
|tag_chem|
|tag_qcloud|
|tag_qsim|


+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| Tutorial                                                                                                                | Main tag                     | Secondary tags                                                            |
+=========================================================================================================================+==============================+===========================================================================+
| `1. The basics <|example_repo|workflow_basics/1.the_basics.ipynb>`_                                                     | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `2. QPU Connection <|example_repo|workflow_basics/2.qpu_connection.ipynb>`_                                             | |tag_qsim|                   | |tag_exp|                                                                 |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `3. Noisy Simulation <|example_repo|workflow_basics/3.noisy_simulation.ipynb>`_                                         | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Symbolic Simulation <|example_repo|workflow_basics/symbolic_simulator.ipynb>`_                                         | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Quantum Chemistry Basics <|example_repo|workflow_basics/chemistry/qchem_modelling_basics.ipynb>`_                      | |tag_chem|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Excited State methods <|example_repo|chemistry/excited_states.ipynb>`_                                                 | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `VQE <|example_repo|variational_methods/vqe.ipynb>`_                                                                    | |tag_vqe|                    | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `VQE with custom ansatz and Hamiltonian <|example_repo|variational_methods/vqe_custom_ansatz_hamiltonian.ipynb>`_       | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Adapt VQE Solver <|example_repo|variational_methods/adapt.ipynb>`_                                                     | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Iterative Qubit Coupled Cluster with Clifford Circuits <|example_repo|variational_methods/iqcc_using_clifford.ipynb>`_ | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Classical Shadows <|example_repo|measurement_reduction/classical_shadows.ipynb>`_                                      | |tag_qsim|                   | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Density Matrix Embedding Theory <|example_repo|problem_decomposition/dmet.ipynb>`_                                     | |tag_pd|                     | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `DMET Unrestricted Hartree-Fock <|example_repo|problem_decomposition/dmet_uhf.ipynb>`_                                  | |tag_pd|                     | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `MIFNO <|example_repo|problem_decomposition/mifno.ipynb>`_                                                              | |tag_pd|                     | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `ONIOM <|example_repo|problem_decomposition/oniom.ipynb>`_                                                              | |tag_pd|                     | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `End-to-End hardware experiment <|example_repo|measurement_reduction/hardware_experiments/overview_endtoend.ipynb>`_    | |tag_exp|                    | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Hardware Experiment using QEMIST Cloud <|example_repo|hardware_experiments/qemist_cloud_hardware_experiment.ipynb>`_   | |tag_exp|                    | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Berylium IBM Quantum experiment <|example_repo|hardware_experiments/berylium_ibm_quantum.ipynb>`_                      | |tag_exp|                    | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `Umbrella inversion Braket <|example_repo|hardware_experiments/umbrella_inversion.ipynb>`_                              | |tag_exp|                    | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+
| `State Preparation with Quantum Signal Processing <|example_repo|fault_tolerant/qsp_state_prep.ipynb>`_                 | |tag_exp|                    | |tag_intro|                                                               |
+-------------------------------------------------------------------------------------------------------------------------+------------------------------+---------------------------------------------------------------------------+





Welcome !

This is the repository that holds the example jupyter notebooks for `Tangelo <https://github.com/goodchemistryco/Tangelo>`_.

This includes tutorial notebooks and research related notebooks. Anyone can contribute a notebook to this repository!

If you are new to Tangelo, we suggest you start with `1. The basics <https://github.com/goodchemistryco/Tangelo-Examples/blob/main/examples/workflow_basics/1.the_basics.ipynb>`_, and
`Quantum Chemistry Basics <https://github.com/goodchemistryco/Tangelo-Examples/blob/main/examples/chemistry/qchem_modelling_basics.ipynb>`_. After that, what you are most interested in determines
where you go next.

    * `State Preparation with Quantum Signal Processing <https://github.com/goodchemistryco/Tangelo-Examples/blob/main/examples/fault_tolerant/qsp_state_prep.ipynb>`_
