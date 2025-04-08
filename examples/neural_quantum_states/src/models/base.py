import numpy as np
import torch
import torch.nn as nn
import re
import logging
from pytorch_model_summary import summary

class Base(nn.Module):
    '''
    Base template for all autoregressive NQS ansatze.
    Args:
        name: name of specific model type
        num_sites: qubit number
        num_spin_up: number of spin up electrons
        num_spin_down: number of spin down electrons
        device: Device (CPU or Cuda) to store model
        **kwargs: nonspecific kwargs
    '''
    def __init__(self, name: str, num_sites: int, num_spin_up: int, num_spin_down: int, device: str, **kwargs):
        super().__init__()
        self.name = name
        self.num_sites = num_sites
        self.num_spin_up = num_spin_up
        self.num_spin_down = num_spin_down
        self.device = device

        self.sampling = False
        self.inference = False

    def forward(self, configurations: torch.Tensor, **kwargs):
        '''
        Performs a forward pass through the ansatz for either training, sampling, or inference
        Args:
        - configurations: a batch of qubit spin configurations for either the whole system or individual orbitals
        - **kwargs: for sampling, some models require kwargs to perform forward passes
        Returns:
        - prob_cond: if self.sampling, returns conditional probabilities corresponding with configurations, possibly additional internal info
        - log_psi: if not self.sampling, returns log of stace vector entries corresponding with configurations
        '''
        pass

    def sample(self, num_uniqs: int, num_samples: int) -> [torch.Tensor, torch.Tensor]:
        '''
        Samples from model state distribution
        Args:
        - num_uniqs: maximum number of unique samples to return after sampling completes
        - num_samples: total number of nonunique samples obtained
        Returns: 
        - uniq_samples: batch of unique samples
        - uniq_count: number of times (out of num_samples) that each unique sample was obtained
        '''
        pass

    def save(self, model_save_path: str):
        '''
        Saves current model weights as .pth file
        Args:
        - model_save_path: path to which the model is saved
        Returns:
        - None
        '''
        logging.info("[*] Save model to {}...".format(model_save_path))
        torch.save(self.state_dict(), model_save_path)
        return model_save_path

    def load(self, model_load_path: str, strict: bool = True) -> torch.nn.Module:
        """
        Load pretrained model parameters from a given path.
        Args:
        - model_load_path: The path of the saved model file.
        - strict: Whether to strictly enforce that the keys in state_dict match the keys returned by model.state_dict().
        Returns:
        - model: The updated PyTorch model.
        """
        # Load the saved model from the file path
        bad_state_dict = torch.load(model_load_path, map_location='cpu')
        # Rename the keys in state_dict from 'module.' to '' (for loading into a non-DistributedDataParallel model)
        correct_state_dict = {re.sub(r'^module\.', '', k): v for k, v in bad_state_dict.items()}
        # If strict is False, only load the parameters that have the same shape as the corresponding parameters in the model
        if not strict:
            logging.info(f"Loading {len(correct_state_dict)} params")
            own_state = self.state_dict()
            final_state_dict = {}
            for name, param in correct_state_dict.items():
                if name not in own_state:
                    continue
                param = param.data
                own_param = own_state[name].data
                if own_param.shape == param.shape:
                    final_state_dict[name] = param
            correct_state_dict = final_state_dict
            logging.info(f"Loaded {len(correct_state_dict)} params")
        # Load the state_dict into the model
        self.load_state_dict(correct_state_dict, strict=strict)
        self.eval()
        self.zero_grad()
    
    def state2shell(self, states: torch.Tensor) -> torch.Tensor:
        '''
        Useful function for converting qubit spin configurations to statevector indices: i.e. converts [|0,0>, |1,0>, |0,1>, |1,1>] to [0, 1, 2, 3]
        Args:
            states: qubit spin configurations
        Returns:
            shell: statevector indices
        '''
        bs = states.shape[0]
        shell_size = 2
        shell = (states.view(bs, -1, shell_size).clamp_min(0) * torch.Tensor([1.0, 2.0]).to(states.device)).sum(-1)
        return shell.type(torch.int64)

    def multinomial_arr(self, count: np.ndarray, p: np.ndarray) -> np.ndarray:
        '''
        Samples from binomial distribution of 'count' trials with success probability 'p' (as a batch)
        Args:
        - count: batch of count values
        - p: batch of probabilities
        Returns:
        - out: batch of binomial distribution samples (as histograms)
        '''
        # Copy the count array to avoid modifying it in place
        count = np.copy(count)
        out = np.zeros_like(p, dtype=int)
        # Compute the cumulative sums of the probabilities
        ps = np.cumsum(p, axis=-1)
        # Avoid division by zero and NaNs by setting the probabilities to zero where the cumulative sum is zero
        condp = np.divide(p, ps, out=np.zeros_like(p), where=ps != 0)
        # Iterate over the columns of p in reverse order
        for i in range(p.shape[-1] - 1, 0, -1):
            # Sample from a binomial distribution using the conditional probabilities
            binsample = np.random.binomial(count, condp[..., i])
            # Update the output array and the count array
            out[..., i] = binsample
            count -= binsample
        # Assign the remaining count to the first column of the output array
        out[..., 0] = count
        return out


def get_model(model_name: str, device: str, print_model_info: bool, **kwargs) -> torch.nn.Module:
    """
    Get a PyTorch model based on the given model name and arguments.
    Args:
    - model_name: Name of the model to be loaded.
    - device: Device to be used for model inference and training.
    - print_model_info: Whether to print the model summary.
    - **kwargs: Other arguments specific to the model.
    Returns:
    - model: The loaded PyTorch model.
    """
    if model_name == 'made':
        from .made import MADE
        model = MADE(**kwargs)
    elif model_name == 'transformer':
        from .transformer import NNQSTransformer
        model = NNQSTransformer(**kwargs)
    elif model_name == 'retnet':
        from .retnet import NNQSRetNet
        model = NNQSRetNet(**kwargs)
    elif model_name == 'alt_transformer':
        from .alt_transformer import AltTransformer
        model = AltTransformer(**kwargs)
    else:
        raise ValueError(f"Unknown model_name: {model_name}")
    if print_model_info:
        print(summary(model, torch.zeros(10, model.num_sites), show_input=False))
    model.eval()
    model.device=device
    return model.to(device)

