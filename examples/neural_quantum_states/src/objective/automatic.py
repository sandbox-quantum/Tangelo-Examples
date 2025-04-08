import numpy as np
import torch

from src.complex import exp, scalar_mult
from .hamiltonian import Hamiltonian


class Automatic(Hamiltonian):
    def __init__(self, hamiltonian_string: str, num_sites: int, flip_bs: int, **kwargs):
        '''
        A "standard" NQS Hamiltonian object. Object takes in Pauli string form of Hamiltonian and stores it as four tensors: one storing the unique bit flip indices corresponding with all terms in the Hamiltonian, a tensor mapping those flip indices to the original Hamiltonian terms, a tensor storing the phase flip indices of the Hamiltonian terms, and the scalar coefficients
        Args:
            hamiltonian_string: Pauli string representation of Hamiltonian
            num_sites: qubit number of system
            flip_bs: largest batch size of model input tensors that each GPU is expected to handle at once
        '''
        super(Automatic, self).__init__('automatic', hamiltonian_string, num_sites)
        # product of identity operators by default, encoded as 0
        self.coefficients = torch.stack((self.coefficients.real, self.coefficients.imag), dim=-1)
        self.flip_bs = flip_bs
        # find index of pauli X,Y,Z operators
        pauli_x_idx = (self.operators==1).int() # [num_terms, input_dim]
        pauli_y_idx = (self.operators==2).int() # [num_terms, input_dim]
        pauli_z_idx = (self.operators==3).int() # [num_terms, input_dim]
        del self.operators
        # track the exponential of -i
        self.num_pauli_y = pauli_y_idx.sum(-1) # [num_terms]
        part1 = (-1j)**self.num_pauli_y.detach()
        part1 = torch.stack((part1.real, part1.imag), dim=-1).float()
        self.coefficients = scalar_mult(self.coefficients, part1)
        del part1
        # the unique element has flipped value if the corresponding pauli is x or y.
        flip_idx = pauli_x_idx + pauli_y_idx # [num_terms, input_dim]
        # self.flip_idx = flip_idx
        del pauli_x_idx
        # only the entry value with y or z pauli is multiplied
        self.select_idx = pauli_y_idx + pauli_z_idx
        del pauli_y_idx
        del pauli_z_idx
        self.unique_flips, self.unique_indices = torch.unique(flip_idx, sorted=True, return_inverse=True, dim=0)
        self.unique_flips = 1 - 2*(self.unique_flips.unsqueeze(0))
        self.unique_num_terms = self.unique_flips.shape[1]
        print('Number of unique flips in Hamiltonian: {}'.format(self.unique_num_terms))

    def compute_local_energy(self, x: torch.Tensor, model: torch.nn.Module) -> [torch.Tensor, torch.Tensor]:
        '''
        Compute local energy values of Hamiltonian w.r.t. batch of qubit spin configurations and an ansatz model
        Args:
            x: qubit spin configurations
            model: NQS ansatz
        Returns:
            local_energy: local energy values (detached from computational graph)
            log_psi: logarithms of ansatz statevector entries (attached to computational graph)
        '''
        # see appendix B of https://arxiv.org/pdf/1909.12852.pdf
        # x [bs, input_dim]
        bs = x.shape[0]
        process_bs = int(np.ceil(self.unique_num_terms*bs/self.flip_bs))
        # first obtain model output for input batch # [bs, 2]
        log_psi = model(x) # [bs, 2]
        with torch.no_grad():
            # log_psi_k comprises model outputs corresponding to unique flips of the Hamiltonian for each batch sample # [bs*unique_num_terms, 2]
            log_psi_k = torch.zeros(bs*self.unique_num_terms, 2).to(x.device)
            x_k = (x.unsqueeze(1) * self.unique_flips).reshape(-1, self.input_dim) # [bs*unique_num_terms, input_dim]
            # further batching is done to conserve GPU memory footprint
            model.inference = True
            flip_batches = np.ceil(x_k.shape[0]/process_bs).astype(np.int64)
            for i in range(flip_batches):
                log_psi_k[process_bs*i:process_bs*(i + 1)] = model(x_k[process_bs*i:process_bs*(i + 1)])
            model.inference = False
        if len(log_psi.shape) == 1: # if not complex
            log_psi_k = torch.stack([log_psi_k, torch.zeros_like(log_psi_k).to(log_psi_k.device)], dim=-1)
            log_psi = torch.stack([log_psi, torch.zeros_like(log_psi).to(log_psi.device)], dim=-1)
        log_psi_k = log_psi_k.reshape(bs, self.unique_num_terms, 2) # [bs, unique_num_terms, 2]
        log_psi_k = log_psi_k[:, self.unique_indices] # [bs, num_terms, 2]
        ratio = exp(log_psi_k-log_psi.unsqueeze(1)).detach() # [bs, num_terms, 2]
        # compute matrix element
        # Eq. B3
        part2 = (x.unsqueeze(1).repeat(1, self.num_terms, 1) * self.select_idx.unsqueeze(0) + (1-self.select_idx).unsqueeze(0)).prod(-1) # [bs, num_terms]
        mtx_k = torch.stack((part2, torch.zeros_like(part2)), dim=-1)
        # total local energy
        local_energy = scalar_mult(self.coefficients.unsqueeze(0), scalar_mult(mtx_k, ratio)).sum(1) # [bs, 2]
        return local_energy.detach(), log_psi

    def set_device(self, device: str):
        '''
        Sets device of all relevant object tensors to 'device'
        '''
        self.coefficients = self.coefficients.to(device)
        self.num_pauli_y = self.num_pauli_y.to(device)
        self.select_idx = self.select_idx.to(device)
        self.unique_flips = self.unique_flips.to(device)
        self.unique_indices = self.unique_indices.to(device)
