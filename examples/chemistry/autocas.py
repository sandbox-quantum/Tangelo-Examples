"""Script to perform an SCINE autoCAS calculation for the automatic selection of
a molecule active space. SCINE autoCAS identifies the important orbitals via the
orbital entanglement evaluation. The package is open-source and can be found on
GitHub at https://github.com/qcscine/autocas.git.

Refs:
- C. J. Stein and M. Reiher, "autoCAS: A Program for Fully Automated
  Multiconfigurational Calculations", J. Comput. Chem., 2019, 40, 2216-2226.
- C. J. Stein and M. Reiher, "Automated Selection of Active Orbital Spaces",
  J. Chem. Theory Comput., 2016, 12, 1760.
- C. J. Stein, V. von Burg, and M. Reiher, "The Delicate Balance of Static and
  Dynamic Electron Correlation", J. Chem. Theory Comput., 2016, 12, 3764.
- C. J. Stein and M. Reiher, "Measuring Multi-Configurational Character by
  Orbital Entanglement", Mol. Phys., 2017, 115, 2110.
- C. J. Stein and M. Reiher, "Automated Identification of Relevant Frontier
  Orbitals for Chemical Compounds and Processes", Chimia, 2017, 71, 170.

Installation instructions:

Prerequisites:
Beforehand, autoCAS requires a quantum chemistry package to perform
complete active space (CAS) calculations. OpenMolcas can be installed using the
instructions found in the GitLab repo (https://gitlab.com/Molcas/OpenMolcas).

SCINE autoCAS:
The up-to-date installation steps can be found in the SCINE autoCAS GitHub repo
(https://github.com/qcscine/autocas).

Known issues:
Note that SCINE autoCAS has strict requirements for certain packages
(h5py==3.1.0 and numpy==1.19.5). With Python versions above 3.9, issues may
arise when attempting to build wheels for these specific packages. However,
non-exhaustive tests using Python versions above 3.9 were successful with more
recent versions of these packages. To achieve this, one can follow the
'Git + pip' method outlined in the SCINE autoCAS repository and manually modify
the 'requirements.txt' file.
"""

import os

import h5py
import numpy as np
import yaml

from scine_autocas.main_functions import MainFunctions
from tangelo import SecondQuantizedMolecule
from tangelo.algorithms.classical import FCISolver


def call_autocas(sqmol: SecondQuantizedMolecule, settings: dict) -> dict:
    """Calls SCINE autoCAS to generate the active space of a molecule.

    Args:
    - sqmol (SecondQuantizedMolecule): SecondQuantizedMolecule object
        representing the molecule.
    - settings (dict): Settings for the autoCAS calculation.

    Returns:
    - dict: Results obtained from the autoCAS workflow.
    """

    # Working in the current directory.
    root_folder = os.getcwd()
    xyz_file = os.path.join(root_folder, f"{settings['interface']['project_name']}.xyz")

    # Writing the coordinate file.
    sqmol.to_file(xyz_file)

    settings["molecule"].update({
        "charge": sqmol.q,
        "spin_multiplicity": sqmol.spin + 1,
        "xyz_file": xyz_file
    })
    settings["interface"]["settings"].update({
        "xyz_file": xyz_file,
        "basis_set": sqmol.basis,
        "uhf": sqmol.uhf
    })

    yaml_file = os.path.join(root_folder, f"autocas_settings_{settings['interface']['project_name']}.yml")

    with open(yaml_file, "w", encoding="utf-8") as file:
        yaml.dump(settings, file)

    # Calling the autocas with the generated YAML file.
    autocas_workflow = MainFunctions()
    autocas_workflow.main({
        "yaml_input": yaml_file
    })

    return autocas_workflow.results


def apply_active_space(sqmol: SecondQuantizedMolecule, autocas_results: dict) -> None:
    """Applies the active space obtained from autoCAS to the molecule. Modifies
    the 'sqmol' object by in-place freezing molecular orbitals and utilizing the
    molecular coefficients returned from autoCAS. Does not return any value.

    Args:
    - sqmol (SecondQuantizedMolecule): SecondQuantizedMolecule object
        representing the molecule.
    - autocas_results (dict): Results obtained from the autoCAS workflow.
    """

    # Get the active space.
    cas_index = autocas_results["final_orbital_indices"]
    sqmol.freeze_mos([i for i in range(sqmol.n_mos) if i not in cas_index])

    # Get the molecular orbitals coefficients from autocas.
    with h5py.File(autocas_results["interface"].orbital_file, "r") as h5_file:
        mo_coeff = np.array(h5_file.get("MO_VECTORS")).reshape((sqmol.n_mos,)*2)

    # Transposing the mo_coeff matrix, it was stored column-wise.
    sqmol.mo_coeff = mo_coeff.T

    return sqmol


if __name__ == "__main__":

    # Settings for autocas.
    root_folder = os.getcwd()
    settings = {
        "molecule": {
            "double_d_shell": False
        },
        "interface": {
            "interface": "molcas",
            "project_name": "example_for_n2",
            "environment": {"molcas_scratch_dir": os.path.join(root_folder, "molcas_scratch")},
            "settings": {"work_dir":  os.path.join(root_folder, "autocas_project")}
        }
    }

    # Create the N2/cc-pVDZ molecule.
    xyz_n2 = """
        N 0.0000 0.0000 0.0000
        N 0.0000 0.0000 1.0900
    """
    n2 = SecondQuantizedMolecule(xyz_n2, q=0, spin=0, basis="cc-pvdz")

    # Call the autocas workflow, and apply the active space selection.
    autocas_results = call_autocas(n2, settings)
    apply_active_space(n2, autocas_results)

    # Call the FCI classical solver.
    fci = FCISolver(n2)
    e_fci = fci.simulate()

    print(f"The FCI energy of the N2 / cc-pVDZ system with an active space CAS(e, o) ({n2.n_active_electrons}, {n2.n_active_mos}) is {e_fci} Ha.")
