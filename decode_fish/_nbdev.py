# AUTOGENERATED BY NBDEV! DO NOT EDIT!

__all__ = ["index", "modules", "custom_doc_links", "git_url"]

index = {"number_of_features_per_level": "00_models.ipynb",
         "create_conv": "00_models.ipynb",
         "SingleConv": "00_models.ipynb",
         "DoubleConv": "00_models.ipynb",
         "Upsampling": "00_models.ipynb",
         "Encoder": "00_models.ipynb",
         "Decoder": "00_models.ipynb",
         "Abstract3DUNet": "00_models.ipynb",
         "UNet3D": "00_models.ipynb",
         "OutputNet": "00_models.ipynb",
         "UnetDecodeNoBn_2S": "00_models.ipynb",
         "LinearInterpolatedPSF": "01_psf.ipynb",
         "Microscope": "02_microscope.ipynb",
         "place_psf": "02_microscope.ipynb",
         "extract_psf_roi": "02_microscope.ipynb",
         "get_roi_filt_inds": "02_microscope.ipynb",
         "mic_inp_apply_inds": "02_microscope.ipynb",
         "add_pos_noise": "02_microscope.ipynb",
         "concat_micro_inp": "02_microscope.ipynb",
         "place_roi": "02b_place_psfs.ipynb",
         "CudaPlaceROI": "02b_place_psfs.ipynb",
         "sCMOS": "03_noise.ipynb",
         "PointProcessUniform": "04_pointsource.ipynb",
         "list_to_locations": "04_pointsource.ipynb",
         "get_phased_ints": "04_pointsource.ipynb",
         "PointProcessGaussian": "05_gmm_loss.ipynb",
         "get_sample_mask": "05_gmm_loss.ipynb",
         "get_true_labels_mf": "05_gmm_loss.ipynb",
         "grp_range": "05_gmm_loss.ipynb",
         "cum_count_per_group": "05_gmm_loss.ipynb",
         "add_colorbar": "06_plotting.ipynb",
         "plot_3d_projections": "06_plotting.ipynb",
         "scat_3d_projections": "06_plotting.ipynb",
         "extract_roi": "15_fit_psf.ipynb",
         "plot_channels": "06_plotting.ipynb",
         "combine_figures": "06_plotting.ipynb",
         "load_model_state": "07_file_io.ipynb",
         "get_df_from_hdf5": "07_file_io.ipynb",
         "add_df_to_hdf5": "07_file_io.ipynb",
         "swap_psf_vol": "07_file_io.ipynb",
         "get_gaussian_psf": "07_file_io.ipynb",
         "get_vol_psf": "07_file_io.ipynb",
         "load_psf": "07_file_io.ipynb",
         "load_psf_noise_micro": "07_file_io.ipynb",
         "load_post_proc": "07_file_io.ipynb",
         "get_dataloader": "07_file_io.ipynb",
         "load_all": "07_file_io.ipynb",
         "DecodeDataset": "08_dataset.ipynb",
         "print_class_signature": "08_dataset.ipynb",
         "TransformBase": "08_dataset.ipynb",
         "ScaleTensor": "08_dataset.ipynb",
         "RandScale": "08_dataset.ipynb",
         "UniformValue": "08_dataset.ipynb",
         "get_forward_scaling": "08_dataset.ipynb",
         "RandomCrop3D": "08_dataset.ipynb",
         "AddFoci": "08_dataset.ipynb",
         "torch_gaussian_filter": "08_dataset.ipynb",
         "get_uneven": "08_dataset.ipynb",
         "GaussianSmoothing": "08_dataset.ipynb",
         "AddPerlinNoise": "08_dataset.ipynb",
         "get_roi_mask": "08_dataset.ipynb",
         "sample_to_df": "09_output_trafo.ipynb",
         "SIPostProcess": "09_output_trafo.ipynb",
         "ISIPostProcess": "09_output_trafo.ipynb",
         "matching": "10_evaluation.ipynb",
         "shift_df": "11_emitter_io.ipynb",
         "percentile_filter": "11_emitter_io.ipynb",
         "sig_filt": "11_emitter_io.ipynb",
         "nm_to_px": "11_emitter_io.ipynb",
         "px_to_nm": "11_emitter_io.ipynb",
         "cat_emitter_dfs": "11_emitter_io.ipynb",
         "append_emitter_df": "11_emitter_io.ipynb",
         "crop_df": "11_emitter_io.ipynb",
         "exclude_borders": "11_emitter_io.ipynb",
         "get_n_locs": "11_emitter_io.ipynb",
         "sel_int_ch": "11_emitter_io.ipynb",
         "zero_int_ch": "11_emitter_io.ipynb",
         "get_peaks": "11_emitter_io.ipynb",
         "remove_fids": "11_emitter_io.ipynb",
         "remove_doublets": "11_emitter_io.ipynb",
         "seed_everything": "12_utils.ipynb",
         "free_mem": "12_utils.ipynb",
         "center_crop": "12_utils.ipynb",
         "smooth": "12_utils.ipynb",
         "gaussian_sphere": "12_utils.ipynb",
         "expand_codebook": "12_utils.ipynb",
         "tiff_imread": "12_utils.ipynb",
         "load_tiff_image": "12_utils.ipynb",
         "load_tiff_from_list": "12_utils.ipynb",
         "gpu": "12_utils.ipynb",
         "cpu": "12_utils.ipynb",
         "prepend_line": "12_utils.ipynb",
         "zip_longest_special": "12_utils.ipynb",
         "param_iter": "12_utils.ipynb",
         "generate_perlin_noise_2d_torch": "12_utils.ipynb",
         "generate_fractal_noise_2d_torch": "12_utils.ipynb",
         "generate_perlin_noise_3d_torch": "12_utils.ipynb",
         "generate_fractal_noise_3d_torch": "12_utils.ipynb",
         "estimate_noise_scale": "12_utils.ipynb",
         "get_color_shift_inp": "12_utils.ipynb",
         "eval_logger": "13_train.ipynb",
         "save_train_state": "13_train.ipynb",
         "exp_train_eval": "13_train.ipynb",
         "train": "13_train.ipynb",
         "get_peaks_3d": "15_fit_psf.ipynb",
         "plot_detection": "15_fit_psf.ipynb",
         "fit_psf": "15_fit_psf.ipynb",
         "get_simulation_statistics": "16_visualization.ipynb",
         "sl_plot": "16_visualization.ipynb",
         "gt_plot": "16_visualization.ipynb",
         "eval_random_crop": "16_visualization.ipynb",
         "plot_micro_pars": "16_visualization.ipynb",
         "plot_slice_psf_pars": "16_visualization.ipynb",
         "eval_random_sim": "16_visualization.ipynb",
         "sim_data": "17_eval_routines.ipynb",
         "get_prediction": "17_eval_routines.ipynb",
         "window_predict": "18_predict_funcs.ipynb",
         "plot_gene_numbers": "19_MERFISH_routines.ipynb",
         "plot_gene_panels": "19_MERFISH_routines.ipynb",
         "make_roc": "19_MERFISH_routines.ipynb",
         "code_net": "22_MERFISH_codenet.ipynb",
         "conv_net": "22_MERFISH_codenet.ipynb",
         "input_from_df": "22_MERFISH_codenet.ipynb",
         "net": "22_MERFISH_codenet.ipynb",
         "train_metric_net": "22_MERFISH_codenet.ipynb",
         "get_istdeco_df": "23_MERFISH_comparison.ipynb",
         "get_bardensr_tensor": "23_MERFISH_comparison.ipynb",
         "get_bardensr_df": "23_MERFISH_comparison.ipynb",
         "simfish_to_df": "24_exp_specific.ipynb",
         "matlab_fq_to_df": "24_exp_specific.ipynb",
         "load_sim_fish": "24_exp_specific.ipynb",
         "big_fishq_to_df": "24_exp_specific.ipynb",
         "rsfish_to_df": "24_exp_specific.ipynb",
         "read_MOp_tiff": "24_exp_specific.ipynb",
         "read_starfish_tiff": "24_exp_specific.ipynb",
         "get_benchmark_from_starfish": "24_exp_specific.ipynb",
         "get_starfish_benchmark": "24_exp_specific.ipynb",
         "get_starfish_codebook": "24_exp_specific.ipynb",
         "get_istdeco": "24_exp_specific.ipynb",
         "get_mop_codebook": "24_exp_specific.ipynb",
         "get_mop_benchmark": "24_exp_specific.ipynb",
         "get_mop_fov": "24_exp_specific.ipynb",
         "get_mop_colors": "24_exp_specific.ipynb",
         "get_train_eval_benchmark_MOp": "24_exp_specific.ipynb",
         "get_train_eval_benchmark_starfish": "24_exp_specific.ipynb",
         "df_pp_mop": "24_exp_specific.ipynb",
         "df_pp_starfish": "24_exp_specific.ipynb",
         "gen_train_dataset": "26_gen_train.ipynb",
         "rescale_train": "27_testtime_rescale.ipynb"}

modules = ["engine/model.py",
           "engine/psf.py",
           "engine/microscope.py",
           "engine/place_psfs.py",
           "engine/noise.py",
           "engine/point_process.py",
           "engine/gmm_loss.py",
           "funcs/plotting.py",
           "funcs/file_io.py",
           "funcs/dataset.py",
           "funcs/output_trafo.py",
           "funcs/evaluation.py",
           "funcs/emitter_io.py",
           "funcs/utils.py",
           "funcs/train_funcs.py",
           "funcs/fit_psf.py",
           "funcs/visualization.py",
           "funcs/routines.py",
           "funcs/predict.py",
           "funcs/merfish_eval.py",
           "funcs/merfish_codenet.py",
           "funcs/merfish_comparison.py",
           "funcs/exp_specific.py",
           "funcs/gen_train_funcs.py",
           "funcs/tt_rescale.py"]

doc_url = "https://turagalab.github.io/decode_fish/"

git_url = "https://github.com/TuragaLab/decode_fish/tree/master/"

def custom_doc_links(name): return None
