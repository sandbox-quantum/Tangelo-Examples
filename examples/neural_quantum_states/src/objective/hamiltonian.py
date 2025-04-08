import numpy as np
import torch
import torch.nn as nn
from src.complex import scalar_mult, real, imag

class Hamiltonian(nn.Module):
    def __init__(self, choice, hamiltonian_string, num_sites):
        super().__init__()
        self.name = choice
        self.operators, self.coefficients = self.parse_hamiltonian_string(hamiltonian_string, num_sites)
        self.num_terms, self.input_dim = self.operators.shape
        print("Number of terms is {}.".format(self.num_terms))

    def forward(self, config: torch.Tensor, model: nn.Module) -> [torch.Tensor, torch.Tensor]:
        # Wrapper function for self.compute_local_energy
        return self.compute_local_energy(config, model)

    def set_device(self, device: str): # Sets devices of all Hamiltonian attributes to 'device'
        pass

    def compute_local_energy(self, config: torch.Tensor, model: nn.Module) -> [torch.Tensor, torch.Tensor]:
        '''
        Template for computing the local energies of the Hamiltonian using a given set of spin configurations and a given model
        Args:
        - config: tensor batch of spin configurations
        - model: ansatz model
        Returns:
        - local_energies: corresponding batch of local energies, detached from model computational graph
        - log_psi: corresponding batch of model outputs, attached to model computational graph
        '''
        pass

    def parse_hamiltonian_string(self, hamiltonian_string: str, num_sites: int) -> [np.ndarray, np.ndarray]:
        '''
        Converts string encoding Hamiltonian (in Pauli string basis) to separate arrays containing Hamiltonian strings (encoded as integer vectors) and their corresponding scalar coefficients
        Args:
            hamiltonian_string: Pauli Hamiltonian represented as a string
            num_sites: Number of qubits in Hamiltonian system
        Returns:
            hmtn_ops: integer array representing Pauli strings in Hamiltonian
            params: scalar parameters
        '''
        splitted_string = hamiltonian_string.split('+\n')
        num_terms = len(splitted_string)
        params = np.zeros([num_terms]).astype(np.complex128)
        hmtn_ops = np.zeros([num_terms, num_sites])
        for i,term in enumerate(splitted_string):
            params[i] = complex(term.split(' ')[0])
            ops = term[term.index('[')+1:term.index(']')]
            ops_lst = ops.split(' ')
            for op in ops_lst:
                if op == '':
                    continue
                pauli_type = op[0]
                idx = int(op[1:])
                if pauli_type == 'X':
                    encoding = 1
                elif pauli_type == 'Y':
                    encoding = 2
                elif pauli_type == 'Z':
                    encoding = 3
                elif pauli_type == 'I':
                    encoding = 0
                else:
                    raise "Unknown pauli_type!"
                hmtn_ops[i, idx] = encoding
        return torch.tensor(hmtn_ops).int(), torch.tensor(params)

def get_hamiltonian(hamiltonian_choice: str, hamiltonian_data: dict) -> nn.Module:
    """
    Returns an instance of Hamiltonian based on the choice of Hamiltonian and additional parameters.
    Args:
        hamiltonian_choice: Choice of hamiltonian type, default is 'exact' a.k.a. 'Automatic'.
        hamiltonian_data: Dictionary of parameters specific to each Hamiltonian type
    Returns:
        Hamiltonian: An instance of Hamiltonian.
    """
    if hamiltonian_choice in ['sample']:
        from .naive_sampler import NaiveSampler
        return NaiveSampler(**hamiltonian_data)
    elif hamiltonian_choice in ['adaptive_shadows']:
        from .adaptive_shadows import AdaptiveShadows
        return AdaptiveShadows(**hamiltonian_data)
    elif hamiltonian_choice in ['exact']:
        from .automatic import Automatic
        return Automatic(**hamiltonian_data)
    elif hamiltonian_choice in ['surrogate']:
        from .surrogate import Surrogate
        return Surrogate(**hamiltonian_data)
    else:
        raise Exception('Hamiltonian choice not recognized!')

