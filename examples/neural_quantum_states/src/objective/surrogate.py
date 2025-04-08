import numpy as np
import itertools
import torch
import torch.distributed as dist

from tqdm import tqdm
from src.complex import exp, scalar_mult
from .hamiltonian import Hamiltonian


class Surrogate(Hamiltonian):
    def __init__(self, hamiltonian_string: str, num_sites: int, flip_bs: int, **kwargs):
        '''
        An implementation of the surrogate Hamiltonian described in https://dl.acm.org/doi/10.1145/3581784.3607061
        To minimize the number of forward passes through the ansatz needed for each gradient update step, local energies are approximated using only qubit spin configurations that are directly sampled from the ansatz distribution. Hamiltonian is stored in an identical manner to the Automatic Hamiltonian class, but two steps are required to compute local energy values (self.obtain_log_entries, self.compute_local_energy) that must occur separately at each step of the training loop.
        Args:
            hamiltonian_string: Pauli string representation of Hamiltonian
            num_sites: qubit number of system
            flip_bs: largest batch size of model input tensors that each GPU is expected to handle at once
        '''
        super(Surrogate, self).__init__('surrogate', hamiltonian_string, num_sites)
        # product of identity operators by default, encoded as 0
        self.coefficients = torch.stack((self.coefficients.real, self.coefficients.imag), dim=-1)
        self.flip_bs = flip_bs
        # find index of pauli X,Y,Z operators
        pauli_x_idx = (self.operators==1).int() # [num_terms, input_dim]
        pauli_y_idx = (self.operators==2).int() # [num_terms, input_dim]
        pauli_z_idx = (self.operators==3).int() # [num_terms, input_dim]

        del self.operators # intermediate Hamiltonian data is explicitly deleted to preserve memory
        # track the exponential of -i
        self.num_pauli_y = pauli_y_idx.sum(-1) # [num_terms]
        part1 = (-1j)**self.num_pauli_y.detach()
        part1 = torch.stack((part1.real, part1.imag), dim=-1).float()
        self.coefficients = scalar_mult(self.coefficients, part1)
        del part1
        
        # Each Pauli string in Hamiltonian corresponds with a bit flip sequence and a phase flip sequence, which are stored separately
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
    
    def obtain_log_entries(self, samples: torch.Tensor, model: torch.nn.Module, global_rank: int, world_size: int, mini_bs: int):
        '''
        For a given set of qubit spin configuration samples generated from an NQS ansatz, computes and stores within the class all entries of the model's statevector corresponding with the samples. The calculation is parallelized across all GPUs available in the system.
        Args:
            samples: a set of qubit spin configurations sampled from model
            model: an NQS ansatz
            global_rank: rank of current GPU among all GPUs
            world_size: total number of GPUs utilized
            mini_bs: maximum number of unique configurations processed at once on each GPU
        '''
        self.global_rank = global_rank
        self.world_size = world_size
        partition = global_rank
        batch_size = int(np.ceil(samples.shape[0]/world_size))
        with torch.no_grad():
            if global_rank == world_size - 1:
                sample_batch = samples[partition*batch_size:]
            else:
                sample_batch = samples[partition*batch_size:(partition+1)*batch_size]
            if world_size > 1:
                log_entry_batch = torch.zeros(batch_size, 2).to(samples.device)
            else:
                log_entry_batch = torch.zeros(sample_batch.shape[0], 2).to(samples.device)
            num_batches = int(np.ceil(sample_batch.shape[0]/mini_bs).astype(np.int64))
            model.inference = True
            for i in range(num_batches):
                if mini_bs*i >= sample_batch.shape[0]:
                    continue
                elif i == num_batches - 1:
                    final_batch = sample_batch[mini_bs*(num_batches - 1):]
                    log_entry_batch[mini_bs*(num_batches - 1):mini_bs*(num_batches - 1) + len(final_batch)] = model(final_batch)
                else:
                    log_entry_batch[mini_bs*i:mini_bs*(i + 1)] = model(sample_batch[mini_bs*i:mini_bs*(i + 1)])
            model.inference = False
            if world_size > 1:
                self.sample_log_entries = torch.zeros(world_size*batch_size, 2).to(samples.device)
                dist.all_gather_into_tensor(self.sample_log_entries, log_entry_batch)
                self.sample_configs = model.module.state2shell(samples)
            else:
                self.sample_log_entries = log_entry_batch
                self.sample_configs = model.state2shell(samples)
            sample_idxs = [(self.sample_configs[:,0] == i) for i in range(4)]
            self.sample_configs = self.sample_configs[:,1:]
            self.sample_log_entries = self.sample_log_entries[:len(self.sample_configs)]
            self.sample_log_entries = [self.sample_log_entries[i] for i in sample_idxs]
            self.sample_configs = [self.sample_configs[i] for i in sample_idxs]


    def compute_local_energy(self, x: torch.Tensor, model: torch.nn.Module) -> [torch.Tensor, torch.Tensor]:
        '''
        Compute local energy values of Hamiltonian w.r.t. batch of qubit spin configurations and an ansatz model. Unlike the Automatic class, which computes local energies exactly, this function approximates local energies by only incorporating terms corresponding with sampled qubit spin configurations previously obtained with self.obtain_log_entries. The calculation matching configurations that appear in the Hamiltonian with configurations in the sample set is parallelized across all available GPUs.
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
        # first obtain model output for input batch # [bs, 2]
        log_psi = model(x) # [bs, 2]
        with torch.no_grad():
            # log_psi_k comprises model outputs corresponding to unique flips of the Hamiltonian for each batch sample # [bs*unique_num_terms, 2]
            if self.world_size > 1:
                x_k = model.module.state2shell((x.unsqueeze(1) * self.unique_flips).reshape(-1, self.input_dim)) # [bs*unique_num_terms, input_dim]
            else:
                x_k = model.state2shell((x.unsqueeze(1) * self.unique_flips).reshape(-1, self.input_dim)) # [bs*unique_num_terms, input_dim]
            # further batching is done to conserve GPU memory footprint
            x_k, x_k_idx = torch.unique(x_k, sorted=True, return_inverse=True, dim=0)
            if self.world_size > 1:
                max_num_uniqs = torch.Tensor([x_k.shape[0]]).to(x.device)
                dist.all_reduce(max_num_uniqs, op=dist.ReduceOp.MAX)
                max_num_uniqs = int(max_num_uniqs)
                collected_uniqs = torch.zeros(max_num_uniqs*self.world_size, x_k.shape[1], dtype=x_k.dtype).to(x.device)
                dist.all_gather_into_tensor(collected_uniqs, torch.cat([x_k, (torch.zeros(max_num_uniqs - x_k.shape[0], x_k.shape[1], dtype=x_k.dtype).to(x.device) - 1)]))
                full_x_k, full_x_k_idx = torch.unique(collected_uniqs, sorted=True, return_inverse=True, dim=0)
                uniq_idxs = [(full_x_k[:,0] == i) for i in range(4)]
                full_x_k = full_x_k[:,1:]
                split_uniqs = [full_x_k[i] for i in uniq_idxs]
                uniq_batches = []
                log_psi_k_batches = [] 
                for uniq_bundle in split_uniqs:
                    batch_size = np.ceil(uniq_bundle.shape[0]/self.world_size).astype(np.int64)
                    uniq_batch = uniq_bundle[self.global_rank*batch_size:(self.global_rank + 1)*batch_size]
                    uniq_batches.append(uniq_batch)
                    log_psi_k_batch = torch.zeros(uniq_batch.shape[0], 2).to(x.device)
                    log_psi_k_batch[:,0] = float('-inf')
                    log_psi_k_batches.append(log_psi_k_batch)
                split_uniqs = [torch.zeros(int(np.ceil(entry.shape[0]/self.world_size))*self.world_size, 2).to(x.device) for entry in split_uniqs]
                log_psi_k = torch.zeros(full_x_k.shape[0], 2).to(x.device)
                log_psi_k[:,0] = float('-inf')
            else:
                uniq_idxs = [(x_k[:,0] == i) for i in range(4)]
                x_k = x_k[:,1:]
                uniq_batches = [x_k[i] for i in uniq_idxs]
                log_psi_k = torch.zeros(x_k.shape[0],2).to(x.device)
                log_psi_k[:,0] = float('-inf')
                log_psi_k_batches = [log_psi_k[i] for i in uniq_idxs]
       
            for i in range(4):
                if len(uniq_batches[i]) == 0 or len(self.sample_configs[i]) == 0:
                    continue
                else:
                    sbs = int(np.ceil(uniq_batches[i].shape[0]/self.flip_bs))
                    num_batches = int(np.ceil(uniq_batches[i].shape[0]/sbs))
                    for j in range(num_batches):
                        if j*sbs >= uniq_batches[i].shape[0]:
                            continue
                        else:
                            commonalities = torch.nonzero(((uniq_batches[i][j*sbs:(j+1)*sbs].unsqueeze(1) - self.sample_configs[i]) == 0).prod(-1))
                            if torch.numel(commonalities) > 0:
                                log_psi_k_batches[i][commonalities[:,0] + j*sbs] = self.sample_log_entries[i][commonalities[:,1]]
            if self.world_size > 1:
                for i in range(4):
                    dist.all_gather_into_tensor(split_uniqs[i], torch.cat([log_psi_k_batches[i], float('inf')*torch.ones(int(split_uniqs[i].shape[0]/self.world_size) - log_psi_k_batches[i].shape[0], log_psi_k_batches[i].shape[1]).to(x.device)]))
                    split_uniqs[i] = split_uniqs[i][split_uniqs[i][:,0] != float('inf')]
                    log_psi_k[uniq_idxs[i]] = split_uniqs[i]
                log_psi_k = log_psi_k[full_x_k_idx]
                log_psi_k = log_psi_k[self.global_rank*max_num_uniqs: self.global_rank*max_num_uniqs + x_k.shape[0]]
            else:
                for i in range(4):
                    log_psi_k[uniq_idxs[i]] = log_psi_k_batches[i]
            log_psi_k = log_psi_k[x_k_idx]

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
        Args:
            device: name of Cuda device to which Hamiltonian is being sent
        '''
        self.coefficients = self.coefficients.to(device)
        self.num_pauli_y = self.num_pauli_y.to(device)
        self.select_idx = self.select_idx.to(device)
        self.unique_flips = self.unique_flips.to(device)
        self.unique_indices = self.unique_indices.to(device)

if __name__ == '__main__':
    pass
