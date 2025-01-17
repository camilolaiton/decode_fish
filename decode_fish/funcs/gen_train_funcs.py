# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/26_gen_train.ipynb (unless otherwise specified).

__all__ = ['gen_train_dataset']

# Cell
from ..imports import *
from .matching import *
from .file_io import *
from .emitter_io import *
from .utils import *
from .dataset import *
from .output_trafo import *
from .plotting import *
from .predict import *
import torch.nn.functional as F
from torch import distributions as D
from torch.utils.data import DataLoader
import torch_optimizer
from ..engine.microscope import Microscope, get_roi_filt_inds, extract_psf_roi, mic_inp_apply_inds, add_pos_noise, concat_micro_inp
from ..engine.model import UnetDecodeNoBn_2S
from ..engine.point_process import PointProcessUniform, get_phased_ints
from ..engine.gmm_loss import PointProcessGaussian
import shutil
import wandb
import kornia

from hydra import compose, initialize
from .merfish_eval import *
from .exp_specific import *
# from decode_fish.funcs.visualization vimport get_simulation_statistics

# Cell
def gen_train_dataset(cfg,
          microscope,
          rois,
          bgs,
          proc_out_inp,
          filt_inds,
          optim_dict):

    save_dir = Path(cfg.output.save_dir)

    # Save initial psf state
    torch.save(microscope.psf.state_dict(), str(save_dir) + '/psf_init.pkl' )

    # Controls which genmodel parameters are optimized
    for name, p in microscope.named_parameters(recurse=False):
        p.requires_grad = cfg.training.mic.par_grads[name]
    for name, p in microscope.psf.named_parameters():
        p.requires_grad = False
    calc_log_p_x = False

    for batch_idx in range(cfg.training.start_iter, cfg.training.num_iters+1):

        optim_dict['optim_mic'].zero_grad()
        calc_log_p_x = False

        ch_out_inp = microscope.get_single_ch_inputs(*proc_out_inp, ycrop=None, xcrop=None)
        ch_out_inp = mic_inp_apply_inds(*ch_out_inp, filt_inds)

        psf_recs = microscope(*ch_out_inp, ret_psfs=True, add_noise=False)

        mean_diff = 0.
        if cfg.training.mic.mean_diff:
            mean_diff = rois.mean([1,2,3,4], keepdim=True) - (psf_recs.detach()+bgs).mean([1,2,3,4], keepdim=True)

        if cfg.training.mic.edge_diff:
            bg_edges = torch.cat([bgs[:,0,0,:2,:].flatten(1,2), bgs[:,0,0,-2:,:].flatten(1,2), bgs[:,0,0,:,:2].flatten(1,2), bgs[:,0,0,:,-2:].flatten(1,2)], 1)
            rois_edges = torch.cat([rois[:,0,0,:2,:].flatten(1,2), rois[:,0,0,-2:,:].flatten(1,2), rois[:,0,0,:,:2].flatten(1,2), rois[:,0,0,:,-2:].flatten(1,2)], 1)
            mean_diff = (rois_edges.mean(-1) - bg_edges.mean(-1))[:,None,None,None,None]

        log_p_x_given_z = -microscope.noise(psf_recs, bgs, const_theta_sim=False, ch_inds=ch_out_inp[0][1]).log_prob((rois-mean_diff).clamp_min_(1.))

        log_p_x_given_z = log_p_x_given_z.mean()
        calc_log_p_x = True

#         log_p_x_given_z += ch_fac_loss

        if cfg.training.mic.norm_reg:
            log_p_x_given_z += cfg.training.mic.norm_reg * (microscope.psf.com_loss())

        if cfg.training.mic.l1_reg:
            log_p_x_given_z += cfg.training.mic.l1_reg * (microscope.psf.l1_diff_norm(microscope.psf_init_vol))

        log_p_x_given_z.backward()
        if cfg.training.mic.grad_clip:
            torch.nn.utils.clip_grad_norm_(microscope.parameters(), max_norm=cfg.training.mic.grad_clip, norm_type=2)

        optim_dict['optim_mic'].step()
        optim_dict['sched_mic'].step()

        # Logging
        if batch_idx % cfg.output.log_interval == 0:

#             print(batch_idx, log_p_x_given_z)
            wandb.log({'AE Losses/p_x_given_z': log_p_x_given_z.detach().cpu()}, step=batch_idx)
            wandb.log({'AE Losses/RMSE(rec)': torch.sqrt((((rois-mean_diff)-(psf_recs+bgs))**2).mean()).detach().cpu()}, step=batch_idx)
            wandb.log({'AE Losses/sum(psf)': F.relu(microscope.psf.psf_volume)[0].sum().detach().cpu()}, step=batch_idx)

            torch.save(microscope.state_dict(), save_dir/'microscope.pkl')

    wandb.finish()