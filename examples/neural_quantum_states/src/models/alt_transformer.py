import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .base import Base

class AltTransformer(Base):
    def __init__(self, num_sites: int, num_spin_up: int, num_spin_down: int, embedding_dim: int=16, nhead: int=2, dim_feedforward: int=64, num_layers: int=1, temperature: float=1.0, device: str=None, **kwargs):
        '''
        A Transformer-based autoregressive NQS Ansatz using the phase strategy from Bennewitz et al, where a single linear layer operators on the concated list of transformer hidden states in lieu of a seperate phase network.
        Parent class args:
            num_sites: number of qubits in the ansatz system
            num_spin_up: total occupancy number of spin-up spin-orbitals
            num_spin_down: total occupancy number of spin-down spin-orbitals
            device: Device (CPU or Cuda) to store model
        Child class specific args:
            embedding_dim: dimension of transformer hidden states
            nhead: number of attention heads
            dim_feedforward: dimension of transformer feedforward layer
            num_layers: number of transformer blocks
            temperature: modulus network softmax temperature parameter
            device: device to store model on
        '''
        super(AltTransformer, self).__init__('AltTransformer', num_sites, num_spin_up, num_spin_down, device)

        # construct model
        self.num_in, self.num_out = num_sites, num_sites*2
        self.temperature = temperature
        # Sample function samples spatial orbitals in reverse order, but spin-up orbitals are always sampled first. self.input_order calculates this order for sampling.
        self.input_order = np.stack([np.arange(self.num_sites-2,-1,-2), np.arange(self.num_sites-1,-1,-2)],1).reshape(-1) # [4,5,2,3,0,1]
        self.input_order = torch.Tensor(self.input_order).int().to(self.device)
        # Calculate spatial orbital sampling order
        self.shell_order = torch.arange(self.num_sites//2-1, -1, -1) # [2,1,0]
        
        transformer_layer = nn.TransformerEncoderLayer(embedding_dim, nhead, dim_feedforward=dim_feedforward, dropout=0.0, batch_first=True)
        self.transformer = nn.TransformerEncoder(transformer_layer, num_layers)
        self.fc = nn.Linear(embedding_dim, 4)
        self.tok_emb = nn.Embedding(5, embedding_dim)
        self.pos_emb = nn.Embedding(len(self.shell_order), embedding_dim)
        self.apply(self._init_weights)
        self.softmax = nn.Softmax(dim=-1)
        self.log_softmax = nn.LogSoftmax(dim=-1)

        self.net_phase = nn.Linear(in_features=embedding_dim*len(self.shell_order), out_features=4, bias=True)

        self.mask = torch.zeros((len(self.shell_order), len(self.shell_order))).to(self.device)
        for i in range(len(self.mask)):
            for j in range(len(self.mask)):
                if i < j:
                    self.mask[i][j] = float('-inf') 
        
    def _init_weights(self, module: nn.Module):
        '''
        Performs weight initialization for each module in ansatz, dependent on module type
        Args:
            module: module to be initialized
        '''
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            torch.nn.init.zeros_(module.bias)
            torch.nn.init.ones_(module.weight)

    def forward(self, x: torch.Tensor, sample_shell: int = 0) -> torch.Tensor:
        '''
        Forward function for Transformer ansatz (used for both sampling and training)
        Args:
            x: qubit spin configuration
            sample_shell: shell index provided during sampling to avoid extraneous forward passes
        Returns:
            prob_cond/log_psi: either conditional probabilities of logarithms of statevector entries, depending on if sampling
        '''
        # x: [bs, num_sites]
        shells = self.state2shell(x)[:, self.shell_order]
        input = 4*torch.ones(shells.shape, dtype=torch.int64).to(self.device) 
        input[:,1:] = shells[:,:-1]
        pos = self.shell_order.to(self.device)

        input = self.tok_emb(input) + self.pos_emb(pos)
        # new x is of shape (batch_size, sequence_length, d_model)

        if self.mask.device != self.device:
            self.mask = self.mask.to(self.device)
        output = self.transformer(input[:,:(len(self.shell_order) - sample_shell + 1)], mask=self.mask[:(len(self.shell_order) - sample_shell + 1),:(len(self.shell_order) - sample_shell + 1)], is_causal=True)
        
        if not self.sampling:
            phase_input = output.reshape(output.shape[0], -1)
        output = self.fc(output)
        
        if output.shape[1] < len(self.shell_order):
            new_output = torch.zeros(output.shape[0], len(self.shell_order), output.shape[2]).to(self.device)
            new_output[:,:output.shape[1],:] = output
            output = new_output[:, self.shell_order]
        else:
            output = output[:, self.shell_order]
        
        if (self.num_spin_up + self.num_spin_down) >= 0:
            logits_cls = self.apply_constraint(x, output)
        logits_cls /= self.temperature
        
        if self.sampling:
            prob_cond = self.softmax(logits_cls)
            return prob_cond
        else:
            log_psi_cond = 0.5 * self.log_softmax(logits_cls)
            idx = self.state2shell(x)
            log_psi_real = log_psi_cond.gather(-1, idx.unsqueeze(-1)).sum(-1).sum(-1)
            log_psi_imag = self.net_phase(phase_input).gather(-1, idx[:, -1].unsqueeze(-1)).squeeze()
            if log_psi_real.shape[0] == 1:
                log_psi_imag = log_psi_imag.reshape(log_psi_real.shape)
            log_psi = torch.stack((log_psi_real, log_psi_imag), dim=-1)
            return log_psi

    def apply_constraint(self, inp: torch.Tensor, log_psi_cond: torch.Tensor) -> torch.Tensor:
        '''
        Applies constraints that enforce particle number and spin on ansatz network
        Args:
            inp: input spin configurations
            log_psi_cond: unconstrained ansatz outputs
        Returns:
            log_psi_cond: ansatz outputs with constraint applied
        '''
        # convert [|-1,-1>, |1,-1>, |-1,1>, |1,1>] to [0, 1, 2, 3]
        device = inp.device
        N = inp.shape[-1] // 2
        inp_up = inp[:, self.input_order][:, ::2].clone()
        inp_down = inp[:, self.input_order][:, 1::2].clone()
        inp_cumsum_up = torch.cat((torch.zeros((inp_up.shape[0],1)).to(device), ((1 + inp_up)/2).cumsum(-1)[:, :-1]), axis=-1)
        inp_cumsum_down = torch.cat((torch.zeros((inp_down.shape[0],1)).to(device), ((1 + inp_down)/2).cumsum(-1)[:, :-1]), axis=-1)
        upper_bound_up = self.num_spin_up
        lower_bound_up = (self.num_spin_up - (N - torch.arange(1, N+1)))
        condition1_up = (inp_cumsum_up < lower_bound_up.to(device)).float()
        condition2_up = (inp_cumsum_up >= upper_bound_up).float()
        upper_bound_down = self.num_spin_down
        lower_bound_down = (self.num_spin_down - (N - torch.arange(1, N+1)))
        condition1_down = (inp_cumsum_down < lower_bound_down.to(device)).float()
        condition2_down = (inp_cumsum_down >= upper_bound_down).float()
        idx = torch.sort(self.shell_order)[1]
        # first entry must be down
        log_psi_cond[:,:,0].masked_fill_(condition1_up[:,idx]==1, float('-inf'))
        log_psi_cond[:,:,2].masked_fill_(condition1_up[:,idx]==1, float('-inf'))
        # second entry must be down
        log_psi_cond[:,:,0].masked_fill_(condition1_down[:,idx]==1, float('-inf'))
        log_psi_cond[:,:,1].masked_fill_(condition1_down[:,idx]==1, float('-inf'))
        # first entry must be up
        log_psi_cond[:,:,1].masked_fill_(condition2_up[:,idx]==1, float('-inf'))
        log_psi_cond[:,:,3].masked_fill_(condition2_up[:,idx]==1, float('-inf'))
        # second entry must be up
        log_psi_cond[:,:,2].masked_fill_(condition2_down[:,idx]==1, float('-inf'))
        log_psi_cond[:,:,3].masked_fill_(condition2_down[:,idx]==1, float('-inf'))
        return log_psi_cond

    @torch.no_grad()
    def sample(self, bs: int, num_samples: int) -> [torch.Tensor, torch.Tensor]:
        '''
        Generates a set of samples from the ansatz state vector distribution
        Inputs:
            bs: total number of unique samples desired
            num_samples: total number of non-unique samples desired
        Returns:
            uniq_samples: unique spin sample set
            uniq_counts: tensor of count values (summing to num_samples) corresponding with uniq_samples
        '''
        self.eval()
        self.sampling = True
        sample_multinomial = True
        # random initialize a configuration of values +- 1
        uniq_samples = (torch.randn(1, self.num_sites).to(self.device) > 0.0).float() * 2 - 1
        uniq_count = torch.tensor([num_samples]).to(self.device)
        for i in self.shell_order:
            prob = self.forward(uniq_samples, i)[:, i] # num_uniq, 4
            num_uniq = uniq_samples.shape[0]
            uniq_samples = uniq_samples.repeat(4,1) # 4*num_uniq, num_sites
            # convert [|-1,-1>, |1,-1>, |-1,1>, |1,1>] to [0, 1, 2, 3]
            uniq_samples[:num_uniq, 2*i] = -1
            uniq_samples[:num_uniq, 2*i+1] = -1
            uniq_samples[num_uniq:2*num_uniq, 2*i] = 1
            uniq_samples[num_uniq:2*num_uniq, 2*i+1] = -1
            uniq_samples[2*num_uniq:3*num_uniq, 2*i] = -1
            uniq_samples[2*num_uniq:3*num_uniq, 2*i+1] = 1
            uniq_samples[3*num_uniq:4*num_uniq, 2*i] = 1
            uniq_samples[3*num_uniq:4*num_uniq, 2*i+1] = 1
            if sample_multinomial:
                uniq_count = torch.tensor(self.multinomial_arr(uniq_count.long().data.cpu().numpy(), prob.data.cpu().numpy())).T.flatten().to(prob.device)
            else:
                uniq_count = (uniq_count.unsqueeze(-1)*prob).T.flatten().round()
            keep_idx = uniq_count > 0
            uniq_samples = uniq_samples[keep_idx]
            uniq_count = uniq_count[keep_idx]
            uniq_samples = uniq_samples[uniq_count.sort()[1][-2*bs:]]
            uniq_count = uniq_count[uniq_count.sort()[1][-2*bs:]]
        uniq_samples = uniq_samples[uniq_count.sort()[1][-bs:]]
        uniq_count = uniq_count[uniq_count.sort()[1][-bs:]]
        self.sampling = False
        self.train()
        return [uniq_samples, uniq_count]
