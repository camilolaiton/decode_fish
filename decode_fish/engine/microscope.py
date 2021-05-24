# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/02_microscope.ipynb (unless otherwise specified).

__all__ = ['Microscope', 'place_psf']

# Cell
from ..imports import *
import torch.nn as nn
from torch.jit import script
from typing import Union, List
import torch.nn.functional as F
from ..funcs.plotting import *

# Cell
class Microscope(nn.Module):
    """
    The Mircoscope module takes  5 vectors 'locations', 'x_os', 'y_os', 'z_os',
    'ints_3d' turns them into 3D data through the following steps:
    1) Apply continuous shifts to the PSF according to x_os, y_os, z_os
    2) Clamping the PSF (retaining only positive values)
    3) Normalize the PSF dividing it by it's max value
    6) Place point spread function according to locations  to
    generate 'x_sim'
    7) Multiplies x_sim with scale

    Args:
        psf (torch.nn.Module): Parametric PSF
        noise (torch.nn.Module): Camera noise model
        scale(float): Constant for scaling

    Shape:
        -Input: locations: Tuple(torch.Tensor)
                x_os_val: (N_emitters,)
                y_os_val: (N_emitters,)
                z_os_val: (N_emitters,)
                ints_val: (N_emitters,)
                output_shape: Shape Tuple(BS, C, H, W, D)

        -Output: xsim: (BS, C, H, W, D)
    """


    def __init__(self, psf: torch.nn.Module=None, noise: Union[torch.nn.Module, None]=None, scale: float = 10000.):

        super().__init__()
        self.psf = psf
        self.scale = scale
        self.noise = noise

        self.theta = self.noise.theta

    def forward(self, locations, x_os_val, y_os_val, z_os_val, i_val, output_shape, bg=None, eval_=None):

        if len(locations[0]):

            # Apply continuous shift
            psf = self.psf(x_os_val, y_os_val, z_os_val)
            torch.clamp_min_(psf,0)
            # normalize psf
            psf_max = psf.amax(dim=[2, 3, 4], keepdim=True)
            psf = psf.div(psf_max)
            # applying intenseties
            tot_intensity = torch.clamp_min(i_val, 0)
            psf = psf * tot_intensity[:,None,None,None,None]
            # place psf according to locations
            xsim = place_psf(locations, psf, output_shape)
            # scale (not learnable)
            xsim = self.scale * xsim
            if eval_:
                return xsim, psf
            return xsim

        else:

            return torch.zeros(output_shape).cuda()

# Cell
def place_psf(locations, psf_volume, output_shape):
    """
    Places point spread functions (psf_volume) in to corresponding locations.

    Args:
        locations: tuple with the 5D voxel coordinates
        psf_volume: torch.Tensor
        output_shape: Shape Tuple(BS, C, H, W, D)

    Returns:
        placed_psf: torch.Tensor with shape (BS, C, H, W, D)
    """
#     filter_size = psf_volume.shape[-3:]
#     filter_sizes = torch.cat([torch.tensor((sz // 2, sz // 2 + 1)) for sz in filter_size]).reshape(3, 2).cuda()
#     padding_sz = torch.tensor(max(filter_size) // 2 + 2).cuda()
#     batch, ch, z, y, x = locations
#     placed_psf = _place_psf(psf_volume, padding_sz, filter_sizes, batch, ch, z, y, x, torch.tensor(output_shape))
#     assert placed_psf.shape == output_shape
#     return placed_psf

    batch, ch, z, y, x = locations
    placed_psf = _place_psf(psf_volume, batch, ch, z, y, x, torch.tensor(output_shape))
    assert placed_psf.shape == output_shape
    return placed_psf

# Cell
@script
def _place_psf(psf_vols, b, ch, z, y, x, output_shape):
    '''jit function for placing PSFs
    1) This function will add padding to coordinates (z, y, x) (we need padding in order to place psf on the edges)
    afterwards we will just crop out to original shape
    2) Create empty tensor with paddings loc3d_like
    3) place each individual PSFs in to the corresponding cordinates in loc3d_like
    4) unpad to original output shape

    Args:
        psf_vols:   torch.Tensor
        b:        torch.Tensor
        c:        torch.Tensor
        h:        torch.Tensor
        w:        torch.Tensor
        d:        torch.Tensor
        szs:      torch.Tensor

    Shape:
        psf_vols: (Num_E, C, PSF_SZ_X, PSF_SZ_Y, PSF_SZ_Z)
        b:  (Num_E,)
        c:  (Num_E,)
        h:  (Num_E,)
        w:  (Num_E,)
        d:  (Num_E,)
        output_shape:  (BS, Frames, H, W, D)

    -Output: placed_psf: (BS, Frames, H, W, D)

    '''

    psf_b, psf_c, psf_h, psf_w, psf_d = psf_vols.shape
    pad_zyx = [psf_h//2, psf_w//2, psf_d//2]
    #add padding to z, y, x

    z = z + pad_zyx[0]
    y = y + pad_zyx[1]
    x = x + pad_zyx[2]

    #create padded tensor (bs, frame, c, h, w) We will need pad_size * 2 since we are padding from both size
    loc3d_like = torch.zeros(output_shape[0],
                             output_shape[1],
                             output_shape[2] + 2*(pad_zyx[0]),
                             output_shape[3] + 2*(pad_zyx[1]),
                             output_shape[4] + 2*(pad_zyx[2])).to(x.device)

    psf_vols = psf_vols.reshape(-1, psf_h, psf_w, psf_d)

    for idx in range(x.shape[0]):
        loc3d_like[b[idx], ch[idx],
        z[idx]-pad_zyx[0] : z[idx]+pad_zyx[0] + 1,
        y[idx]-pad_zyx[1] : y[idx]+pad_zyx[1] + 1,
        x[idx]-pad_zyx[2] : x[idx]+pad_zyx[2] + 1] += psf_vols[idx]

    b_sz, ch_sz, h_sz, w_sz, d_sz = loc3d_like.shape

    # unpad to original size
    placed_psf = loc3d_like[:, :, pad_zyx[0]: h_sz - pad_zyx[0],
                                  pad_zyx[1]: w_sz - pad_zyx[1],
                                  pad_zyx[2]: d_sz - pad_zyx[2]]
    return placed_psf