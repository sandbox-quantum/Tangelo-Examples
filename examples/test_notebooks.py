import unittest
import subprocess
import os


def run_notebook_as_test(notebook_path):
    """ Convert python notebook into equivalent script, and run it. Return error if any. """
    try:
        subprocess.run(['jupyter', 'nbconvert', '--to', 'python', notebook_path])
        script_path = './'+os.path.splitext(notebook_path)[0] + '.py'
        directory = os.path.split(notebook_path)[0]
        filename = os.path.split(notebook_path)[1]
        filename = os.path.splitext(filename)[0]+'.py'
        os.environ['PATH'] += ':'+'./'
        subprocess.run(['chmod', '+x', script_path])
        wd = os.getcwd()
        os.chdir(directory)
        subprocess.check_output([filename])
        subprocess.run(['rm', filename])
        os.chdir(wd)
    except subprocess.CalledProcessError as e:
        subprocess.run(['rm', filename])
        os.chdir(wd)
        raise e


class TestNotebooks(unittest.TestCase):
    """ Turn target Python notebooks into script, run them as unittests (pass = no errors at runtime) """

    def test_linq_basics_notebook(self):
        run_notebook_as_test('workflow_basics/1.the_basics.ipynb')

    def test_linq_noisy_simulation_notebook(self):
        run_notebook_as_test('workflow_basics/3.noisy_simulation.ipynb')

    def test_dmet_notebook(self):
        run_notebook_as_test('problem_decomposition/dmet.ipynb')

    def test_vqe_notebook(self):
        run_notebook_as_test('variational_methods/vqe.ipynb')

    def test_adapt_notebook(self):
        run_notebook_as_test('variational_methods/adapt.ipynb')

    def test_vqe_custom_ansatz_notebook(self):
        run_notebook_as_test('variational_methods/vqe_custom_ansatz_hamiltonian.ipynb')

    def test_oniom_notebook(self):
        run_notebook_as_test('problem_decomposition/oniom.ipynb')

    def test_qmmm_notebook(self):
        run_notebook_as_test('problem_decomposition/qmmm.ipynb')

    def test_excited_states(self):
        run_notebook_as_test('chemistry/excited_states.ipynb')

    @unittest.skip("Requires qemist cloud access")
    def test_qemist_cloud_hardware_experiments_notebook(self):
        run_notebook_as_test('hardware_experiments/qemist_cloud_hardware_experiments_braket.ipynb')

    def test_classical_shadows_notebook(self):
        run_notebook_as_test('measurement_reduction/classical_shadows.ipynb')

    def test_ifci_mifno_notebook(self):
        run_notebook_as_test('problem_decomposition/ifci_mifno.ipynb')

    def test_iQCC_clifford_notebook(self):
        run_notebook_as_test('variational_methods/iqcc_using_clifford.ipynb')

    def test_overview_end_to_end_notebook(self):
        run_notebook_as_test('hardware_experiments/overview_endtoend.ipynb')

    def test_qsp_state_prep_notebook(self):
        run_notebook_as_test('fault_tolerant/qsp_state_prep.ipynb')


if __name__ == "__main__":
    unittest.main()
