import numpy as np
import torch

from collections import Counter
from src.complex import exp, scalar_mult, real, norm_square
from .hamiltonian import Hamiltonian


class AdaptiveShadows(Hamiltonian):
    '''
    A variation of Automatic that stochastically estimates the Hamiltonian using Adaptive Pauli Shadows, a classical shadows--based Monte Carlo method that samples from Pauli strings: https://arxiv.org/abs/2105.12207
    This estimated Hamiltonian can then be used to generate local energy estimates during NQS training. Code has not been adquately tested and its accuracy is not completely known
    Args:
        hamiltonian_string: Pauli string representation of Hamiltonian
        num_sites: qubit number of system
        sample_count: Maximum number of Pauli string samples desired
        total_unique_samples: Total number of unique Pauli string samples desired
        reset_prob: Probability to resample Pauli strings
        flip_bs: Number of unique bit flip patterns processed at a time on each GPU
    '''
    def __init__(self, hamiltonian_string: str, num_sites: int, sample_count: int, total_unique_samples: int, reset_prob: float, flip_bs: int, **kwargs):
        super(AdaptiveShadows, self).__init__('adaptive_shadows', hamiltonian_string, num_sites)
        # product of identity operators by default, encoded as 0
        self.coefficients = torch.stack((self.coefficients.real, self.coefficients.imag), dim=-1)
        self.coefficients_square = norm_square(self.coefficients)
        self.sample_count = sample_count
        self.total_unique_samples = total_unique_samples
        self.reset_prob = reset_prob
        self.flip_bs = flip_bs
        self.sample_X_idx, self.sample_Y_idx, self.sample_Z_idx, cover_list = self.generate_sample_paulis(self.sample_count)
        self.covers = {}
        self.sample_coeffs = torch.zeros(self.sample_count, 2)
        self.sample_counts = Counter()
        for i in range(len(cover_list)):
            cover = cover_list[i]
            self.covers[i] = cover
            self.sample_counts.update(cover)
        del(cover_list)
        self.generate_coefficients()
        self.generate_loss_idxs()
        self.counter = 0 # Counter to keep track of which term to replace when updating sample list
        
    def generate_coefficients(self):
        '''
        Generates coefficients in Hamiltonian
        '''
        for i in range(len(self.sample_Z_idx)):
            cover = self.covers[i]
            keys = list(cover.keys())
            self.sample_coeffs[i] = (self.coefficients[keys]/torch.tensor([self.sample_counts[key] for key in keys]).to(self.coefficients.device).reshape(-1,1)).sum(0).to(self.sample_coeffs.device)
        part1 = (-1j)**self.sample_Y_idx.sum(-1)
        part1 = torch.stack((part1.real, part1.imag), dim=-1).float().to(self.sample_coeffs.device)
        self.sample_coeffs = scalar_mult(self.sample_coeffs, part1)
    
    def generate_loss_idxs(self):
        '''
        Generate unique bit flip patterns and indices mapping them to each term in the Hamiltonian
        '''
        flip_idx = self.sample_X_idx + self.sample_Y_idx
        self.select_idx = self.sample_Y_idx + self.sample_Z_idx
        self.unique_flips, self.unique_indices = torch.unique(flip_idx, return_inverse=True, dim=0)
        self.unique_flips = 1 - 2*self.unique_flips.unsqueeze(0)
        self.unique_num_terms = self.unique_flips.shape[1]

    def update_sample_batch(self):
        '''
        Updates existing sample batch with  a new Pauli string sample
        '''
        new_sample_x, new_sample_y, new_sample_z, new_cover = self.generate_sample_paulis(1)
        if self.sample_X_idx.shape[0] < self.total_unique_samples:
            self.sample_X_idx = torch.cat((self.sample_X_idx, new_sample_x.unsqueeze(0)), dim=0)
            self.sample_Y_idx = torch.cat((self.sample_Y_idx, new_sample_y.unsqueeze(0)), dim=0)
            self.sample_Z_idx = torch.cat((self.sample_Z_idx, new_sample_z.unsqueeze(0)), dim=0)
            self.covers[self.sample_X_idx.shape[0] - 1] = new_cover[0]
            self.sample_counts.update(new_cover[0])
            self.sample_coeffs = torch.cat((self.sample_coeffs, torch.zeros(1,2).to(self.sample_coeffs.device)), dim=0)
        else:
            self.sample_X_idx[self.counter] = new_sample_x
            self.sample_Y_idx[self.counter] = new_sample_y
            self.sample_Z_idx[self.counter] = new_sample_z
            old_cover = self.covers[self.counter]
            self.covers[self.counter] = new_cover[0]
            self.sample_counts.subtract(old_cover)
            self.sample_counts.update(new_cover[0])
            self.counter = (self.counter+1)%self.total_unique_samples
        self.generate_coefficients()
        self.generate_loss_idxs()


    def generate_sample_paulis(self, num_samples: int) -> [torch.Tensor, torch.Tensor, torch.Tensor, Counter]:
        '''
        Generates one (or several) Pauli string samples according to Adaptive Pauli Shadows sampling scheme
        Args:
            num_samples: Number of new samples desired
        Returns:
            samples: indexes specifying locations of X, Y, and Z matrices in sample strings; separate index arrays for each letter
            covers: a Counter object showing which Hamiltonian terms are covered by each string according to Adaptive Pauli Shadows
        '''
        samples = torch.zeros(num_samples, self.input_dim) # 'X' is 1, 'Y' is 2, 'Z' is 3, 'I' is 0
        covers = [Counter(dict(zip(np.arange(self.num_terms), np.ones(self.num_terms)))) for _ in range(num_samples)] # Dictionaries of potential covers for each Pauli sample
        for i in range(num_samples):
            orders = torch.randperm(self.input_dim)
            for qubit in orders:
                candidates = list(covers[i].keys())
                cover_partition = [Counter(), Counter(), Counter(), Counter()] # 'I' is 0, 'X' is 1, 'Y' is 2, 'Z' is 3
                for term in candidates:
                    cover_partition[self.operators[term, qubit]][term] = covers[i][term]
                    del covers[i][term]
                covers[i].update(cover_partition[0])
                prob_vector = torch.zeros(4)
                all_zero = True
                for j in range(1,4):
                    if len(cover_partition[j]) == 0:
                        continue
                    else:
                        values = self.coefficients_square[list(cover_partition[j].keys())]
                        prob = torch.sqrt(sum(values))
                        if prob > 0:
                            all_zero = False
                        prob_vector[j] = prob
                if all_zero:
                    prob[1:] = 1.0
                sample = torch.multinomial(prob_vector, 1)
                samples[i, qubit] = sample
                covers[i].update(cover_partition[sample])
        samples = samples.squeeze().to(self.coefficients.device)
        return (samples==1).int(), (samples==2).int(), (samples==3).int(), covers

    def compute_local_energy(self, x, model):
        '''
        Compute estimated local energy values of Hamiltonian, using Pauli string samples, w.r.t. batch of qubit spin configurations and an ansatz model
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
            self.update_sample_batch()
        process_bs = int(np.ceil(self.unique_num_terms*bs/self.flip_bs))
        # first obtain model output for input batch # [bs, 2]
        log_psi = model(x) # [bs, 2]i
        with torch.no_grad():
            # log_psi_k comprises model outputs corresponding to unique flips of the Hamiltonian for each batch sample # [bs*unique_num_terms, 2]
            log_psi_k = torch.zeros(bs*self.unique_num_terms, 2).to(x.device)
            x_k = (x.unsqueeze(1) * self.unique_flips).reshape(-1, self.input_dim) # [bs*unique_num_terms, input_dim]
            # further batching is done to conserve GPU memory footprint
            for i in range(self.flip_bs):
                log_psi_k[process_bs*i:process_bs*(i + 1)] = model(x_k[process_bs*i:process_bs*(i+1)])
        if len(log_psi.shape) == 1: # if not complex
            log_psi_k = torch.stack([log_psi_k, torch.zeros_like(log_psi_k).to(log_psi_k.device)], dim=-1)
            log_psi = torch.stack([log_psi, torch.zeros_like(log_psi).to(log_psi.device)], dim=-1)
        log_psi_k = log_psi_k.reshape(bs, self.unique_num_terms, 2) # [bs, unique_num_terms, 2]
        log_psi_k = log_psi_k[:, self.unique_indices] # [bs, num_samples, 2]
        ratio = exp(log_psi_k-log_psi.unsqueeze(1)).detach() # [bs, num_samples, 2]
        # compute matrix element
        # Eq. B3
        part2 = (x.unsqueeze(1).repeat(1, self.sample_coeffs.shape[0], 1) * self.select_idx.unsqueeze(0) + (1-self.select_idx).unsqueeze(0)).prod(-1) # [bs, num_terms]
        mtx_k = torch.stack((part2, torch.zeros_like(part2)), dim=-1)
        # total local energy
        local_energy = scalar_mult(self.sample_coeffs.unsqueeze(0), scalar_mult(mtx_k, ratio)).sum(1) # [bs, 2]
        return local_energy.detach(), log_psi

    def set_device(self, device: str):
        '''
        Sets device of Hamiltonian instance.
        '''
        self.coefficients = self.coefficients.to(device)
        self.select_idx = self.select_idx.to(device)
        self.unique_flips = self.unique_flips.to(device)
        self.unique_indices = self.unique_indices.to(device)
        self.sample_X_idx = self.sample_X_idx.to(device)
        self.sample_Y_idx = self.sample_Y_idx.to(device)
        self.sample_Z_idx = self.sample_Z_idx.to(device)
        self.sample_coeffs = self.sample_coeffs.to(device)
