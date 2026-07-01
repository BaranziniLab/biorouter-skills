---
name: ucsf-hpc
description: Use when working with the UCSF CHPC HPC cluster — setting up SSH access, transferring files, submitting SLURM jobs, installing software, or exploring cluster resources.
license: Apache-2.0
user-invocable: true
---

# UCSF CHPC HPC Cluster

Verified May 2026. Confirm live state with `sinfo` and `scontrol show partition` before submitting large jobs.

---

## 1. SSH Setup

### Hosts

| Alias | Hostname | Role |
|---|---|---|
| `ucsf-bastion` | `chpc-ucsf-bastion-vm1.corehpc.ucsf.edu` | Gateway (internet-facing, Duo auth here) |
| `ucsf-login` | `chpc-ucsf-login-vm1.corehpc.ucsf.edu` | Login/submit node (reached via bastion) |

### One-time setup

**Step 1 — Generate an HPC-specific key (if you don't have one):**
```bash
HPC_USER=$(whoami)
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_ucsf -C "$HPC_USER@ucsf"
```

**Step 2 — Copy key to the bastion (one password + Duo push):**
```bash
HPC_USER=$(whoami)
ssh-copy-id -i ~/.ssh/id_ed25519_ucsf.pub $HPC_USER@chpc-ucsf-bastion-vm1.corehpc.ucsf.edu
```

**Step 3 — Add both hosts to `~/.ssh/config`:**
```
Host ucsf-bastion
    hostname chpc-ucsf-bastion-vm1.corehpc.ucsf.edu
    user <your-ucsf-username>
    IdentityFile ~/.ssh/id_ed25519_ucsf
    ServerAliveInterval 15s
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h:%p
    ControlPersist 8h

Host ucsf-login
    hostname chpc-ucsf-login-vm1.corehpc.ucsf.edu
    user <your-ucsf-username>
    ProxyJump ucsf-bastion
    IdentityFile ~/.ssh/id_ed25519_ucsf
    ServerAliveInterval 15s
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h:%p
    ControlPersist 24h
```

**Step 4 — Create the sockets directory:**
```bash
mkdir -p ~/.ssh/sockets && chmod 700 ~/.ssh/sockets
```

**Step 5 — Copy your public key to the login node:**
```bash
# Via the bastion (if direct access not yet set up)
cat ~/.ssh/id_ed25519_ucsf.pub | ssh ucsf-bastion \
  "ssh chpc-ucsf-login-vm1 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'"
```

**Step 6 — Add login node host key to known_hosts (avoids "host key verification failed"):**
```bash
ssh -o BatchMode=yes ucsf-bastion "ssh-keyscan chpc-ucsf-login-vm1 2>/dev/null" >> ~/.ssh/known_hosts
ssh -o BatchMode=yes ucsf-bastion "ssh-keyscan chpc-ucsf-login-vm1.corehpc.ucsf.edu 2>/dev/null" >> ~/.ssh/known_hosts
```

---

## 2. Avoiding Repeated Duo Pushes (ControlMaster)

SSH multiplexing reuses one authenticated socket for all subsequent connections. After the first Duo push, no further auth is needed until the socket expires.

### Start persistent sockets (one Duo push total):
```bash
ssh -fNM ucsf-bastion    # master socket, 8h persist
ssh -fNM ucsf-login      # master socket, 24h persist (tunnels through bastion)
```

### Check socket status:
```bash
ssh -O check ucsf-bastion
ssh -O check ucsf-login
```

### Close sockets manually:
```bash
ssh -O exit ucsf-login
ssh -O exit ucsf-bastion
```

### After expiry:
Re-run the two `ssh -fNM` commands. One Duo push re-establishes both for the full duration.

---

## 3. File Transfer

All commands use the `ucsf-login` alias and ride the multiplexed socket — no Duo prompts.

### Local → Cluster
```bash
# Single file
scp ~/Desktop/myfile.txt ucsf-login:/mnt/home/$USER/

# Folder (rsync preferred — resumable, incremental)
rsync -avz ~/Desktop/my_project/ ucsf-login:/mnt/home/$USER/my_project/
```

### Cluster → Local
```bash
# Single file
scp ucsf-login:/mnt/home/$USER/results.txt ~/Desktop/

# Multiple files by glob
scp "ucsf-login:/mnt/home/$USER/slurm_logs/*.out" ~/Desktop/logs/

# Entire folder
rsync -avz --progress ucsf-login:/mnt/home/$USER/slurm_logs/ ~/Desktop/slurm_logs/
```

### Download directly on the cluster (HTTP/HTTPS available, ICMP/ping blocked):
```bash
ssh ucsf-login "cd /mnt/scratch/$USER && curl -O https://example.com/file.tar.gz"
ssh ucsf-login "cd /mnt/scratch/$USER && wget https://example.com/file.tar.gz"
```

### Rsync flags reference
| Flag | Effect |
|---|---|
| `-a` | Archive: preserves permissions, timestamps, symlinks |
| `-v` | Verbose output |
| `-z` | Compress during transfer |
| `--progress` | Per-file transfer progress |
| `--exclude='*.tmp'` | Skip matching files |
| `--dry-run` | Preview without transferring |

---

## 4. Storage Layout

| Mount Point | Type | Pool Size | Notes |
|---|---|---|---|
| `/mnt/home/$USER/` | VAST NFS | 2.7 PB | Home — permanent, backed up |
| `/mnt/scratch/$USER/` | VAST NFS | 2.7 PB | Scratch — fast, NOT backed up; ~41 TB quota (verify with `quota -s`) |
| `/mnt/data/` | VAST NFS | 2.7 PB | Shared datasets |
| `/mnt/software/` | VAST NFS | 2.7 PB | Shared software installs |
| `/mnt/fac/` | Lab NFS | varies | Faculty/lab-specific allocations |

**Use `/mnt/scratch/$USER/` for all job I/O.** It is faster than home and has a large quota. Home is for code, configs, and results to keep long-term.

Check usage:
```bash
quota -s                   # scratch quota
du -sh /mnt/home/$USER/
du -sh /mnt/scratch/$USER/
```

---

## 5. Cluster Hardware and Partitions

### Login node (`chpc-ucsf-login-vm1`)
- **CPU**: AMD EPYC-Genoa, 32 cores
- **RAM**: 125 GB
- **OS**: Rocky Linux 9.7 (Blue Onyx), kernel 5.14.0
- **Internet**: HTTP/HTTPS accessible; ICMP (ping) blocked
- No GPUs — submit GPU jobs to compute nodes via SLURM

### Compute node specs

| Node type | Nodes | CPUs/node | RAM/node | GPUs |
|---|---|---|---|---|
| CPU | `gcpu2-[03-48]` | 336 (2×84c EPYC, HT on) | ~1.5 TB | None |
| GPU (L40S) | `ggpu1-[06-18]`, `ggpu4-[01-06]` | 64 | ~386 GB | 2× NVIDIA L40S (46 GB VRAM each) |
| POD / H200 | `ggpu3-[09-16]` | 208 | ~2 TB | 8× NVIDIA H200 (80 GB VRAM each) |
| Large GPU | `ggpu3-[17-20]`, `ggpu5-[01-03]` | TBD | TBD | TBD |

### Partitions

| Partition | Default | Max Walltime | Total CPUs | Nodes | GPU type | Notes |
|---|---|---|---|---|---|---|
| `cpu` | ✅ | 2 days | 21,088 | 46 | — | General CPU work |
| `gpu` | — | 2 days | 1,600 | 19 | L40S | Standard GPU jobs |
| `pod` | — | 2 days | 1,664 | 8 | H200 | Large model / high-mem GPU |
| `large_gpu` | — | 1 day | 1,728 | 7 | TBD | Big single-job GPU |
| `community` | — | 14 days | 7,680 | 80 | — | Long jobs; access may be group-restricted |
| `community_short` | — | 1 hour | 7,680 | 80 | — | Quick tests; access may be group-restricted |

No hard per-job CPU/memory limits — QoS policies control concurrency (`QOSMaxJobsPerUserLimit`).

### Check live availability:
```bash
sinfo                                   # partition summary
sinfo -p gpu                            # specific partition
scontrol show partition cpu             # full partition config
scontrol show node gcpu2-03            # full node spec
squeue                                  # all running/pending jobs
squeue -u $USER                           # your jobs only
w                                       # who is logged into the login node
```

---

## 6. SLURM Job Templates

Create a log directory first:
```bash
mkdir -p /mnt/home/$USER/slurm_logs
```

`%x` = job name, `%j` = job ID in output paths.

### CPU job
```bash
#!/bin/bash
#SBATCH --job-name=my_cpu_job
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16        # up to 336 per node
#SBATCH --mem=32G                 # up to ~1.5 TB per node
#SBATCH --time=02-00:00:00        # DD-HH:MM:SS
#SBATCH --output=/mnt/home/$USER/slurm_logs/%x_%j.out
#SBATCH --error=/mnt/home/$USER/slurm_logs/%x_%j.err

echo "Node: $(hostname), CPUs: $SLURM_CPUS_PER_TASK, Mem: $SLURM_MEM_PER_NODE MB"
module load miniforge3/25.11.0
# your commands here
```

### RAM-heavy job
```bash
#!/bin/bash
#SBATCH --job-name=my_ram_job
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=512G                # node has ~1.5 TB max
#SBATCH --time=02-00:00:00
#SBATCH --output=/mnt/home/$USER/slurm_logs/%x_%j.out
#SBATCH --error=/mnt/home/$USER/slurm_logs/%x_%j.err

echo "Node: $(hostname), Mem: $SLURM_MEM_PER_NODE MB"
# your commands here
```

### GPU job (L40S — `gpu` partition)
```bash
#!/bin/bash
#SBATCH --job-name=my_gpu_job
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1              # 1 or 2 per node on gpu partition
#SBATCH --time=02-00:00:00
#SBATCH --output=/mnt/home/$USER/slurm_logs/%x_%j.out
#SBATCH --error=/mnt/home/$USER/slurm_logs/%x_%j.err

echo "Node: $(hostname), GPU: $CUDA_VISIBLE_DEVICES"
nvidia-smi
module load miniforge3/25.11.0
module load nvidia/cuda/12.9.1
module load nvidia/cudnn/9.10_cuda_12.9
# your commands here
```

### Large GPU job (H200 — `pod` partition)
```bash
#!/bin/bash
#SBATCH --job-name=my_h200_job
#SBATCH --partition=pod
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=200G
#SBATCH --gres=gpu:nvidia_h200:1  # explicitly request H200; up to 8 per node
#SBATCH --time=02-00:00:00
#SBATCH --output=/mnt/home/$USER/slurm_logs/%x_%j.out
#SBATCH --error=/mnt/home/$USER/slurm_logs/%x_%j.err

echo "Node: $(hostname), GPU: $CUDA_VISIBLE_DEVICES"
nvidia-smi
module load miniforge3/25.11.0
module load nvidia/cuda/12.9.1
module load nvidia/cudnn/9.10_cuda_12.9
# your commands here
```

### Array job
```bash
#!/bin/bash
#SBATCH --job-name=my_array
#SBATCH --partition=cpu
#SBATCH --array=0-9               # SLURM_ARRAY_TASK_ID = 0..9
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01-00:00:00
#SBATCH --output=/mnt/home/$USER/slurm_logs/%x_%A_%a.out
#SBATCH --error=/mnt/home/$USER/slurm_logs/%x_%A_%a.err

echo "Array task: $SLURM_ARRAY_TASK_ID"
python myscript.py --index $SLURM_ARRAY_TASK_ID
```

### Submit, monitor, cancel
```bash
sbatch job.sh                                                    # submit
squeue -u $USER                                                    # check your jobs
sacct -u $USER --format=JobID,JobName,State,ExitCode,Elapsed       # job history
sacct -j <JOBID> --format=JobID,State,ExitCode,Elapsed,MaxRSS   # single job detail
scancel <JOBID>                                                  # cancel one job
scancel -u $USER                                                   # cancel ALL your jobs
```

---

## 7. Available Modules

```bash
module avail                    # list all
module avail python             # search by name
module spider cuda              # detailed dependency search
module load <name>              # load a module
module list                     # show currently loaded modules
module purge                    # unload all
```

### Key modules (verified May 2026)

| Category | Module | Notes |
|---|---|---|
| Python | `anaconda3/2024.10` | Full scipy stack |
| Python | `miniforge3/25.11.0` | Lighter; preferred for custom envs |
| CUDA | `nvidia/cuda/12.9.1` | CUDA 12.9 |
| cuDNN | `nvidia/cudnn/9.10_cuda_12.9` | Deep learning |
| NVHPC | `nvidia/nvhpc/2025_cuda12.9` | NVIDIA HPC SDK |
| GCC | `gnu14/14.2.0` | C/C++/Fortran (loaded by default) |
| MPI | `openmpi5/5.0.7` | Multi-node MPI (loaded by default) |
| Containers | `apptainer/1.4.1` | Singularity-compatible |
| Build | `cmake/4.0.0`, `spack/0.23.1` | |
| UCSF labs | `CBI`, `Sali` | Lab-specific software |

Default system Python is `3.9.25` at `/usr/bin/python3`. Always use a conda env for research code.

---

## 8. Installing Software

### Python environments with Miniforge (recommended)
```bash
module load miniforge3/25.11.0

# Create env in home (persistent)
conda create -n myenv python=3.11 -y
conda activate myenv

# OR create in scratch (larger quota)
conda create --prefix /mnt/scratch/$USER/envs/myenv python=3.11 -y
conda activate /mnt/scratch/$USER/envs/myenv

pip install numpy pandas scikit-learn matplotlib seaborn
```

### PyTorch with GPU support
```bash
module load miniforge3/25.11.0
module load nvidia/cuda/12.9.1
module load nvidia/cudnn/9.10_cuda_12.9
conda activate myenv

# For CUDA 12.x
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

### JAX with GPU support
```bash
pip install --upgrade "jax[cuda12_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html
```

### R
R is not in the default PATH. Options:
```bash
module avail R          # check for an R module
module load R           # if available

# Or install via conda
conda install -c conda-forge r-base r-tidyverse r-biocmanager
```

### Bioinformatics tools
```bash
conda install -c bioconda samtools bwa bowtie2 gatk4 star cellranger
conda install -c conda-forge nextflow
```

### Containers (Apptainer / Singularity-compatible)
```bash
module load apptainer/1.4.1

# Pull from Docker Hub
apptainer pull docker://ubuntu:22.04

# Pull from NVIDIA NGC (pre-built GPU containers)
apptainer pull docker://nvcr.io/nvidia/pytorch:24.01-py3

# Run with GPU passthrough (--nv flag)
apptainer exec --nv mycontainer.sif python train.py

# Run interactively
apptainer shell --nv mycontainer.sif
```

Containers are the most reliable approach for GPU workloads — they bundle CUDA, cuDNN, and all libraries in one portable image.

### Compiling from source
```bash
module load gnu14/14.2.0
module load cmake/4.0.0
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/mnt/home/$USER/local ..
make -j 16
make install
export PATH=/mnt/home/$USER/local/bin:$PATH   # add to ~/.bashrc to persist
```

---

## 9. Resource Guidelines

Confirmed hardware caps as of May 2026. Always check `scontrol show node` for current values.

| Resource | Practical max per job | Recommendation |
|---|---|---|
| CPUs (cpu partition) | 336/node | Request what you need; over-requesting delays scheduling |
| RAM (cpu partition) | ~1.5 TB/node | Add 20% buffer; check with `sacct --format=MaxRSS` after |
| GPU (gpu, L40S) | 2/node, 46 GB VRAM each | 4–8 CPUs per GPU is typical |
| GPU (pod, H200) | 8/node, 80 GB VRAM each | Use `--gres=gpu:nvidia_h200:N` |
| Walltime (cpu/gpu/pod) | 2 days | Test with `--time=00:10:00` first |
| Walltime (community) | 14 days | Useful for long-running jobs if accessible |
| Scratch quota | ~41 TB | Check with `quota -s` |

---

## 10. Common Pitfalls

| Problem | Cause | Fix |
|---|---|---|
| `Permission denied (publickey)` | Key not in `authorized_keys` | Run `ssh-copy-id` to the target host |
| `Host key verification failed` | Login node key missing from `known_hosts` | Run `ssh-keyscan` via bastion and append to `known_hosts` |
| Duo push on every command | ControlMaster not active | Run `ssh -fNM ucsf-bastion && ssh -fNM ucsf-login` |
| `community_short` jobs stuck pending | `ccpu1-[01-80]` nodes may be group-restricted | Use `cpu` partition with short walltime instead |
| Job fails immediately, exit code 1 | Missing `module load` inside the script | Always `module load` inside the SBATCH script, not just interactively |
| Out of memory / OOM kill | Underestimated RAM | Check `sacct -j <ID> --format=MaxRSS`; increase `--mem` |
| Slow file I/O in jobs | Writing to `/mnt/home` | Use `/mnt/scratch/$USER/` for job working files |
| GPU not detected in job | Forgot `--gres=gpu:N` | Add `--gres=gpu:1` (or more) to SBATCH headers |
| `nvidia-smi` not found | CUDA module not loaded | Add `module load nvidia/cuda/12.9.1` to SBATCH script |
