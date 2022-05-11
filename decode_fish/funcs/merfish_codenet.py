# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/22_MERFISH_codenet.ipynb (unless otherwise specified).

__all__ = ['input_from_df', 'extract_rmses', 'code_net', 'input_from_df', 'net']

# Cell
from ..imports import *
from .file_io import *
from .emitter_io import *
from .utils import *
from .dataset import *
from .plotting import *
from ..engine.noise import estimate_noise_scale
import shutil
from .visualization import *
import torch.nn as nn
import torch.nn.functional as F
from .predict import *

from omegaconf import open_dict
from hydra import compose, initialize
from .merfish_eval import *

# Cell

# def input_from_df(df, from_matches=True):

#     df_str = '_pred' if from_matches else  ''
#     df = get_code_from_ints(df, codebook, targets, int_str=df_str)
#     matched_codes = codebook[df['code_inds'].values]

#     input_keys = ['prob'+df_str,'x_sig'+df_str,'y_sig'+df_str, 'code_err'] + [f'int_{i}{df_str}' for i in range(16)] + [f'int_sig_{i}{df_str}' for i in range(16)]
#     inp_arr = df[input_keys].values
#     return np.concatenate([df[input_keys].values, matched_codes], 1)

# def input_from_df(df, codebook, targets, from_matches=True):

#     df_str = '_pred' if from_matches else  ''
#     df = get_code_from_ints(df, codebook, targets, int_str=df_str)
#     matched_codes = codebook[df['code_inds'].values]

#     input_keys = ['prob'+df_str,'x_sig'+df_str,'y_sig'+df_str, 'code_err'] #+ ['rec_rmses'] + [f'int_sig_{i}{df_str}' for i in range(16)]
#     inp_arr = df[input_keys].values
#     int_sum = df[[f'int_{i}{df_str}' for i in range(16)]].values.sum(-1)[:,None]
#     ints_sum = df[[f'int_sig_{i}{df_str}' for i in range(16)]].values.sum(-1)[:,None]

#     return np.concatenate([inp_arr, int_sum, ints_sum], 1)

def input_from_df(df):

    input_keys = ['prob','x_sig','y_sig','z_sig'] + [f'int_sig_{i}' for i in range(4)]  + [f'int_{i}' for i in range(4)]
    inp_arr = df[input_keys].values

    return inp_arr
#     int_sum = df[[f'int_{i}' for i in range(16)]].values.sum(-1)[:,None]
#     ints_sum = df[[f'int_sig_{i}' for i in range(16)]].values.sum(-1)[:,None]

#     return np.concatenate([inp_arr, int_sum, ints_sum], 1)



# def target_from_matches(matches_df, codebook, targets):

#     matches_df = get_code_from_ints(matches_df, codebook, targets, int_str='_pred')
#     matched_codes = codebook[matches_df['code_inds'].values]

# #     int_arr = matches_df[[f'int_{i}_tar' for i in range(16)]]
# #     tar_code = np.where(int_arr>0,1,0)

#     int_arr = matches_df[[f'int_{i}_tar' for i in range(16)]].values
#     s_arr = np.sort(int_arr)
#     lim = s_arr[:,-5]
#     tar_code = np.stack([np.where(i>l,1,0) for i,l in zip(int_arr, lim)])
#     matches_df[[f'int_{i}_tar' for i in range(16)]] = tar_code
#     matches_df = get_code_from_ints(matches_df, codebook, targets, int_str='_tar')
#     tar_code = codebook[matches_df['code_inds'].values]

#     return  1 - abs(np.array(matched_codes, dtype='int') - np.array(tar_code, dtype='int')).max(1)

def extract_rmses(vol, ixy_coords, size_xy = 10, px_size=100):

    rmses = []

    for k in range(len(ixy_coords)):

        i, x, y = ixy_coords[k]
        crop = np.s_[int(i),:, np.max([0,int(y/px_size-size_xy)]): int(y/px_size+size_xy+1), np.max([0,int(x/px_size-size_xy)]): int(x/px_size+size_xy+1)]

        rmses.append(vol[crop].mean().item())

    return rmses

# Cell
class code_net(nn.Module):

    def __init__(self, n_inputs=13, n_outputs=1):
        super(code_net, self).__init__()

        self.layers = nn.Sequential(
          nn.Linear(n_inputs, 128),
          nn.BatchNorm1d(128),
          nn.ReLU(),
          nn.Linear(128, 64),
          nn.BatchNorm1d(64),
          nn.ReLU(),
          nn.Linear(64, 64),
          nn.BatchNorm1d(64),
          nn.ReLU(),
          nn.Linear(64, 32),
          nn.BatchNorm1d(32),
          nn.ReLU(),
          nn.Linear(32, n_outputs)
        )

    def forward(self, x):

        return self.layers(x)

net = code_net().cuda()

def input_from_df(df):

    input_keys = ['prob', 'z', 'x_sig','y_sig','z_sig'] + [f'int_sig_{i}' for i in range(4)]  + [f'int_{i}' for i in range(4)]
    offsets = [0.75, 50., 20., 20., 15.] + 4*[1.] + 4*[4.]
    scales = [1., 50., 20., 20., 15.] + 4*[2.] + 4*[5.]
    inp_arr = df[input_keys].values
    inp_arr = (inp_arr - np.array(offsets))/np.array(scales)

    return torch.tensor(inp_arr, dtype=torch.float32).cuda()