The exam guide asks you to evaluate **CPU vs GPU vs TPU** and to understand **distributed training with
data and model parallelism**. Questions typically describe a model and a symptom ("training takes 3 days",
"GPU utilisation is 20 %", "model doesn't fit in memory") and ask for the most effective change.

## Choosing hardware

| Hardware | Best for | Watch out for |
|---|---|---|
| **CPU** | Classic ML (sklearn, XGBoost on modest data), small models, input preprocessing, many cheap parallel trials | Slow for deep learning |
| **GPU** (NVIDIA: T4, L4, A100, H100…) | Most deep learning; flexible; custom ops; PyTorch & TensorFlow; mixed workloads | Cost; memory limits large models |
| **TPU** (Cloud TPU) | Large deep-learning models dominated by **matrix multiplications**, large batch sizes, long training runs; TensorFlow, **JAX**, PyTorch/XLA | Custom ops that must run on CPU, dynamic shapes, very small models, frequent host↔device transfers |
| **Edge accelerators** (mobile, Edge TPU) | On-device inference | Need compressed/quantised models (TF Lite) |

Rules of thumb:
- First check the **input pipeline** — an expensive accelerator waiting on data is the most common waste.
- TPUs shine when the model is big, mostly dense linear algebra and you can use large batches; a tiny
  model or lots of CPU-side custom code won't benefit.
- Use **mixed precision** (bfloat16 on TPUs, float16/bfloat16 on GPUs) to speed up training and halve
  memory.
- On Vertex AI, TPU VM training uses a single worker pool with one replica (the TPU slice itself is the
  parallel hardware).

## Data parallelism vs model parallelism

| | **Data parallelism** | **Model parallelism** |
|---|---|---|
| Idea | Every device holds a full copy of the model; each processes a different slice of the batch; gradients are averaged | The model itself is split across devices (layers = pipeline parallelism, tensors = tensor parallelism; sharding parameters = FSDP/ZeRO) |
| Use when | Model fits in one device's memory; you want faster training on more data | Model is **too large for one device** |
| Main cost | Gradient synchronisation (all-reduce) | Communication between model parts; complexity |

## TensorFlow distribution strategies (`tf.distribute`)

| Strategy | Setup |
|---|---|
| `MirroredStrategy` | One machine, multiple GPUs, synchronous all-reduce |
| `MultiWorkerMirroredStrategy` | Many machines (each with GPUs), synchronous all-reduce; reads `TF_CONFIG` |
| `TPUStrategy` | TPUs / TPU Pods |
| `ParameterServerStrategy` | Asynchronous training with parameter servers; tolerant of slow/preempted workers; good for very large embedding tables |
| `OneDeviceStrategy` / default | Single device |

PyTorch equivalents: `DistributedDataParallel` (data parallel), FSDP (sharded parameters for large
models). JAX uses `pjit`/sharding. Vertex AI sets `TF_CONFIG`/`CLUSTER_SPEC` so these discover their peers.

## Vertex AI worker pools for distributed jobs

| Pool | Role |
|---|---|
| 0 | Primary replica (chief) — exactly one; coordinates, often writes checkpoints/model |
| 1 | Workers |
| 2 | **Parameter servers** *or* **Reduction Server** replicas |
| 3 | Evaluators (not part of the TF cluster) |

### Reduction Server
An all-reduce implementation that **increases throughput and reduces latency of gradient aggregation**
in **multi-node, GPU, synchronous data-parallel** training (TensorFlow or PyTorch using **NCCL**
all-reduce). You add reducer replicas (CPU-only, e.g. `n1-highcpu-16`) in worker pool 2; their total
network bandwidth should match the workers'. It helps when communication between nodes is the bottleneck,
not for single-machine or TPU training.

## Input pipeline performance (`tf.data`)

- `prefetch(tf.data.AUTOTUNE)` overlaps data loading with training.
- `map(..., num_parallel_calls=AUTOTUNE)` parallelises preprocessing; `interleave` reads many files in
  parallel.
- `cache()` small datasets after expensive preprocessing.
- Use **sharded TFRecords** instead of millions of small files; read from the same region.
- Profile with TensorBoard's profiler — "device idle waiting for input" points to the pipeline.

## ⚖️ Symptom → fix

| Symptom | First thing to try |
|---|---|
| GPU/TPU utilisation low, CPU busy | Optimise `tf.data` (prefetch, parallel map, TFRecords), more vCPUs |
| Model doesn't fit in GPU memory | Smaller batch, mixed precision, gradient checkpointing; then model parallelism / FSDP / bigger-memory GPU |
| Training on one GPU too slow, model fits | Data parallelism: `MirroredStrategy` (one VM, many GPUs) then `MultiWorkerMirroredStrategy` |
| Multi-node GPU training bottlenecked on gradient sync | **Reduction Server**, faster interconnect, larger per-worker batch |
| Huge dense model, long training, TF/JAX | **TPUs** |
| Workers preempted / heterogeneous speeds | ParameterServerStrategy (async) or checkpoints + Spot retries |
| Large batch after scaling out hurts accuracy | Scale learning rate with batch size, warm-up |

## ⚖️ GPU vs TPU

| | GPU | TPU |
|---|---|---|
| Flexibility (custom ops, dynamic shapes) | **High** | Lower (XLA-compiled) |
| Frameworks | Everything | TF, JAX, PyTorch/XLA |
| Sweet spot | General DL, small–large models, inference | Large models, big batches, long runs, matrix-heavy |
| Precision | FP16/BF16/FP8 | **bfloat16** |

## 🪤 Exam traps

- **Adding more GPUs when the input pipeline is the bottleneck** — utilisation stays low.
- **Model parallelism for a model that fits** — data parallelism is simpler and faster.
- **TPUs for models with custom CPU ops** or tiny models — little or no speed-up.
- **Reduction Server for single-node or TPU training** — it's for multi-node GPU all-reduce.
- **Increasing workers without adjusting batch size / learning rate** — convergence problems.

## ✅ Key takeaways

- Fix the input pipeline before buying accelerators.
- GPUs = flexible default; TPUs = big matrix-heavy models with large batches.
- Data parallelism when the model fits; model parallelism / sharding when it doesn't.
- `MirroredStrategy` (1 machine) → `MultiWorkerMirroredStrategy` (many) → `TPUStrategy`; Reduction
  Server speeds multi-node GPU all-reduce.
