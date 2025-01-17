# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/18_predict_funcs.ipynb (unless otherwise specified).

__all__ = ['window_predict']

# Cell
from ..imports import *
from .utils import *
from monai.inferers import sliding_window_inference
from .emitter_io import append_emitter_df

# Cell
def window_predict(model, post_proc, image_vol, window_size=[None,256,256], crop=np.s_[:,:,:,:,:], bs=1, device='cuda', chrom_map=None, scale=None, progress_bar=False):
    pred_df = DF()
    with torch.no_grad():

        print(image_vol.shape)
        if image_vol.ndim == 4:
            image_vol = image_vol[None]

        n_batches = int(np.ceil(len(image_vol)/bs))

        if scale is not None:
            image_vol = image_vol * scale.to(image_vol.device)

        if chrom_map is not None:
            image_vol = torch.concat([image_vol,chrom_map.to(image_vol.device).repeat_interleave(len(image_vol),0)], 1)

        if crop is not None:
            image_vol = image_vol[crop]

        for i in tqdm(range(n_batches), disable=not(progress_bar)):
            inp = image_vol[i*bs:(i+1)*bs]
            output = sliding_window_inference(inp, window_size, 1, model.to(device), overlap=0.2, sw_device=device, device='cpu', mode='gaussian')
            output = model.tensor_to_dict(output)
            p_si = sliding_window_inference(output['logits'], window_size, 1, post_proc, overlap=0.2, sw_device=device, device='cpu', mode='gaussian')
            i_df = post_proc.get_df(output, p_si)
            pred_df = append_emitter_df(pred_df, i_df)
            free_mem()

        return pred_df