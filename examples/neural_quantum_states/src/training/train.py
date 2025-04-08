import os
import time
import logging
from tqdm import trange
import numpy as np
import torch
import torch.nn as nn
import torch.distributed as dist
import argparse
from torch.nn.parallel import DistributedDataParallel
from tensorboardX import SummaryWriter
from tangelo.algorithms.classical import CCSDSolver, FCISolver

from src.data.data_loader import load_data
from src.training.scheduler import get_scheduler, VNAScheduler
from src.util import get_optimizer
from src.models.base import get_model
from src.complex import real, imag, conjugate, scalar_mult

from .evaluate import test
from ..objective.hamiltonian import get_hamiltonian

def train_one_batch(model: nn.Module, hamiltonian: nn.Module, optimizer: torch.optim.Optimizer, scheduler: torch.optim.lr_scheduler._LRScheduler, batch_size: int, num_samples: int, mini_bs: int, global_rank: int, world_size: int, nmlzr: torch.Tensor, epoch: int, num_epochs: int, reg_const: float, entropy: torch.Tensor) -> dict:
    '''
    Calculates local energies, estimates model gradients, and performs one gradient update
    Args:
        model: NQS Ansatz
        hamiltonian: Problem Hamiltonian
        optimizer: choice of optimizer for training
        scheduler: choice of learning rate scheduler for the optimizer
        batch_size: maximum number of unique samples per GPU
        num_samples: number of non-unique samples to generate in training
        mini_bs: maximum number of unique samples to process on each GPU at one time
        global_rank: global index among all GPUs
        world_size: total number of GPUs
        nmlzr: stochastic estimate of Hamiltonian expectation value
        epoch: current training iteration
        num_epochs: total number of training epochs
        reg_const: regularization constant for neural annealing
        entropy: stochastic estimate of ansatz entropy
    Returns:
        losses: dictionary containing loss value information for logging purposes
    '''
    model.train()
    losses = {}
    device = list(model.parameters())[0].device
    # collect samples
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
        bs = samples.shape[0]
        samples = torch.tensor(samples).float().to(device)
        weight = torch.ones([bs]).to(samples.device) / bs
    if hamiltonian.name in ['surrogate']:
        hamiltonian.obtain_log_entries(samples, model, global_rank, world_size, mini_bs)
    # get the corresponding batch for each GPU device
    partition = world_size - global_rank - 1
    if global_rank == 0:
        samples = samples[partition*batch_size:]
        weight = weight[partition*batch_size:]
    else:
        samples = samples[partition*batch_size:(partition+1)*batch_size]
        weight = weight[partition*batch_size:(partition+1)*batch_size]
    total_local_energies = []
    total_losses = []
    inner_iter = torch.tensor(np.ceil(samples.shape[0]/mini_bs).astype(np.int64)).to(global_rank)
    if world_size > 1:
        dist.all_reduce(inner_iter, op=dist.ReduceOp.MAX)
    sbs = torch.ceil(samples.shape[0]/inner_iter).int()
    # save the gradient of each small batch_size to disk and then sum them up for updates
    for i in range(inner_iter):
        if i*sbs >= samples.shape[0]:
            continue
        else:
            sbs_samples = samples[i*sbs:(i+1)*sbs]
            sbs_weight = weight[i*sbs:(i+1)*sbs]
            # train
            local_energies, log_psi = hamiltonian.compute_local_energy(sbs_samples, model)
            log_psi_conj = conjugate(log_psi)
            wt = sbs_weight.unsqueeze(-1)
            nmlzr[1] = 0.0
            if reg_const > 0.0:
                loss_grad_diff = (local_energies - nmlzr).detach()
                entropy_grad_sum = torch.zeros_like(log_psi).to(device)
                entropy_grad_sum[:,0] = 1.0 + 2.0*log_psi[:,0]
                loss = 2 * (real(scalar_mult(log_psi_conj, (loss_grad_diff + reg_const * (entropy_grad_sum + entropy)).detach()) * wt)).sum()
            else:
                loss = 2 * (real(scalar_mult(log_psi_conj, (local_energies - nmlzr).detach()) * wt)).sum()
            loss.backward()
            total_local_energies.append(local_energies)
            total_losses.append(loss.item())
    
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    scheduler.step()
    # print("Learning rate:", optimizer.param_groups[0]['lr'])
    optimizer.zero_grad()
    losses['loss'] = np.sum(total_losses)
    local_energies = torch.cat(total_local_energies, axis=0)
    mean_energy = (local_energies * weight.unsqueeze(-1)).sum(0)
    if global_rank == 0:
        score = real(mean_energy.detach())
        scores = real(local_energies.detach())
        std = ((scores - score)**2 * wt).sum().sqrt()
        losses['score'] = score.item()
        losses['std'] = std.item()
        losses['num_uniq'] = samples.shape[0]
    return losses

def train(cfg: argparse.Namespace, local_rank: int, global_rank: int) -> [[float, float], float, dict]:
    '''
    Retrieves the model, hamiltonian, and all relevant submodules for training, then performs training according to user-specified settings
    Args:
        cfg: config flags specifying training settings
        local_rank: identifying index among GPUs from the same compute node
        global_rank: identifying index among all GPUs
    Returns:
        [best_mean, best_std**2, best_num_samples]: best expectation value estimate and associated sample variance and number of samples
        time_elapsed: the amount of time that elapsed during training
        dic: dictionary of loss values saved periodically during training
    '''
    # set hyper-parameters
    logger_dir = cfg.MISC.DIR
    save_dir = cfg.MISC.SAVE_DIR
    device = torch.device('cuda:{}'.format(local_rank) if (cfg.DDP.WORLD_SIZE > 0) else 'cpu')
    world_size = cfg.DDP.WORLD_SIZE
    # train
    lr = cfg.TRAIN.LEARNING_RATE
    weight_decay = cfg.TRAIN.WEIGHT_DECAY
    num_epochs = cfg.TRAIN.NUM_EPOCHS
    bs = cfg.TRAIN.BATCH_SIZE
    opt_name = cfg.TRAIN.OPTIMIZER_NAME
    sche_name = cfg.TRAIN.SCHEDULER_NAME
    retest_interval = cfg.TRAIN.RETEST_INTERVAL
    entropy_scheduler = VNAScheduler(num_epochs, cfg.TRAIN.ANNEALING_COEFFICIENT, cfg.TRAIN.ANNEALING_SCHEDULER)
    mini_bs = cfg.TRAIN.MINIBATCH_SIZE
    # Maximum number of non-unique samples to generate during autoregressive sampling
    max_num_samples = cfg.DATA.MAX_NUM_SAMPLES
    # model
    model_name = cfg.MODEL.MODEL_NAME
    model_load_path = cfg.EVAL.MODEL_LOAD_PATH
    made_depth = cfg.MODEL.MADE_DEPTH
    made_width = cfg.MODEL.MADE_WIDTH
    embedding_dim = cfg.MODEL.EMBEDDING_DIM
    attention_heads = cfg.MODEL.ATTENTION_HEADS
    feedforward_dim = cfg.MODEL.FEEDFORWARD_DIM
    transformer_layers = cfg.MODEL.TRANSFORMER_LAYERS
    temperature = cfg.MODEL.TEMPERATURE
    # load data
    data = load_data(cfg, global_rank, world_size)
    num_sites = data['num_sites']
    assert num_sites == 2*data['molecule'].n_active_mos
    # num_spin_up/down records number of unoccupied orbitals instead of occupied ones, for legacy reasons
    num_spin_up = data['molecule'].n_active_mos - (data['molecule'].mo_occ > 0).sum()
    num_spin_down = data['molecule'].n_active_mos - (data['molecule'].mo_occ > 1).sum()
    logging.info('Num of up/down spins {}/{}'.format(num_spin_up, num_spin_down))
    # load model
    model = get_model(model_name, device,
                      print_model_info=True,
                      num_sites=num_sites,
                      made_width=made_width,
                      made_depth=made_depth,
                      embedding_dim = embedding_dim,
                      nhead = attention_heads,
                      dim_feedforward = feedforward_dim,
                      num_layers = transformer_layers,
                      num_spin_up=num_spin_up,
                      num_spin_down=num_spin_down,
                      temperature=temperature,
                      )
    if model_load_path:
        model.load(model_load_path)
    # set up training
    choice = cfg.DATA.HAMILTONIAN_CHOICE
    # Append Hamiltonian parameters to data dictionary
    data.update({'sample_count': cfg.DATA.HAMILTONIAN_BATCH_SIZE, 'total_unique_samples': cfg.DATA.HAMILTONIAN_NUM_UNIQS, 'reset_prob': cfg.DATA.HAMILTONIAN_RESET_PROB, 'flip_bs': cfg.DATA.HAMILTONIAN_FLIP_BATCHES})
    hamiltonian = get_hamiltonian(choice, data)
    hamiltonian.set_device(device)
    optimizer = get_optimizer(opt_name, model, lr, weight_decay)
    scheduler = get_scheduler(sche_name, optimizer, lr, num_epochs)
    if world_size > 1:
        print("The local rank here is {}".format(local_rank))
        model = DistributedDataParallel(model, device_ids=[local_rank])
    # tensorboard
    if global_rank == 0:
        tensorboard = SummaryWriter(log_dir=logger_dir)
        tensorboard.add_text(tag='argument', text_string=str(cfg.__dict__))
        num_model_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if cfg.DATA.FCI:
            fci_result = FCISolver(data['molecule']).simulate()
        else:
            fci_result = 'N/A'
        print('Trainable Model Parameter Total: {}\nHartree--Fock Energy: {:8f}\nCCSD Energy: {:8f}\nFCI Energy: {}'.format(num_model_params, data['molecule'].mf_energy, CCSDSolver(data['molecule']).simulate(), fci_result))
        tensorboard.add_text(tag='test_info', text_string='Qubits: {}, Electrons: {}, Hamiltonian Terms: {}, Hartree-Fock Energy: {:8f}'.format(num_sites, data['molecule'].n_electrons, hamiltonian.num_terms, data['molecule'].mf_energy))
    # train
    best_mean, best_std, best_num_samples = 0.0, 0.0, 1
    time_elapsed = 0.0
    dic = {'mean': [], 'std': [], 'num_uniq': [], 'entropy': [], 'num_samples': []}
    if global_rank == 0:
        progress_bar = trange(num_epochs, desc='Progress Bar', leave=True)
    initial_samples = cfg.DATA.MIN_NUM_SAMPLES
    sample_growth_ratio = (max_num_samples/initial_samples)**(1/(0.90*num_epochs))

    for epoch in range(1, num_epochs + 1):
        initial_samples *= sample_growth_ratio
        num_samples = min(max_num_samples, int(initial_samples))
        # evaluation
        retest = (epoch == 1) or (epoch%retest_interval == 0) or (epoch == num_epochs) or (epoch/num_epochs > 0.90)
        if retest:
            nmlzr, mean, std, num_uniq, entropy = test(model, hamiltonian, bs, num_samples, mini_bs, global_rank, world_size)
        # train
        model.train()
        start_time = time.time()
        reg_const = entropy_scheduler(epoch)
        losses = train_one_batch(model, hamiltonian, optimizer, scheduler, bs, num_samples, mini_bs, global_rank, world_size, nmlzr, epoch, num_epochs, reg_const, entropy)
        end_time = time.time()
        time_elapsed += end_time - start_time
        if global_rank == 0:
            for key in losses:
                tensorboard.add_scalar('train/{}'.format(key), losses[key].real, epoch)
        # log
        message = '[Epoch {}]'.format(epoch)
        for key in losses:
            if key in ['loss']:
                message += ' {}: {:.6f}'.format(key, abs(losses[key]))
        entropy_fig = real(entropy).item()
        if global_rank == 0 and retest:
            dic['mean'].append(mean)
            dic['std'].append(std)
            dic['num_uniq'].append(num_uniq)
            dic['entropy'].append(entropy_fig)
            dic['num_samples'].append(num_samples)
            tensorboard.add_scalar('test/mean', mean, epoch)
            tensorboard.add_scalar('test/std', std, epoch)
            tensorboard.add_scalar('test/num_uniq', num_uniq, epoch)
            tensorboard.add_scalar('test/num_samples', num_samples, epoch)
            tensorboard.add_scalar('test/entropy', entropy_fig, epoch)
        message += ', mean/std/entropy: {:.6f}/{:.6f}/{:.6f}, {} uniqs'.format(mean, std, entropy_fig, num_uniq)
        if (mean + 1.65*std/np.sqrt(num_samples) < best_mean) and retest:
            best_mean = mean
            best_std = std
            best_num_samples = num_samples
            if global_rank == 0:
                if world_size > 1:
                    model.module.save(os.path.join(save_dir, 'last_model.pth'))
                else:
                    model.save(os.path.join(save_dir, 'last_model.pth'))
        if global_rank == 0:
            progress_bar.set_description(message)
            progress_bar.refresh() # to show immediately the update
            progress_bar.update(1)
        if epoch % int(num_epochs/5) == 0:
            logging.info(message)
    if global_rank == 0:
        tensorboard.close()
        print('Best Score Across Training: {}, Confidence Interval: +/-{}\nSample Standard Deviation: {}, Number of Samples: {}\nAverage Number of Uniques: {}'.format(best_mean, 1.96*best_std/np.sqrt(best_num_samples), best_std, best_num_samples, sum(dic['num_uniq'])/len(dic['num_uniq'])))
    return [best_mean, best_std, best_num_samples], time_elapsed, dic
