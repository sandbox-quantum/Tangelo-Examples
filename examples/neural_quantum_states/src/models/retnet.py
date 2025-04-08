import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from yet_another_retnet.retnet import RetNetDecoderLayer, RetNetDecoder

from .base import Base

class NNQSRetNet(Base):
    def __init__(self, num_sites: int, num_spin_up: int, num_spin_down: int, made_width: int=64, made_depth: int=2, embedding_dim: int=16, nhead: int=2, dim_feedforward: int=64, num_layers: int=1, temperature: float=1.0, device: str=None, **kwargs):
        '''
        Retentive network (RetNet) NQS ansatz
        Parent class args:
            num_sites: number of qubits in the ansatz system
            num_spin_up: total occupancy number of spin-up spin-orbitals
            num_spin_down: total occupancy number of spin-down spin-orbitals
            device: Device (CPU or Cuda) to store model
        Child class specific args:
            made_width: width of phase network hidden layers
            made_depth: number of phase network hidden layers
            embedding_dim: dimension of RetNet embedding
            nhead: number of multi-scale retention heads
            dim_feedforward: dimension of RetNet feedforward layers
            num_layers: number of RetNet blocks
            temperature: RetNet softmax temperature parameter
            device: device on which the model is stored
        '''
        super(NNQSRetNet, self).__init__('RetNet', num_sites, num_spin_up, num_spin_down, device)

        # construct model
        self.num_in, self.num_out = num_sites, num_sites*2
        self.temperature=temperature
        self.input_order = np.stack([np.arange(self.num_sites-2,-1,-2), np.arange(self.num_sites-1,-1,-2)],1).reshape(-1) # [4,5,2,3,0,1]
        self.shell_order = torch.arange(self.num_sites//2-1, -1, -1) # [2,1,0]
        
        decoder_layer = RetNetDecoderLayer(embedding_dim, nhead, dim_feedforward=dim_feedforward, dropout=0.0)
        self.decoder = RetNetDecoder(decoder_layer, num_layers)
        self.fc = nn.Linear(embedding_dim, 4)
        self.tok_emb = nn.Embedding(5, embedding_dim)
        self.pos_emb = nn.Embedding(len(self.shell_order), embedding_dim)
        self.apply(self._init_weights)
        self.log_softmax = nn.LogSoftmax(dim=-1)
        self.softmax = nn.Softmax(dim=-1)

        self.net_phase = [nn.Linear(in_features=self.num_in-2, out_features=made_width, bias=True)]
        for i in range(made_depth):
            self.net_phase += [nn.ReLU(), nn.Linear(in_features=made_width, out_features=made_width, bias=True)]
        self.net_phase += [nn.ReLU(), nn.Linear(in_features=made_width, out_features=4, bias=True)]
        self.net_phase = nn.Sequential(*self.net_phase)

    def _init_weights(self, module: nn.Module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            torch.nn.init.zeros_(module.bias)
            torch.nn.init.ones_(module.weight)

    def forward_sample(self, x_shell: torch.Tensor, count_up: torch.Tensor, count_down: torch.Tensor, idx: int=0, prev_states: list = []) -> [torch.Tensor, list]:
        '''
        Performs a forward pass on one input token for purposes of autoregressive sampling
        Args:
            x_shell: qubit spin configurations for most recently sampled molecular orbital (2 qubits)
            count_up: spin-up occupancies for previously sampled shells
            count_down: spin-down occupancies for previously sampled shells
            idx: index for currently sampled orbital
            prev_states: internal states for RetNets
        Returns:
            prob_cond: conditional probabilities for orbital 'idx'
            prev_states: new internal RetNet states
        '''
        # x: [bs, 1]
        input = self.tok_emb(x_shell) + self.pos_emb(idx.to(self.device))
        # new x is of shape (batch_size, d_model)
        output, prev_states = self.decoder.forward_recurrent(input, self.shell_order[idx], prev_states)
      
        logits_cls = self.fc(output)
        if (self.num_spin_up + self.num_spin_down) >= 0:
            logits_cls = self.apply_constraint_sample(logits_cls, idx, count_up, count_down)
        prob_cond = self.softmax(logits_cls/self.temperature)
        
        return prob_cond, prev_states

    def forward_state(self, x: torch.Tensor) -> torch.Tensor:
        '''
        Performs a forward pass of the ansatz model to produce statevector entries (recurrent RetNet if self.inference, parallel RetNet if not)
        Args:
            x: qubit spin configurations
        Returns:
            log_psi: logarithms of ansatz entries
        '''
        # x: [bs, num_sites]
        shells = self.state2shell(x)[:, self.shell_order]
        input = 4*torch.ones(shells.shape, dtype=torch.int).to(self.device) 
        input[:,1:] = shells[:,:-1]
        # x is of shape (batch_size, sequence_length)
        pos = self.shell_order.to(self.device)

        input = self.tok_emb(input) + self.pos_emb(pos)
        # new x is of shape (batch_size, sequence_length, d_model)

        if self.inference:
            outputs = []
            prev_states = []
            for i in range(len(self.shell_order)):
                out, prev_states = self.decoder.forward_recurrent(input[:,i].squeeze(), i, prev_states)
                outputs.append(torch.unsqueeze(out, 1))
            output = torch.stack(outputs, dim=1)
        else:
            output = self.decoder.forward_parallel(input)
        output = self.fc(output)[:, self.shell_order]
        if (self.num_spin_up + self.num_spin_down) >= 0:
            logits_cls = self.apply_constraint_state(x, output)
        log_psi_cond = 0.5 * self.log_softmax(logits_cls/self.temperature)
        idx = self.state2shell(x)
        log_psi_real = log_psi_cond.gather(-1, idx.unsqueeze(-1)).sum(-1).sum(-1)
        log_psi_imag = self.net_phase(x[:, :-2]).gather(-1, idx[:, -1].unsqueeze(-1)).squeeze()
        if log_psi_real.shape[0] == 1:
            log_psi_imag = log_psi_imag.reshape(log_psi_real.shape)
        log_psi = torch.stack((log_psi_real, log_psi_imag), dim=-1)
        return log_psi

    def forward(self, x: torch.Tensor, **kwargs):
        '''
        Wrapper function that directs to either self.forward sample or self.forward_state, depending on self.sampling
        '''
        if self.sampling:
            return self.forward_sample(x, **kwargs)
        else:
            return self.forward_state(x)

    def apply_constraint_sample(self, log_psi_cond: torch.Tensor, shell_idx: torch.Tensor, sum_up: torch.Tensor, sum_down: torch.Tensor) -> torch.Tensor:
        '''
        Applies particle + spin number constraints to a single molecular orbital occupancy, for use in recurrent RetNet
        Args:
            log_psi_cond: intermediate output of modulus network for one orbital
            shell_idx: orbital index corresponding with 'log_psi_cond'
            sum_up: spin-up occupancy count for previously sampled orbitals
            sum_down: spin-down occupancies for previously sampled orbitals
        Returns:
            log_spi_cond: Properly masked RetNet outputs
        '''
        condition1_up = (sum_up < self.lower_bound_up[self.shell_order[shell_idx]]).float()
        condition2_up = (sum_up >= self.upper_bound_up).float()

        condition1_down = (sum_down < self.lower_bound_down[self.shell_order[shell_idx]]).float()
        condition2_down = (sum_down >= self.upper_bound_down).float()
        # first entry must be down
        log_psi_cond[:,0].masked_fill_(condition1_up==1, float('-inf'))
        log_psi_cond[:,2].masked_fill_(condition1_up==1, float('-inf'))
        # second entry must be down
        log_psi_cond[:,0].masked_fill_(condition1_down==1, float('-inf'))
        log_psi_cond[:,1].masked_fill_(condition1_down==1, float('-inf'))
        # first entry must be up
        log_psi_cond[:,1].masked_fill_(condition2_up==1, float('-inf'))
        log_psi_cond[:,3].masked_fill_(condition2_up==1, float('-inf'))
        # second entry must be up
        log_psi_cond[:,2].masked_fill_(condition2_down==1, float('-inf'))
        log_psi_cond[:,3].masked_fill_(condition2_down==1, float('-inf'))
        return log_psi_cond

    def apply_constraint_state(self, inp: torch.Tensor, log_psi_cond: torch.Tensor) -> torch.Tensor:
        '''
        Applies particle + spin number symmetry constraints to parallel RetNet outputs
        Args:
            inp: qubit spin configurations
            log_psi_cond: intermediate parallel RetNet outputs
        Returns:
            log_psi_cond: properly masked conditional log-probabilities
        '''
        device = inp.device
        N = inp.shape[-1] // 2
        inp_up = inp[:, self.input_order][:, ::2].clone()
        inp_down = inp[:, self.input_order][:, 1::2].clone()
        inp_cumsum_up = torch.cat((torch.zeros((inp_up.shape[0],1)).to(device), ((inp_up + 1)/2).cumsum(-1)[:, :-1]), axis=-1)
        inp_cumsum_down = torch.cat((torch.zeros((inp_down.shape[0],1)).to(device), ((inp_down + 1)/2).cumsum(-1)[:, :-1]), axis=-1)
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
        RetNet-specific Monte Carlo sampling function
        '''
        self.eval()
        self.sampling = True
        sample_multinomial = True
        # Create arrays for conditions
        N = self.num_sites//2
        self.upper_bound_up = self.num_spin_up
        self.lower_bound_up = (self.num_spin_up - (N - torch.arange(1, N+1)))
        self.upper_bound_down = self.num_spin_down
        self.lower_bound_down = (self.num_spin_down - (N - torch.arange(1, N+1)))

        # randomly initialize a configuration of values +- 1
        uniq_samples = (torch.randn(1, self.num_sites).to(self.device) > 0.0).float() * 2 - 1
        uniq_count = torch.tensor([num_samples]).to(self.device)
        count_up = torch.zeros(1).to(self.device)
        count_down = torch.zeros(1).to(self.device)
        prev_states = []
        for index in range(len(self.shell_order)):
            i = self.shell_order[index]
            if index == 0:
                model_input = 4*torch.ones(uniq_samples.shape[0], dtype=torch.int64).to(self.device)
            else:
                model_input = self.state2shell(uniq_samples[:, 2*self.shell_order[index - 1]:2*(1 + self.shell_order[index - 1])]).squeeze()
                if uniq_samples.shape[0] == 1:
                    model_input = model_input.unsqueeze(0)
            prob, prev_states = self.forward(model_input, count_up=count_up, count_down=count_down, idx=i, prev_states=prev_states) # num_uniq, 4
            num_uniq = uniq_samples.shape[0]
            uniq_samples = uniq_samples.repeat(4,1) # 4*num_uniq, num_sites
            count_up = torch.cat(4*[count_up])
            count_down = torch.cat(4*[count_down])
            # convert [|-1,-1>, |1,-1>, |-1,1>, |1,1>] to [0, 1, 2, 3]
            uniq_samples[:num_uniq, 2*i] = -1
            uniq_samples[:num_uniq, 2*i+1] = -1
            uniq_samples[num_uniq:2*num_uniq, 2*i] = 1
            uniq_samples[num_uniq:2*num_uniq, 2*i+1] = -1
            uniq_samples[2*num_uniq:3*num_uniq, 2*i] = -1
            uniq_samples[2*num_uniq:3*num_uniq, 2*i+1] = 1
            uniq_samples[3*num_uniq:4*num_uniq, 2*i] = 1
            uniq_samples[3*num_uniq:4*num_uniq, 2*i+1] = 1
            count_up[num_uniq:2*num_uniq] += 1
            count_up[3*num_uniq:4*num_uniq] += 1
            count_down[2*num_uniq:3*num_uniq] += 1
            count_down[3*num_uniq:4*num_uniq] += 1
            if sample_multinomial:
                uniq_count = torch.tensor(self.multinomial_arr(uniq_count.long().data.cpu().numpy(), prob.data.cpu().numpy())).T.flatten().to(prob.device)
            else:
                uniq_count = (uniq_count.unsqueeze(-1)*prob).T.flatten().round()
            keep_idx = uniq_count > 0
            uniq_samples = uniq_samples[keep_idx]
            uniq_count = uniq_count[keep_idx]
            prev_state_idx = torch.arange(num_uniq).repeat(4).to(self.device)
            prev_state_idx = prev_state_idx[keep_idx]
            count_up = count_up[keep_idx]
            count_down = count_down[keep_idx]
            uniq_samples = uniq_samples[uniq_count.sort()[1][-2*bs:]]
            prev_state_idx = prev_state_idx[uniq_count.sort()[1][-2*bs:]]
            for j in range(len(prev_states)):
                prev_states[j] = prev_states[j][prev_state_idx]
            count_up = count_up[uniq_count.sort()[1][-2*bs:]]
            count_down = count_down[uniq_count.sort()[1][-2*bs:]]
            uniq_count = uniq_count[uniq_count.sort()[1][-2*bs:]]
        uniq_samples = uniq_samples[uniq_count.sort()[1][-bs:]]
        uniq_count = uniq_count[uniq_count.sort()[1][-bs:]]
        self.sampling = False
        self.train()
        return [uniq_samples, uniq_count]
