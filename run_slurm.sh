bsub -gpu "num=1" -q gpu_any -o logs/ofish.log -e logs/efish.log /groups/turaga/home/speisera/anaconda3/envs/decode2_dev/bin/python /groups/turaga/home/speisera/Mackebox/Artur/WorkDB/deepstorm/decode_fish/decode_fish/train.py +experiment=N2_352_b8 autoencoder.opt.lr=0.0003 autoencoder.step_size=3000 autoencoder.grad_clip=0 run_name=lr:0.0003xstep_size:3000xgrad_clip:0 output.group=sweep_b8
bsub -gpu "num=1" -q gpu_any -o logs/ofish.log -e logs/efish.log /groups/turaga/home/speisera/anaconda3/envs/decode2_dev/bin/python /groups/turaga/home/speisera/Mackebox/Artur/WorkDB/deepstorm/decode_fish/decode_fish/train.py +experiment=N2_352_b8 autoencoder.opt.lr=0.0003 autoencoder.step_size=3000 autoencoder.grad_clip=0.1 run_name=lr:0.0003xstep_size:3000xgrad_clip:0.1 output.group=sweep_b8
bsub -gpu "num=1" -q gpu_any -o logs/ofish.log -e logs/efish.log /groups/turaga/home/speisera/anaconda3/envs/decode2_dev/bin/python /groups/turaga/home/speisera/Mackebox/Artur/WorkDB/deepstorm/decode_fish/decode_fish/train.py +experiment=N2_352_b8 autoencoder.opt.lr=0.0003 autoencoder.step_size=3000 autoencoder.grad_clip=0.001 run_name=lr:0.0003xstep_size:3000xgrad_clip:0.001 output.group=sweep_b8
bsub -gpu "num=1" -q gpu_any -o logs/ofish.log -e logs/efish.log /groups/turaga/home/speisera/anaconda3/envs/decode2_dev/bin/python /groups/turaga/home/speisera/Mackebox/Artur/WorkDB/deepstorm/decode_fish/decode_fish/train.py +experiment=N2_352_b8 autoencoder.opt.lr=0.0001 autoencoder.step_size=3000 autoencoder.grad_clip=0 run_name=lr:0.0001xstep_size:3000xgrad_clip:0 output.group=sweep_b8
bsub -gpu "num=1" -q gpu_any -o logs/ofish.log -e logs/efish.log /groups/turaga/home/speisera/anaconda3/envs/decode2_dev/bin/python /groups/turaga/home/speisera/Mackebox/Artur/WorkDB/deepstorm/decode_fish/decode_fish/train.py +experiment=N2_352_b8 autoencoder.opt.lr=0.0001 autoencoder.step_size=3000 autoencoder.grad_clip=0.1 run_name=lr:0.0001xstep_size:3000xgrad_clip:0.1 output.group=sweep_b8
bsub -gpu "num=1" -q gpu_any -o logs/ofish.log -e logs/efish.log /groups/turaga/home/speisera/anaconda3/envs/decode2_dev/bin/python /groups/turaga/home/speisera/Mackebox/Artur/WorkDB/deepstorm/decode_fish/decode_fish/train.py +experiment=N2_352_b8 autoencoder.opt.lr=0.0001 autoencoder.step_size=3000 autoencoder.grad_clip=0.001 run_name=lr:0.0001xstep_size:3000xgrad_clip:0.001 output.group=sweep_b8
