# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/13_train.ipynb (unless otherwise specified).

__all__ = ['eval_logger', 'load_from_eval_dict', 'save_train_state', 'train']

# Cell
from ..imports import *
from .evaluation import *
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
from ..engine.microscope import Microscope, get_roi_filt_inds, extract_psf_roi, mic_inp_apply_inds
from ..engine.model import UnetDecodeNoBn
from ..engine.point_process import PointProcessUniform
from ..engine.gmm_loss import PointProcessGaussian
import shutil
import wandb
import kornia

from hydra import compose, initialize
from .merfish_eval import *
from .exp_specific import *
# from decode_fish.funcs.visualization vimport get_simulation_statistics

# Cell
def eval_logger(pred_df, target_df, iteration, data_str='Sim. '):

    perf_dict,matches,shift = matching(target_df, pred_df, print_res=False,  match_genes=True)
    if 'Inp' in data_str:
        pred_corr = shift_df(pred_df, shift)
        perf_dict, _, _ = matching(target_df, pred_corr, print_res=False,  match_genes=True)

    wandb.log({data_str +'Metrics/eff_3d': perf_dict['eff_3d']}, step=iteration)
    wandb.log({data_str +'Metrics/jaccard': perf_dict['jaccard']}, step=iteration)
    wandb.log({data_str +'Metrics/rmse_vol': perf_dict['rmse_vol']}, step=iteration)

    wandb.log({data_str +'Metrics/precision': perf_dict['precision']}, step=iteration)
    wandb.log({data_str +'Metrics/recall': perf_dict['recall']}, step=iteration)
    wandb.log({data_str +'Metrics/rmse_x': perf_dict['rmse_x']}, step=iteration)
    wandb.log({data_str +'Metrics/rmse_y': perf_dict['rmse_y']}, step=iteration)
    wandb.log({data_str +'Metrics/rmse_z': perf_dict['rmse_z']}, step=iteration)

    return matches

def load_from_eval_dict(eval_dict):

    if eval_dict.reconstruction.enabled:

        eval_img = load_tiff_image(sorted(glob.glob(eval_dict['image_path']))[eval_dict['img_ind']])
        eval_img = eval_img[eval_dict['crop_sl']]
        eval_df = None
        eval_psf = None
        if eval_dict['txt_path'] is not None:
            txt_path = sorted(glob.glob(eval_dict['txt_path']))[eval_dict['img_ind']]
            eval_df = simfish_to_df(txt_path)
            eval_df = crop_df(eval_df, eval_dict['crop_sl'], px_size_zyx=eval_dict['px_size_zyx'])

        if eval_dict['psf_path'] is not None:
            eval_psf = load_tiff_image(eval_dict['psf_path'])

        return eval_img, eval_df, eval_psf

    if eval_dict.code_stats.enabled:

        return None

def save_train_state(save_dir, model, microscope, optim_dict, train_iter):

        torch.save({'state_dict':model.state_dict(), 'scaling':[model.inp_scale, model.inp_offset]}, save_dir/'model.pkl')
        torch.save(microscope.state_dict(), save_dir/'microscope.pkl')

        save_dict = {k:v.state_dict() for (k,v) in optim_dict.items()}
        save_dict['train_iter'] = train_iter

        torch.save(save_dict, save_dir/'training_state.pkl')

# Cell
def train(cfg,
          model,
          microscope,
          post_proc,
          dl,
          optim_dict,
          eval_dict=None):

    """
    Training loop for autoencoder learning. Alternates between a simulator training step to train the inference network
    and an autoencoder step to train the PSF (and microscope) parameters.

    Args:
        model (torch.nn.Module): DECODE 3D UNet.
        microscope (torch.nn.Module): Microscope class that transforms emitter locations into simulated images.
        post_proc (torch.nn.Module): Post processing class that transforms emitter probilities deterministically into binary outputs.
        dl  (torch.utils.data.dataloader.DataLoader): Dataloader that returns a random sub volume from the real volume, an estiamted emitter density and background.
        optim_dict (dict of torch.optim.Optimizer and torch.optim.lr_scheduler): Dict. with optimizer and scheduler objects for the network and gen. model parameters.
        eval_dict  (dict, optional): Dictionary with evaluation parameters

    """

    save_dir = Path(cfg.output.save_dir)

    if eval_dict is not None:
        eval_vars = load_from_eval_dict(eval_dict)

    model.cuda().train()

    # Save initial psf state
    torch.save(microscope.psf.state_dict(), str(save_dir) + '/psf_init.pkl' )

    # Load codebook
    if 'codebook' in cfg:
        bench_df, code_ref, targets = hydra.utils.instantiate(cfg.codebook)
#         bench_df = exclude_borders(bench_df, border_size_zyx=[0,4000,4000], img_size=[2048*100,2048*100,2048*100])

    # Controls which genmodel parameters are optimized
    for name, p in microscope.named_parameters():
        p.requires_grad = cfg.training.mic.par_grads[name]

    calc_log_p_x = False

    upsamp = torch.nn.UpsamplingBilinear2d(size = [2048,2048])
    colshift_inp = kornia.filters.gaussian_blur2d(microscope.color_shifts[None],  (9,9), (3,3))
    colshift_inp = upsamp(colshift_inp)
    colshift_inp = (colshift_inp * model.inp_scale) + model.inp_offset
    colshift_inp = colshift_inp.detach()

    if cfg.training.schedule is not None:
        sched = cfg.training.schedule
        cfg.training.net.enabled = True
        cfg.training.mic.enabled = False
        switch_iter = sched.pop(0)

    for batch_idx in range(cfg.training.start_iter, cfg.training.num_iters+1):

        if cfg.training.schedule is not None:
            if batch_idx == switch_iter:
                cfg.training.net.enabled = not(cfg.training.net.enabled)
                cfg.training.mic.enabled = not(cfg.training.mic.enabled)
                switch_iter += sched.pop(0)

                colshift_inp = kornia.filters.gaussian_blur2d(microscope.color_shifts[None],  (9,9), (3,3))
                colshift_inp = upsamp(colshift_inp)
                colshift_inp = (colshift_inp * model.inp_scale) + model.inp_offset
                colshift_inp = colshift_inp.detach()

        t0 = time.time()
        x, local_rate, background, zcrop, ycrop, xcrop = next(iter(dl))
        background = background * microscope.get_ch_mult().detach()
        x = x * microscope.get_ch_mult().detach()

        colshift_crop = torch.concat([colshift_inp[:,:,ycrop[i]:ycrop[i]+cfg.sim.random_crop.crop_sz, xcrop[i]:xcrop[i]+cfg.sim.random_crop.crop_sz][:,:,None] for i in range(len(ycrop))], 0)

        if cfg.training.net.enabled:

            optim_dict['optim_net'].zero_grad()

            sim_vars = PointProcessUniform(local_rate[:,0], int_conc=model.int_dist.int_conc.detach(),
                                           int_rate=model.int_dist.int_rate.detach(), int_loc=model.int_dist.int_loc.detach(),
                                           sim_iters=5, channels=cfg.genm.exp_type.n_channels, n_bits=cfg.genm.exp_type.n_bits,
                                           sim_z=cfg.genm.exp_type.pred_z, codebook=torch.tensor(code_ref, dtype=torch.bool), int_option=cfg.training.int_option).sample(from_code_book=True)

            # sim_vars = locs_sl, x_os_sl, y_os_sl, z_os_sl, ints_sl, output_shape, codes
#             print('Sim, ', time.time()-t0); t0 = time.time()
            ch_inp = microscope.get_single_ch_inputs(*sim_vars[:-1], ycrop=ycrop.flatten(), xcrop=xcrop.flatten())
            xsim = microscope(*ch_inp, add_noise=True, add_pos_noise=True)

#             print('Micro, ', time.time()-t0); t0 = time.time()

            if cfg.genm.emitter_noise.rate_fac:

                noise_vars = PointProcessUniform(local_rate[:,0] * cfg.genm.emitter_noise.rate_fac, int_conc=model.int_dist.int_conc.detach() * cfg.genm.emitter_noise.int_fac,
                                               int_rate=model.int_dist.int_rate.detach(), int_loc=model.int_dist.int_loc.detach(),
                                               sim_iters=5, channels=cfg.genm.exp_type.n_channels, n_bits=1,
                                               sim_z=cfg.genm.exp_type.pred_z, codebook=None, int_option=cfg.training.int_option).sample(from_code_book=False)

#                 print('Em. sim ', time.time()-t0); t0 = time.time()
                noise_inp = microscope.get_single_ch_inputs(*noise_vars[:-1], ycrop=ycrop.flatten(), xcrop=xcrop.flatten())
                xsim += microscope(*noise_inp, add_noise=True)
#                 print('Em Micro, ', time.time()-t0); t0 = time.time()

            xsim_noise = microscope.noise(xsim, background, const_theta_sim=cfg.genm.exp_type.const_theta_sim).sample()


#             print('Noise. ', time.time()-t0); t0 = time.time()

#             out_sim = model.tensor_to_dict(model(xsim_noise))
            out_sim = model.tensor_to_dict(model(torch.concat([xsim_noise,colshift_crop], 1)))

#             print('Model forw. ', time.time()-t0); t0 = time.time()

            ppg = PointProcessGaussian(**out_sim)

            count_prob, spatial_prob = ppg.log_prob(*sim_vars[:5], codes=sim_vars[-1],
                                                    n_bits=cfg.genm.exp_type.n_bits, channels=cfg.genm.exp_type.n_channels,
                                                    loss_option=cfg.training.loss_option,
                                                    count_mult=cfg.training.count_mult, cat_logits=cfg.training.cat_logits,
                                                    slice_rec=cfg.genm.exp_type.slice_rec, z_sig_fac=cfg.training.z_sig_fac,
                                                    int_inf=cfg.genm.exp_type.int_inf)

            gmm_loss = -(spatial_prob + cfg.training.net.cnt_loss_scale*count_prob).mean()

            background_loss = F.mse_loss(out_sim['background'], background) * cfg.training.net.bl_loss_scale

            loss = gmm_loss + background_loss

#             print('Loss calc. ', time.time()-t0); t0 = time.time()

            # Update network parameters
            loss.backward()

            if cfg.training.net.grad_clip: torch.nn.utils.clip_grad_norm_(model.network.parameters(), max_norm=cfg.training.net.grad_clip, norm_type=2)

            optim_dict['optim_net'].step()
            optim_dict['sched_net'].step()
            # Step all the other optimizers too so the lr's dont got out of sync
#             optim_dict['sched_mic'].step()
#             optim_dict['sched_int'].step()

#             print('Grad upd. ', time.time()-t0); t0 = time.time()

        if batch_idx > min(cfg.training.start_mic,cfg.training.start_int):

#             out_inp = model.tensor_to_dict(model(x))
            out_inp = model.tensor_to_dict(model(torch.concat([x, colshift_crop], 1)))
            proc_out_inp = post_proc.get_micro_inp(out_inp)

            if cfg.training.mic.enabled and batch_idx > cfg.training.start_mic and len(proc_out_inp[1]) > 0 and len(proc_out_inp[1]) < 300:

#                 print('Pre filt ', len(proc_out_inp[1]))
                ch_out_inp = microscope.get_single_ch_inputs(*proc_out_inp, ycrop=ycrop.flatten(), xcrop=xcrop.flatten())
                optim_dict['optim_mic'].zero_grad()
                calc_log_p_x = False

                # Get ch_fac loss
                ch_inds = ch_out_inp[0][1]
                int_vals = ch_out_inp[-2]

                int_means = torch.ones(cfg.genm.exp_type.n_channels).cuda() * (model.int_dist.int_loc.detach() + model.int_dist.int_conc.detach())
                for i in range(cfg.genm.exp_type.n_channels):
                    if i in ch_inds:
                        int_means[i] = int_vals[ch_inds == i].mean()

                int_means = (model.int_dist.int_loc.detach() + model.int_dist.int_conc.detach()) / int_means
                ch_fac_loss = torch.sqrt(torch.mean((microscope.channel_facs - microscope.channel_facs.detach() * int_means)**2))

                # Get autoencoder loss
                if cfg.training.mic.roi_rec:
                    filt_inds = get_roi_filt_inds(*ch_out_inp[0], microscope.psf.psf_volume.shape, x.shape, slice_rec=cfg.genm.exp_type.slice_rec, min_dist=10)
                    ch_out_inp = mic_inp_apply_inds(*ch_out_inp, filt_inds)
                    if len(ch_out_inp[1]):
                        psf_recs = microscope(*ch_out_inp, ret_psfs=True, add_noise=False)
#                         print('N rec inds ', len(psf_recs))

                        rois = extract_psf_roi(ch_out_inp[0], x, torch.tensor(psf_recs.shape))
                        bgs = extract_psf_roi(ch_out_inp[0], out_inp['background'], torch.tensor(psf_recs.shape))

                        log_p_x_given_z = -microscope.noise(psf_recs, bgs, const_theta_sim=False).log_prob(rois.clamp_min_(1.)).mean()
                        calc_log_p_x = True

                else:
                    ae_img = microscope(*ch_out_inp, add_noise=False)
                    log_p_x_given_z = -microscope.noise(ae_img, out_inp['background'], const_theta_sim=False).log_prob(x.clamp_min_(1.)).mean()
                    calc_log_p_x = True

                if calc_log_p_x:

#                     print(ch_fac_loss)
                    log_p_x_given_z += ch_fac_loss

                    if cfg.training.mic.norm_reg:
                        log_p_x_given_z += cfg.training.mic.norm_reg * (microscope.psf.com_loss())

                    if cfg.training.mic.l1_reg:
                        log_p_x_given_z += cfg.training.mic.l1_reg * (microscope.psf.l1_diff_norm(microscope.psf_init_vol))

                    log_p_x_given_z.backward()
                    if cfg.training.mic.grad_clip:
                        torch.nn.utils.clip_grad_norm_(microscope.parameters(), max_norm=cfg.training.mic.grad_clip, norm_type=2)

                    optim_dict['optim_mic'].step()

                optim_dict['sched_mic'].step()

#                 print('PSF ', time.time()-t0); t0 = time.time()

            if  cfg.training.int.enabled and batch_idx > cfg.training.start_int and len(proc_out_inp[4]):

                optim_dict['optim_int'].zero_grad()
                ints = proc_out_inp[4]
                ints = torch.clamp_min(ints, model.int_dist.int_loc.detach() + 0.01)

                gamma_int = D.Gamma(model.int_dist.int_conc, model.int_dist.int_rate)
                loc_trafo = [D.AffineTransform(loc=model.int_dist.int_loc.detach(), scale=1)]
                int_loss = -D.TransformedDistribution(gamma_int, loc_trafo).log_prob(ints.detach()).mean()

                if cfg.training.int.grad_clip:
                    torch.nn.utils.clip_grad_norm_(model.int_dist.parameters(), max_norm=cfg.training.mic.grad_clip, norm_type=2)

                int_loss.backward()
                optim_dict['optim_int'].step()

#                 print('INT ', time.time()-t0); t0 = time.time()

        # Logging
        if batch_idx % 10 == 0:

            if cfg.training.net.enabled:

                wandb.log({'SL Losses/xyz_loss': spatial_prob.mean().detach().cpu().item()}, step=batch_idx)
    #             wandb.log({'SL Losses/ints_loss': int_prob.mean().detach().cpu().item()}, step=batch_idx)
                wandb.log({'SL Losses/count_loss': (-count_prob.mean()).detach().cpu()}, step=batch_idx)
    #             wandb.log({'SL Losses/bg_loss': background_loss.detach().cpu()}, step=batch_idx)

#                 wandb.log({'AE Losses/int_mu': model.int_dist.int_conc.item()/model.int_dist.int_rate.item() + model.int_dist.int_loc.item()}, step=batch_idx)
#                 wandb.log({'AE Losses/int_rate': model.int_dist.int_rate.item()}, step=batch_idx)
#                 wandb.log({'AE Losses/int_loc': model.int_dist.int_loc.item()}, step=batch_idx)
                wandb.log({'AE Losses/theta': microscope.noise.theta_par.cpu().detach().mean().item()*microscope.noise.theta_scale}, step=batch_idx)

            if batch_idx > cfg.training.start_mic:
                if cfg.training.mic.enabled and calc_log_p_x:
                    wandb.log({'AE Losses/p_x_given_z': log_p_x_given_z.detach().cpu()}, step=batch_idx)
                    wandb.log({'AE Losses/RMSE(rec)': torch.sqrt(((rois-(psf_recs+bgs))**2).mean()).detach().cpu()}, step=batch_idx)
#                     wandb.log({'AE Losses/RMSE(rec)': torch.sqrt(((x[:,:1]-(ae_img[:,:1]+out_inp['background'][:,:1]))**2).mean()).detach().cpu()}, step=batch_idx)
                    wandb.log({'AE Losses/sum(psf)': F.relu(microscope.psf.psf_volume/microscope.psf.psf_volume.max())[0].sum().detach().cpu()}, step=batch_idx)
#                     wandb.log({'AE Losses/theta': microscope.theta.item()}, step=batch_idx)

#         if batch_idx > 0 and batch_idx % 1500 == 0:
#             torch.save({'state_dict':model.state_dict(), 'scaling':[model.inp_scale, model.inp_offset]}, save_dir/f'model_{batch_idx}.pkl')

        if batch_idx % cfg.output.log_interval == 0:
            print(batch_idx)
            if cfg.training.net.enabled:
                with torch.no_grad():

                    pred_df = post_proc.get_df(out_sim)
                    px_size = cfg.evaluation.px_size_zyx
                    target_df = sample_to_df(*sim_vars[:5], sim_vars[-1], px_size_zyx=px_size)
    #                 print(len(pred_df), len(target_df))
                    matches = eval_logger(pred_df, target_df, batch_idx, data_str='Sim. ')

                    wandb.log({'Sim. Metrics/prob_fac': torch.sigmoid(out_sim['logits']).sum().item()/(len(target_df)+0.1)}, step=batch_idx)
                    wandb.log({'Sim. Metrics/n_em_fac': len(pred_df)/(len(target_df)+0.1)}, step=batch_idx)

                    if cfg.output.log_figs:

                        sl_fig = sl_plot(x, xsim_noise, nm_to_px(pred_df, px_size), nm_to_px(target_df, px_size), background, out_sim)
                        plt.show()
                        wandb.log({'SL summary': sl_fig}, step=batch_idx)

                    if cfg.evaluation.reconstruction.enabled:

                        eval_img, eval_df, eval_psf = eval_vars

                        res_eval = model.tensor_to_dict(model(eval_img[None].cuda()))
                        ae_img = microscope(*post_proc.get_micro_inp(res_eval))
                        pred_eval_df = post_proc.get_df(res_eval)
                        wandb.log({'AE Losses/N preds(eval)': len(pred_eval_df)}, step=batch_idx)

                        if eval_df is not None:
                            eval_logger(pred_eval_df, eval_df, batch_idx, data_str='Inp. ')

                        if eval_psf is not None:
                            wandb.log({'AE Losses/Corr(psf)': np.corrcoef(cpu(eval_psf).reshape(-1), cpu(microscope.psf.psf_volume).reshape(-1))[0,1]}, step=batch_idx)
                            wandb.log({'AE Losses/RMSE(psf)': np.sqrt(np.mean((cpu(eval_psf/eval_psf.max())-cpu(microscope.psf.psf_volume/microscope.psf.psf_volume.max()))**2))}, step=batch_idx)

                        if cfg.output.log_figs:
                            eval_fig = gt_plot(eval_img, nm_to_px(pred_eval_df, px_size), nm_to_px(eval_df, px_size), px_size, ae_img[0]+res_eval['background'][0], microscope.psf)
                            plt.show()
                            wandb.log({'GT': eval_fig}, step=batch_idx)

                    if cfg.evaluation.code_stats.enabled:

                        hydra.utils.call(cfg.evaluation.code_stats.eval_func, model=model, post_proc=post_proc, targets=targets, path=cfg.evaluation.code_stats.path, wandb=wandb, batch_idx=batch_idx, chrom_map=colshift_inp, scale = microscope.get_ch_mult().detach())

            # storing
            save_train_state(save_dir, model, microscope, optim_dict, batch_idx)

    wandb.finish()