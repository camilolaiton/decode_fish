# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/07_file_io.ipynb (unless otherwise specified).

__all__ = ['load_model_state', 'get_df_from_hdf5', 'add_df_to_hdf5', 'swap_psf_vol', 'get_gaussian_psf', 'get_vol_psf',
           'load_psf', 'load_psf_noise_micro', 'load_post_proc', 'get_dataloader', 'load_all']

# Cell
from ..imports import *
from .utils import *
from tifffile import imread
from ..engine.microscope import Microscope
from ..engine.psf import crop_psf
from ..engine.psf import LinearInterpolatedPSF
from .emitter_io import *
from .dataset import *
from torch.utils.data import DataLoader
from collections.abc import MutableSequence

# Cell
def load_model_state(model, path):
    """
    Loads the network parameters, the intensity parameters and the scaling into model given a path.
    """
    model_dict = torch.load(path)
    model.load_state_dict(model_dict['state_dict'])
    model.inp_scale = model_dict['scaling'][0]
    model.inp_offset = model_dict['scaling'][1]
    return model

# Cell
def get_df_from_hdf5(group):

    df = DF()
    for k in group.keys():
        df[k] = group[k][()]
    return df

def add_df_to_hdf5(parent, name, df):

    g = parent.create_group(name)
    for k in df.keys():
        g.create_dataset(k, data=df[k].values)

# Cell
def swap_psf_vol(psf, vol):
    state_dict = psf.state_dict()
    if vol.ndim == 3:
        for i in range(len(state_dict['psf_volume'])):
            state_dict['psf_volume'][i] = torch.cuda.FloatTensor(torch.Tensor(vol).cuda())
    else:
        state_dict['psf_volume'] = torch.cuda.FloatTensor(torch.Tensor(vol).cuda())
    psf.load_state_dict(state_dict)
    return psf

def get_gaussian_psf(size_zyx, radii, pred_z, n_cols=1, mode='bilinear'):

    if not pred_z:
        size_zyx[0] = 1

    if not isinstance(radii, MutableSequence):
        radii = 3*[radii]

    psf = LinearInterpolatedPSF(size_zyx, device='cuda', n_cols=n_cols, mode=mode)
    gauss_vol = gaussian_sphere(size_zyx, radii, [size_zyx[0]//2,size_zyx[1]//2,size_zyx[2]//2])

    psf = swap_psf_vol(psf, gauss_vol)
    return psf

def get_vol_psf(filename, device='cuda', psf_extent_zyx=None, n_cols=1, mode='bilinear'):

    if 'tif' in filename:
        psf_vol = load_tiff_image(filename)
        psf_vol *= psf_extent_zyx
#         psf_vol = torch.tensor(np.array(psf_vol).take(indices=range(0, psf_extent_zyx), axis=-3))
        psf = LinearInterpolatedPSF(psf_vol.shape[-3:], device=device, n_cols=n_cols, mode=mode)
        if psf_vol.ndim == 3: psf_vol = psf_vol[None]
        if psf_vol.shape[0] == 1: psf_vol = psf_vol.repeat_interleave(n_cols,0)
        psf = swap_psf_vol(psf, psf_vol)

    else:
        psf_state = torch.load(filename)
        psf = LinearInterpolatedPSF(psf_state['psf_volume'].shape[-3:], device=device, n_cols=n_cols, mode=mode)
        psf.load_state_dict(psf_state)

#         if psf_extent_zyx:
#             psf = crop_psf(psf,psf_extent_zyx)

    return psf

def load_psf(cfg):

    if cfg.data_path.psf_path:
        psf = get_vol_psf(cfg.data_path.psf_path,cfg.genm.PSF.device, cfg.genm.PSF.psf_extent_zyx, cfg.genm.PSF.n_cols, cfg.genm.PSF.mode)
    else:
        psf = get_gaussian_psf(cfg.genm.PSF.psf_extent_zyx, cfg.genm.PSF.gauss_radii, cfg.genm.exp_type.pred_z, cfg.genm.PSF.n_cols, cfg.genm.PSF.mode)

    return psf

def load_psf_noise_micro(cfg):

    psf = load_psf(cfg)
    noise = hydra.utils.instantiate(cfg.genm.noise)
    micro = hydra.utils.instantiate(cfg.genm.microscope, psf=psf, noise=noise).cuda()

    return psf, noise, micro

def load_post_proc(cfg):
    if cfg.other.pp == 'si':
        return hydra.utils.instantiate(cfg.post_proc_si)
    if cfg.other.pp == 'isi':
        return hydra.utils.instantiate(cfg.post_proc_isi)

def get_dataloader(cfg):

    from_records = False if cfg.data_path.image_path is None else True
    sl = eval(cfg.data_path.image_proc.crop_sl,{'__builtins__': None},{'s_': np.s_})

    if from_records:
        if 'override' in cfg.data_path.image_proc:
            imgs_5d = torch.cat([hydra.utils.instantiate(cfg.data_path.image_proc.override, image_path=f) for f in sorted(glob.glob(cfg.data_path.image_path))], 0)
        else:
            imgs_5d   = torch.cat([load_tiff_image(f)[None] for f in sorted(glob.glob(cfg.data_path.image_path))], 0)

        if imgs_5d.ndim > 5:
            imgs_5d = imgs_5d.view(-1, *(imgs_5d.size()[2:]))

        imgs_5d       = torch.cat([img.permute(*cfg.data_path.image_proc.swap_dim)[sl][None] for img in imgs_5d], 0)
        roi_masks     = [get_roi_mask(img, tuple(cfg.sim.roi_mask.pool_size), percentile= cfg.sim.roi_mask.percentile) for img in imgs_5d]
    else:
        imgs_5d       = torch.cat([torch.empty(list(cfg.data_path.image_sim.image_shape))], 0)
        roi_masks     = None
        gen_bg        = [hydra.utils.instantiate(cfg.sim.bg_estimation.uniform)]
        dataset_tfms  = []


    min_shape = tuple(np.stack([v.shape for v in imgs_5d]).min(0)[-3:])
    crop_zyx = (cfg.sim.random_crop.crop_sz, cfg.sim.random_crop.crop_sz,cfg.sim.random_crop.crop_sz)
    if crop_zyx > min_shape:
        crop_zyx = tuple(np.stack([min_shape, crop_zyx]).min(0))
        print('Crop size larger than volume in at least one dimension. Crop size changed to', crop_zyx)

    if from_records:
        if cfg.sim.bg_estimation.type == 'smoothing':
            gen_bg        = [hydra.utils.instantiate(cfg.sim.bg_estimation.smoothing, z_size=crop_zyx[0])]
        elif cfg.sim.bg_estimation.type == 'uniform':
            gen_bg        = [hydra.utils.instantiate(cfg.sim.bg_estimation.uniform)]

        rand_crop = RandomCrop3D(crop_zyx, roi_masks)
        dataset_tfms  = [rand_crop]

    if cfg.sim.bg_estimation.fractal.scale:
        gen_bg.append(hydra.utils.instantiate(cfg.sim.bg_estimation.fractal))

    probmap_generator = UniformValue(cfg.genm.prob_generator.low, cfg.genm.prob_generator.high)
    rate_tfms = [probmap_generator]

    if cfg.genm.foci.n_foci_avg > 0:
        rate_tfms.append(hydra.utils.instantiate(cfg.genm.foci))

    ds = DecodeDataset(volumes = imgs_5d,
                       dataset_tfms =  dataset_tfms,
                       rate_tfms = rate_tfms,
                       bg_tfms = gen_bg,
                       device='cuda:0',
                       from_records=from_records,
                       num_iter=(cfg.training.num_iters) * cfg.training.bs)

    decode_dl = DataLoader(ds, batch_size=cfg.training.bs, num_workers=0)

    return imgs_5d, decode_dl

def load_all(cfg, load_ds=True):

    path = Path(cfg.output.save_dir)
    model = hydra.utils.instantiate(cfg.network)
    model = load_model_state(model, path/'model.pkl')
    post_proc = hydra.utils.instantiate(cfg.post_proc_isi, samp_threshold=0.5)
    _, noise, micro = load_psf_noise_micro(cfg)
    micro.load_state_dict(torch.load(path/'microscope.pkl'), strict=False)
    if load_ds:
        imgs_5d, decode_dl = get_dataloader(cfg)
    else:
        imgs_5d, decode_dl = None, None

    return model, post_proc, micro, imgs_5d, decode_dl