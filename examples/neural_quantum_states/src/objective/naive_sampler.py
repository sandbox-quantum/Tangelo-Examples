import numpy as np
import torch

from src.complex import exp, scalar_mult
from .hamiltonian import Hamiltonian


class NaiveSampler(Hamiltonian):
    def __init__(self, hamiltonian_string: str, num_sites: int, sample_count: int, total_unique_samples: int, reset_prob: float, flip_bs: int, **kwargs):
        '''
        A variation of the Automatic class that stochastically estimates the input Hamiltonian with Pauli strings sampled from the distribution proportional to the absolute values of the scalar coefficients (simple to construct because the Pauli string coefficients are real for Hamiltonians). This estimated Hamiltonian can be used to create local energy estimates during NQS training for (ideally) lower computational cost.
        '''
        super(NaiveSampler, self).__init__('naive_sampler', hamiltonian_string, num_sites)
        self.flip_bs = flip_bs
        # product of identity operators by default, encoded as 0
        self.coefficients = torch.stack((self.coefficients.real, self.coefficients.imag), dim=-1)
        # find index of pauli X,Y,Z operators
        pauli_x_idx = (self.operators==1).int() # [num_terms, input_dim]
        pauli_y_idx = (self.operators==2).int() # [num_terms, input_dim]
        pauli_z_idx = (self.operators==3).int() # [num_terms, input_dim]
        del self.operators
        # create the probability tensor and change the coefficient tensor to a sign tensor
        self.probabilities = torch.abs(self.coefficients[:,0])
        self.norm_constant = torch.sum(self.probabilities)
        self.probabilities = self.probabilities/self.norm_constant
        self.coefficients = torch.sign(self.coefficients)
        # track the exponential of -i
        self.num_pauli_y = pauli_y_idx.sum(-1) # [num_terms]
        part1 = (-1j)**self.num_pauli_y.detach().cpu().numpy()
        part1 = torch.stack((torch.tensor(part1.real), torch.tensor(part1.imag)), dim=-1).float()
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
        unique_flips, unique_indices = np.unique(np.array(flip_idx), axis=0, return_inverse=True)
        self.unique_flips = torch.tensor(unique_flips)
        self.unique_indices = torch.tensor(unique_indices)
        self.unique_num_terms = self.unique_flips.shape[0]
        self.sampler = Alias_Sampler(self.probabilities, total_unique_samples)
        self.sample_count = sample_count
        self.generate_sample_hamiltonian()
        self.reset_prob = reset_prob

    def generate_sample_hamiltonian(self, device='cpu'):
        '''
        Generates a new stochastic estimate of the Hamiltonian from coefficient distribution
        Args:
            device: device on which to place relevant attribute tensors
        '''
        samples, counts = self.sampler(self.sample_count, device)
        counts = (counts/torch.sum(counts)).to(self.coefficients.device) # convert counts to weights
        self.coefficients_batch = self.coefficients[samples]*(counts.reshape(-1,1))
        self.select_idx_batch = self.select_idx[samples]
        flips = self.unique_flips[self.unique_indices[samples]]
        self.unique_flips_batch, self.unique_indices_batch = torch.unique(flips, return_inverse=True, dim=0)
        self.unique_flips_batch = 1 - 2*self.unique_flips_batch.unsqueeze(0)
        self.unique_num_terms_batch = self.unique_flips_batch.shape[1]
        self.num_terms_batch = self.coefficients_batch.shape[0]
    
    def compute_local_energy(self, x, model):
        '''
        Compute local energy values of estimated Hamiltonian w.r.t. batch of qubit spin configurations and an ansatz model. Randomly resamples the Hamiltonian estimate.
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
        # Randomly regenerate sample Hamiltonian batch
        if torch.rand(1) < self.reset_prob:
            self.generate_sample_hamiltonian(model.device)
        process_bs = int(np.ceil(self.unique_num_terms_batch*bs/self.flip_bs))
        # first obtain model output for input batch # [bs, 2]
        log_psi = model(x)
        with torch.no_grad():
            # log_psi_k comprises model outputs corresponding to unique flips of Hamiltonian batch for eachn sample [bs*unique_num_terms_batch, 2]
            log_psi_k = torch.zeros(bs*self.unique_num_terms_batch, 2).to(x.device)
            x_k = (x.unsqueeze(1) * self.unique_flips_batch).reshape(-1, self.input_dim) # [bs*unique_num_terms_batch, input_dim]
            # further batching is done to conserve GPU memory footprint
            for i in range(self.flip_bs):
                log_psi_k[process_bs*i:process_bs*(i + 1)] = model(x_k[process_bs*i:process_bs*(i + 1)])
        if len(log_psi.shape) == 1: # if not complex
            log_psi_k = torch.stack([log_psi_k, torch.zeros_like(log_psi_k).to(log_psi_k.device)], dim=-1)
            log_psi = torch.stack([log_psi, torch.zeros_like(log_psi).to(log_psi.device)], dim=-1)
        log_psi_k = log_psi_k.reshape(bs, self.unique_num_terms_batch, 2) # [bs, unique_num_terms_batch, 2]
        log_psi_k = log_psi_k[:, self.unique_indices_batch] # [bs, num_terms_batch, 2]
        ratio = exp(log_psi_k-log_psi.unsqueeze(1)).detach() # [bs, num_terms_batch, 2]
        # compute matrix element
        # Eq. B3
        part2 = (x.unsqueeze(1).repeat(1, self.num_terms_batch, 1) * self.select_idx_batch.unsqueeze(0) + (1-self.select_idx_batch).unsqueeze(0)).prod(-1) # [bs, num_terms]
        mtx_k = torch.stack((part2, torch.zeros_like(part2)), dim=-1)
        # total local energy
        local_energy = scalar_mult(self.coefficients_batch.unsqueeze(0), scalar_mult(mtx_k, ratio)).sum(1) # [bs, 2]
        return self.norm_constant*local_energy.detach(), log_psi

    def set_device(self, device):
        '''
        Sets device of all relevant object tensors to 'device'
        '''
        self.coefficients = self.coefficients.to(device)
        self.num_pauli_y = self.num_pauli_y.to(device)
        self.select_idx = self.select_idx.to(device)
        self.unique_flips = self.unique_flips.to(device)
        self.unique_indices = self.unique_indices.to(device)
        self.coefficients_batch = self.coefficients_batch.to(device)
        self.select_idx_batch = self.select_idx_batch.to(device)
        self.unique_flips_batch = self.unique_flips_batch.to(device)
        self.unique_indices_batch = self.unique_indices_batch.to(device)

class Alias_Sampler:
    '''
    A generic sampler module based on Walker's Alias Method: https://en.wikipedia.org/wiki/Alias_method
    Generates lookup tables for a given probability vector, allowing for constant time sampling
    '''
    def __init__(self, probabilities: torch.Tensor, num_unique: int):
        self.U_table, self.V_table, self.num_outcomes = self.generate_alias_tables(probabilities)
        self.num_unique = num_unique

    def __call__(self, num_samples: int, device: str='cpu') -> [torch.Tensor, torch.Tensor]:
        '''
        Use internal lookup tables to generate 'num_samples' nonunique samples
        Args:
            num_samples: number of nonunique samples to generate
        Returns:
            unique_samples: unique sampled Pauli strings
            counts: number of times each unique sample occurred in sampling
        '''
        uniform_samples = torch.rand(num_samples)
        intermediate_product = self.num_outcomes*uniform_samples
        samples = torch.floor(intermediate_product).int()
        tail = intermediate_product - samples
        for i in range(num_samples):
            if tail[i] < self.U_table[samples[i]]:
                continue
            else:
                samples[i] = self.V_table[samples[i]]
        unique_samples, counts = torch.unique(samples, sorted=False, return_counts=True)
        counts, indices = torch.sort(counts, descending = True)
        unique_samples = unique_samples[indices]
        if unique_samples.shape[0] > self.num_unique:
            return unique_samples[:self.num_unique], counts[:self.num_unique]
        else:
            return unique_samples.to(device), counts.to(device)

    def generate_alias_tables(self, probabilities: torch.Tensor) -> [torch.Tensor, torch.Tensor, int]:
        '''
        Generate necessary Alias method lookup tables from input probability vector
        Args:
            probabilities: input probability vector
        Returns:
            U_table: probability tables utilized by method
            V_table: alias tables utilized by method
            probabilities.shape[0]: length of probability vector
        '''
        U_table = probabilities.shape[0]*probabilities
        V_table = -1*torch.ones(probabilities.shape[0], dtype=torch.int)
        overfull = []
        underfull = []
        for i in range(len(U_table)):
            if U_table[i] > 1:
                overfull.append(i)
            elif U_table[i] < 1 and V_table[i] == -1:
                underfull.append(i)
            else:
                continue
        while len(overfull) > 0 and len(underfull) > 0:
            i = overfull.pop(0)
            j = underfull.pop(0)
            V_table[j] = i
            U_table[i] = U_table[i] + U_table[j] - 1
            if U_table[i] > 1:
                overfull.append(i)
            elif U_table[i] < 1 and V_table[i] == -1:
                underfull.append(i)
            else:
                continue
        if len(overfull) > 0 or len(underfull) > 0:
            extras = overfull + underfull
            while len(extras) > 0:
                i = extras.pop(0)
                U_table[i] = 1
        return U_table, V_table, probabilities.shape[0]
