# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/17_eval_routines.ipynb (unless otherwise specified).

__all__ = ['sim_data', 'get_prediction']

# Cell
from ..imports import *
from .file_io import *
from .emitter_io import *
from .utils import *
from .dataset import *
from .plotting import *
from ..engine.microscope import *
import shutil
from .matching import *
from .predict import window_predict
from .matching import matching
from .merfish_eval import *
from .exp_specific import *
from ..engine.point_process import *
from .output_trafo import sample_to_df

from omegaconf import open_dict
from hydra import compose, initialize

# Cell
def sim_data(decode_dl, micro, point_process, batches, n_codes, rate_fac=1., pos_noise_xy=0., pos_noise_z=0., randomize_range=None, n_bits=4):

    gt_dfs = []
    xsim_col = []
    cols_col = []

    for _ in range(batches):
        with torch.no_grad():
            ret_dict = next(iter(decode_dl))
            x, local_rate, background = ret_dict['x'], ret_dict['local_rate'], ret_dict['background'],
            if micro.col_shifts_enabled:
                zcrop, ycrop, xcrop = ret_dict['crop_z'], ret_dict['crop_y'], ret_dict['crop_x']
                zcrop, ycrop, xcrop = zcrop.flatten(), ycrop.flatten(), xcrop.flatten()
            else:
                zcrop, ycrop, xcrop, colshift_crop = None, None, None, None
            background = background * micro.get_ch_mult()
            local_rate *= rate_fac

            sim_vars = point_process.sample(local_rate[:,0])
            ch_inp = list(micro.get_single_ch_inputs(*sim_vars[:-1], ycrop=ycrop, xcrop=xcrop))
            if pos_noise_xy or pos_noise_z:
                cond = sim_vars[-1] < n_codes
                cb_cool = torch.repeat_interleave(cond, cond * (n_bits - 1) + 1)
                ch_inp[1][cb_cool], ch_inp[2][cb_cool], ch_inp[3][cb_cool] = add_pos_noise([ch_inp[1][cb_cool], ch_inp[2][cb_cool], ch_inp[3][cb_cool]],
                                                                                           [pos_noise_xy, pos_noise_xy, pos_noise_z], n_bits)
            xsim = micro(*ch_inp, add_noise=True)

            x = micro.noise(xsim, background, randomize_range=randomize_range).sample()

            if micro.col_shifts_enabled:
                colshift_crop = get_color_shift_inp(micro.color_shifts, micro.col_shifts_yx, ycrop, xcrop, decode_dl.dataset.dataset_tfms[0].crop_sz[-1])
                net_inp = torch.concat([x,colshift_crop], 1)
                cols_col.append(colshift_crop)

            xsim_col.append(x)

            gt_vars = sim_vars[:-2]
            gt_df = sample_to_df(*gt_vars, sim_vars[-1], px_size_zyx=[1.,1.,1.])
            gt_dfs.append(gt_df)

    cols_col = torch.cat(cols_col) if micro.col_shifts_enabled else None

    return torch.cat(xsim_col), cols_col, cat_emitter_dfs(gt_dfs, decode_dl.batch_size)

# Cell
def get_prediction(model, vol, post_proc, col_offset_map=None, micro=None, cuda=True, return_rec=False, filt_rad=10):

    with torch.no_grad():

        vol = vol[(None,)*(5-vol.ndim)]
        model.eval().cuda() if cuda else model.eval().cpu()
        net_inp = torch.concat([vol,col_offset_map], 1) if col_offset_map is not None else vol
        res_dict = model(net_inp.cuda()) if cuda else model(net_inp)
        res_dict = model.tensor_to_dict(res_dict)
        pred_df = post_proc.get_df(res_dict)

        if return_rec:
            assert micro is not None, "Need access to microscope for reconstruction"
            micro_inp = post_proc.get_micro_inp(res_dict)
            ch_inp = micro.get_single_ch_inputs(*micro_inp)
            ae_img_3d = micro(*ch_inp)

            filt_inds = get_roi_filt_inds(*ch_inp[0], micro.psf.psf_volume.shape, vol.shape, slice_rec=micro.slice_rec, min_dist=10)
            ch_inp = mic_inp_apply_inds(*ch_inp, filt_inds)
            if len(ch_inp[1]):
                psf_recs = micro(*ch_inp, ret_psfs=True, add_noise=False)

                rois = extract_psf_roi(ch_inp[0], vol, torch.tensor(psf_recs.shape))
                psf_bgs = extract_psf_roi(ch_inp[0], res_dict['background'], torch.tensor(psf_recs.shape))
            else:
                psf_recs = rois = psf_bgs = None

            return pred_df, ae_img_3d + res_dict['background'], res_dict, psf_recs, psf_bgs, rois, ch_inp

        return pred_df