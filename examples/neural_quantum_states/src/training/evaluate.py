import numpy as np
import torch
import torch.distributed as dist

from src.complex import real, imag, exp, scalar_mult, conjugate

def test(model: torch.nn.Module, hamiltonian: torch.nn.Module, batch_size: int, num_samples: int, mini_bs: int, global_rank: int, world_size: int) -> [torch.Tensor, float, float, int, torch.Tensor]:
    '''
    Estimates the expected value of the problem Hamiltonian in the state encoded by the NQS ansatz through parallelized autoregressive sampling
    Args:
        model: NQS ansatz
        hamiltonian: Problem Hamiltonian
        batch_size: maximum number of unique samples per GPU for sampling
        num_samples: number of non-unique samples to use for expectation estimation
        mini_bs: largest number of unique samples each GPU is expected to process at one time
        global_rank: identifying index of each GPU across all GPUs
        world_size: total number of GPUs
    Returns:
        mean: Sample mean estimating Hamiltonian expectation value
        score: Real part of sample mean (Imaginary part should average to zero; fluctuations ignored for ease of calculation
        std: Score root of sample variance
        num_uniq: number of unique samples obtained
        entropy: sample mean estimating entropy of ansatz distribution
    '''
    device = list(model.parameters())[0].device
    model.eval()
    with torch.no_grad():
        # Generate samples
        if world_size > 1:
            samples = model.module.sample(batch_size*world_size, num_samples)
        else:
            samples = model.sample(batch_size*world_size, num_samples)
        if samples[0].shape[0] < world_size:
            repeat_count = np.ceil(world_size/samples[0].shape[0]).astype(np.int64)
            samples[0] = samples[0].repeat(repeat_count,1)
            samples[1] = samples[1].repeat(repeat_count)
        if samples[0].shape[0] < batch_size*world_size:
            batch_size = np.ceil(samples[0].shape[0] / world_size).astype(np.int64)
            if batch_size * (world_size - 1) >= samples[0].shape[0]:
                batch_size -= 1
        if isinstance(samples, list):
            samples, count = samples
            weight = count / count.sum()
        else:
            weight = 1 / samples.shape[0] * torch.ones([samples.shape[0]])
        if isinstance(samples, (np.ndarray, np.generic)):
            samples = torch.tensor(samples).float().to(device)
        num_uniq = samples.shape[0]
        if hamiltonian.name in ['surrogate']:
            hamiltonian.obtain_log_entries(samples, model, global_rank, world_size, mini_bs)
        partition = world_size - global_rank - 1
        if global_rank == 0:
            samples = samples[partition*batch_size:]
            weight = weight[partition*batch_size:]
        else:
            samples = samples[partition*batch_size:(partition+1)*batch_size]
            weight = weight[partition*batch_size:(partition+1)*batch_size]
        # Calculate number of inner iterations to process all samples
        inner_iter = torch.tensor(np.ceil(samples.shape[0]/mini_bs).astype(np.int64)).to(global_rank)
        if world_size > 1:
            dist.all_reduce(inner_iter, op=dist.ReduceOp.MAX)
        sbs = torch.ceil(samples.shape[0]/inner_iter).int()
        scores = []
        log_psi_batch = []
        # Calculate local energy values in minibatches
        for i in range(inner_iter):
            if i*sbs < samples.shape[0]:
                score, log_psi = hamiltonian.compute_local_energy(samples[i*sbs:(i+1)*sbs], model)
                scores.append(score.float())
                log_psi_batch.append(log_psi.float())
            else:
                continue
        scores = torch.cat(scores, dim=0)
        weight = weight.to(scores.device)
        log_psi_batch = torch.cat(log_psi_batch, dim=0)
        if world_size > 1: # Need to collect calculated values in case of GPU parallelization
            mean = (scores * weight.unsqueeze(-1)).sum(0)
            dist.all_reduce(mean, op=dist.ReduceOp.SUM)
            score = real(mean)
            std = ((real(scores) - score)**2 * weight).sum()
            dist.all_reduce(std, op=dist.ReduceOp.SUM)
            std = std.sqrt()
            averaged_log_psi = (log_psi_batch * weight.unsqueeze(-1)).sum(0)
            dist.all_reduce(averaged_log_psi, op=dist.ReduceOp.SUM)
            averaged_log_psi[1]=0.0
            entropy = -2*averaged_log_psi
        else:
            mean = (scores * weight.unsqueeze(-1)).sum(0)
            score = real(mean)
            std = ((real(scores) - score)**2 * weight).sum().sqrt()
            averaged_log_psi = (log_psi_batch * weight.unsqueeze(-1)).sum(0)
            averaged_log_psi[1]=0.0
            entropy = -2*averaged_log_psi
    return mean, score.item(), std.item(), num_uniq, entropy
