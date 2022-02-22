# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/12_utils.ipynb (unless otherwise specified).

__all__ = ['seed_everything', 'free_mem', 'center_crop', 'smooth', 'gaussian_sphere', 'tiff_imread', 'load_tiff_image',
           'load_tiff_from_list', 'gpu', 'cpu', 'prepend_line', 'zip_longest_special', 'param_iter',
           'generate_perlin_noise_2d_torch', 'generate_fractal_noise_2d_torch', 'generate_perlin_noise_3d_torch',
           'generate_fractal_noise_3d_torch']

# Cell
from ..imports import *
from itertools import product as iter_product
from tifffile import imread

import gc
import random

# Cell
def seed_everything(seed=1234):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
seed_everything()

def free_mem():
    gc.collect()
    torch.cuda.empty_cache()

def center_crop(volume, zyx_ext):

    shape_3d = volume.shape[-3:]
    center = [s//2 for s in shape_3d]
    volume = volume[...,center[0]-math.floor(zyx_ext[0]/2):center[0]+math.ceil(zyx_ext[0]/2),
                        center[1]-math.floor(zyx_ext[1]/2):center[1]+math.ceil(zyx_ext[1]/2),
                        center[2]-math.floor(zyx_ext[2]/2):center[2]+math.ceil(zyx_ext[2]/2)]
    return volume

def smooth(x,window_len=11,window='flat'):

    if window_len<3:
        return x

    s=np.r_[x[window_len-1:0:-1],x,x[-2:-window_len-1:-1]]
    if window == 'flat': #moving average
        w=np.ones(window_len,'d')

    y=np.convolve(w/w.sum(),s,mode='valid')
    return y

def gaussian_sphere(shape, radius, position):
    grid = [slice(-x0, dim - x0) for x0, dim in zip(position, shape)]
    position = np.ogrid[grid]
    arr = np.exp(-position[0]**2 / (2 * (radius[0] ** 2))) * np.exp(-position[1]**2 / (2 * (radius[1] ** 2))) * np.exp(-position[2]**2 / (2 * (radius[2] ** 2))) / (2 * np.pi * (radius[0] * radius[1] * radius[2]))
    return arr

# Cell
def tiff_imread(path):
    '''helper function to read tiff file with pathlib object or str'''
    if isinstance(path, str) : return imread(path)
    if isinstance(path, Path): return imread(str(path))

def load_tiff_image(image_path: str):
    "Given tiff stack path, loads the stack and converts it to a tensor. If necessary adds a dimension for the batch size"
    image_path = Path(image_path)
    image  = torch.tensor(tiff_imread(image_path).astype('float32'))
#     if len(image.shape) == 3: image.unsqueeze_(0)
#     assert len(image.shape) == 4, 'the shape of image must be 4, (1, Z, X, Y)'
    #removing minum values of the image
    return image

def load_tiff_from_list(path_list):
    imgs = []
    for p in path_list:
        imgs.append(load_tiff_image(p))
    return np.concatenate(imgs,0)

# Cell
def gpu(x):
    '''Transforms numpy array or torch tensor torch torch.cuda.FloatTensor'''
    return torch.cuda.FloatTensor(x).cuda()

def cpu(x):
    '''Transforms torch tensor into numpy array'''
    if torch.is_tensor(x):
        return x.cpu().detach().numpy()
    else:
        return x

# Cell
def prepend_line(file_name, line):
    """ Insert given string as a new line at the beginning of a file """
    dummy_file = file_name + '.bak'
    with open(file_name, 'r') as read_obj, open(dummy_file, 'w') as write_obj:
        write_obj.write(line + '\n')
        for line in read_obj:
            write_obj.write(line)
    os.remove(file_name)
    os.rename(dummy_file, file_name)

def zip_longest_special(*iterables):
    def filter(items, defaults):
        return tuple(d if i is sentinel else i for i, d in zip(items, defaults))
    sentinel = object()
    iterables = itertools.zip_longest(*iterables, fillvalue=sentinel)
    first = next(iterables)
    yield filter(first, [None] * len(first))
    for item in iterables:
        yield filter(item, first)

class param_iter(object):

    def __init__(self):

        self.keys = []
        self.vals = []

    def add(self, name, *args):

        self.keys.append(name)
        self.vals.append(args)

    def param_product(self):

        all_params = []
        for values in iter_product(*self.vals):

            params = dict()
            for i,val in zip(self.keys,values):
                params.update({i : val })

            all_params.append(params)

        return all_params

    def param_zip(self):

        all_params = []
        for values in zip_longest_special(*self.vals):

            params = dict()
            for i,val in zip(self.keys,values):
                params.update({i : val })

            all_params.append(params)

        return all_params

# Cell
def generate_perlin_noise_2d_torch(shape, res, device='cpu'):
    ''' Adopted from https://pvigier.github.io/2018/11/02/2d-perlin-noise-numpy.html '''

    def f(t):
        return 6*t**5 - 15*t**4 + 10*t**3

    delta = (res[0] / shape[0], res[1] / shape[1])
    d = (shape[0] // res[0], shape[1] // res[1])
    grid = torch.stack(torch.meshgrid(torch.arange(0, res[0], delta[0], device=device),
                                      torch.arange(0, res[1], delta[1], device=device)), dim = -1) % 1
    # Gradients
    angles = 2*np.pi*torch.rand(res[0]+1, res[1]+1).to(device)
    gradients = torch.stack((torch.cos(angles), torch.sin(angles)),  axis=2).to(device)
    gradients = gradients.repeat_interleave(d[0], 0).repeat_interleave(d[1], 1)
    g00 = gradients[    :-d[0],    :-d[1]]
    g10 = gradients[d[0]:     ,    :-d[1]]
    g01 = gradients[    :-d[0],d[1]:     ]
    g11 = gradients[d[0]:     ,d[1]:     ]
    # Ramps
    n00 = torch.sum(torch.dstack((grid[:,:,0]  , grid[:,:,1]  )) * g00, 2)
    n10 = torch.sum(torch.dstack((grid[:,:,0]-1, grid[:,:,1]  )) * g10, 2)
    n01 = torch.sum(torch.dstack((grid[:,:,0]  , grid[:,:,1]-1)) * g01, 2)
    n11 = torch.sum(torch.dstack((grid[:,:,0]-1, grid[:,:,1]-1)) * g11, 2)
    # Interpolation
    t = f(grid)
    n0 = n00*(1-t[:,:,0]) + t[:,:,0]*n10
    n1 = n01*(1-t[:,:,0]) + t[:,:,0]*n11
    return np.sqrt(2.)*((1-t[:,:,1])*n0 + t[:,:,1]*n1)


def generate_fractal_noise_2d_torch(shape, res, octaves=1, persistence=0.5, device='cpu'):

    noise = torch.zeros(shape).to(device)
    frequency = 1
    amplitude = 1
    for _ in range(octaves):
        noise += amplitude * generate_perlin_noise_2d_torch(shape, (frequency*res[0], frequency*res[1]), device=device)
        amplitude *= persistence
    return noise

# Cell
def generate_perlin_noise_3d_torch(shape, res, device='cpu'):
    ''' Adopted from https://pvigier.github.io/2018/11/02/3d-perlin-noise-numpy.html '''
    def f(t):
        return 6*t**5 - 15*t**4 + 10*t**3

    delta = (res[0] / shape[0], res[1] / shape[1], res[2] / shape[2])
    d = (shape[0] // res[0], shape[1] // res[1], shape[2] // res[2])

    grid = torch.stack(torch.meshgrid(torch.arange(0, res[0], delta[0], device=device),
                                      torch.arange(0, res[1], delta[1], device=device),
                                      torch.arange(0, res[2], delta[2], device=device)), dim = -1) % 1

    theta = 2*np.pi*torch.rand(res[0]+1, res[1]+1, res[2]+1).to(device)
    phi = 2*np.pi*torch.rand(res[0]+1, res[1]+1, res[2]+1).to(device)

    gradients = torch.stack((torch.sin(phi)*torch.cos(theta), torch.sin(phi)*torch.sin(theta), torch.cos(phi)), axis=3)
    gradients[-1] = gradients[0]

    g000 = gradients[0:-1,0:-1,0:-1].repeat_interleave(d[0], 0).repeat_interleave(d[1], 1).repeat_interleave(d[2], 2)
    g100 = gradients[1:  ,0:-1,0:-1].repeat_interleave(d[0], 0).repeat_interleave(d[1], 1).repeat_interleave(d[2], 2)
    g010 = gradients[0:-1,1:  ,0:-1].repeat_interleave(d[0], 0).repeat_interleave(d[1], 1).repeat_interleave(d[2], 2)
    g110 = gradients[1:  ,1:  ,0:-1].repeat_interleave(d[0], 0).repeat_interleave(d[1], 1).repeat_interleave(d[2], 2)
    g001 = gradients[0:-1,0:-1,1:  ].repeat_interleave(d[0], 0).repeat_interleave(d[1], 1).repeat_interleave(d[2], 2)
    g101 = gradients[1:  ,0:-1,1:  ].repeat_interleave(d[0], 0).repeat_interleave(d[1], 1).repeat_interleave(d[2], 2)
    g011 = gradients[0:-1,1:  ,1:  ].repeat_interleave(d[0], 0).repeat_interleave(d[1], 1).repeat_interleave(d[2], 2)
    g111 = gradients[1:  ,1:  ,1:  ].repeat_interleave(d[0], 0).repeat_interleave(d[1], 1).repeat_interleave(d[2], 2)
#     # Ramps
    n000 = torch.sum(torch.stack((grid[:,:,:,0]  , grid[:,:,:,1]  , grid[:,:,:,2]  ), axis=3) * g000, 3)
    n100 = torch.sum(torch.stack((grid[:,:,:,0]-1, grid[:,:,:,1]  , grid[:,:,:,2]  ), axis=3) * g100, 3)
    n010 = torch.sum(torch.stack((grid[:,:,:,0]  , grid[:,:,:,1]-1, grid[:,:,:,2]  ), axis=3) * g010, 3)
    n110 = torch.sum(torch.stack((grid[:,:,:,0]-1, grid[:,:,:,1]-1, grid[:,:,:,2]  ), axis=3) * g110, 3)
    n001 = torch.sum(torch.stack((grid[:,:,:,0]  , grid[:,:,:,1]  , grid[:,:,:,2]-1), axis=3) * g001, 3)
    n101 = torch.sum(torch.stack((grid[:,:,:,0]-1, grid[:,:,:,1]  , grid[:,:,:,2]-1), axis=3) * g101, 3)
    n011 = torch.sum(torch.stack((grid[:,:,:,0]  , grid[:,:,:,1]-1, grid[:,:,:,2]-1), axis=3) * g011, 3)
    n111 = torch.sum(torch.stack((grid[:,:,:,0]-1, grid[:,:,:,1]-1, grid[:,:,:,2]-1), axis=3) * g111, 3)
#     # Interpolation
    t = f(grid)
    n00 = n000*(1-t[:,:,:,0]) + t[:,:,:,0]*n100
    n10 = n010*(1-t[:,:,:,0]) + t[:,:,:,0]*n110
    n01 = n001*(1-t[:,:,:,0]) + t[:,:,:,0]*n101
    n11 = n011*(1-t[:,:,:,0]) + t[:,:,:,0]*n111
    n0 = (1-t[:,:,:,1])*n00 + t[:,:,:,1]*n10
    n1 = (1-t[:,:,:,1])*n01 + t[:,:,:,1]*n11
    return ((1-t[:,:,:,2])*n0 + t[:,:,:,2]*n1)

def generate_fractal_noise_3d_torch(shape, res, octaves=1, persistence=0.5, device='cpu'):
    noise = torch.zeros(shape, device=device)
    frequency = 1
    amplitude = 1
    for _ in range(octaves):
        noise += amplitude * generate_perlin_noise_3d_torch(shape, (frequency*res[0], frequency*res[1], frequency*res[2]), device=device)
        frequency *= 2
        amplitude *= persistence
    return noise