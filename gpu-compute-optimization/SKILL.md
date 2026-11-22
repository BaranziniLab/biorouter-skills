---
name: gpu-compute-optimization
description: Make scientific Python faster on NVIDIA GPUs and prove the result is still correct, choosing the least disruptive layer (CuPy, cuDF, cuML, cuGraph, cuVS, cuCIM, KvikIO, Numba-CUDA, Warp), benchmarking fairly against the CPU baseline, and running the job on Wynton GPU nodes or Modal. Use when NumPy, SciPy, pandas, scikit-learn, NetworkX or image-processing code is slow, when someone mentions CUDA, GPU memory, kernels, profiling, data transfer bottlenecks, multi-GPU work, or where to get a GPU.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/optimize-for-gpu)"
---

# GPU Compute Optimization

A GPU port is worth it only if it is both **faster on the real workload** and **numerically
equivalent** to the code it replaces. This skill gets there in the smallest steps that work, and
says where to run the result. The detailed guide and its library references are adapted from
K-Dense Scientific Agent Skills (MIT; see `LICENSE-UPSTREAM`).

## Decide whether a GPU will help

Answer these with the person before porting anything:

1. **Where does the time go?** Profile the CPU version first (`cProfile`, `py-spy`,
   `line_profiler`). If most time is I/O, Python loops over small objects, or waiting on a
   database, a GPU will not help; fix that first.
2. **Is the hot part data-parallel?** Large array maths, dataframe joins and group-bys on
   millions of rows, distance computations, graph algorithms, image filters and model training
   usually are. Branch-heavy code on small inputs usually is not.
3. **Does the data fit in GPU memory**, or can it be streamed in chunks? Check VRAM on the
   target GPU (46 GB on a Wynton L40S, 80 GB on an H200).
4. **What is the acceptable tolerance?** GPUs often compute in a different order or in lower
   precision. Agree on a tolerance (absolute and relative) before measuring speed.

## Choose the smallest layer that works

| Code today | First thing to try | Reference |
| --- | --- | --- |
| pandas | `cudf.pandas` accelerator mode (no code changes), then explicit cuDF if needed | `references/optimize-for-gpu/references/cudf.md` |
| NumPy or SciPy arrays | CuPy as a drop-in for the array module | `references/optimize-for-gpu/references/cupy.md` |
| scikit-learn | `cuml.accel` or explicit cuML estimators | `references/optimize-for-gpu/references/cuml.md` |
| NetworkX | `nx-cugraph` backend, then cuGraph | `references/optimize-for-gpu/references/cugraph.md` |
| Nearest-neighbour or vector search | cuVS | `references/optimize-for-gpu/references/cuvs.md` |
| scikit-image or large image processing | cuCIM | `references/optimize-for-gpu/references/cucim.md` |
| File reads that starve the GPU | KvikIO (GPUDirect Storage where available) | `references/optimize-for-gpu/references/kvikio.md` |
| A custom loop no library covers | Numba-CUDA kernels, or NVIDIA Warp for simulation and geometry | `references/optimize-for-gpu/references/numba.md`, `references/optimize-for-gpu/references/warp.md` |

The full decision framework, with when to stop at each layer, is in
`references/optimize-for-gpu/references/decision_framework.md`, and before-and-after code
patterns are in `references/optimize-for-gpu/references/code_transformation_patterns.md`.
Deep learning frameworks (PyTorch, JAX) already run on GPUs; for them the work is usually data
loading, mixed precision and batch size, covered with the training code in
`scientific-machine-learning`.

## Measure honestly

- **Keep data on the GPU** between steps; a port that copies to the host after each operation
  often runs slower than the CPU version.
- **Synchronise before timing** (`cupy.cuda.Device().synchronize()` or the library's
  equivalent), discard the first warm-up run (compilation, memory pool growth), and report the
  median of several runs.
- **Compare like with like**: the same input size as the real workload, the CPU baseline using
  all its cores, and end-to-end time including transfers, not just the kernel.
- **Validate first, then time**: compare outputs to the CPU version within the agreed tolerance
  on real data, including edge cases (empty input, NaN, very large values).
- **Decide explicitly**: keep the port, revise it, or reject it. A 1.3x speed-up that adds a
  hard CUDA dependency may not be worth it.

## Where to run it

- **Wynton (UCSF).** Use the `ucsf-hpc` skill's GPU job templates: the `gpu` partition for
  NVIDIA L40S (1 or 2 per node, `#SBATCH --gres=gpu:1`) and the `pod` partition for H200
  (`#SBATCH --gres=gpu:nvidia_h200:1`, up to 8 per node). Load the CUDA module that matches the
  installed RAPIDS or CuPy wheels.
- **Modal.** Run the `modal` CLI through the Developer shell: write the job as a Modal app with a
  GPU type in the function decorator, test with `modal run`, and deploy only when it works. The
  person signs in with `modal token new` themselves; never handle the token. Modal bills by GPU
  time, so state the GPU type and expected run time first. (ModalAgent is retired; this is its
  replacement.)
- **A local workstation** with an NVIDIA GPU works for development; Apple Silicon Macs have no
  CUDA, so RAPIDS does not run there.

## In Biorouter

Profiling, porting and benchmarking run with the Developer shell. Keep the CPU version and the
benchmark script in the project so the comparison can be rerun; `replication-package-audit`
checks that before results are shared. R workloads on CPUs belong in `high-performance-r`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/optimize-for-gpu.md` | The optimisation workflow: contract and baseline, suitability, least disruptive layer, coherent GPU data path, validation, benchmarking |
| `references/optimize-for-gpu/references/installation.md` | RAPIDS and CuPy installation, CUDA versions, platform limits |

Library references in `references/optimize-for-gpu/references/` also cover cuSpatial, cuxfilter
and RAFT.
