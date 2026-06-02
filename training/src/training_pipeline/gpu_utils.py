"""GPU detection and VRAM monitoring utilities."""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    name: str
    vram_total_mb: float
    vram_free_mb: float
    cuda_available: bool
    compute_capability: Optional[tuple] = None


def get_gpu_info() -> GPUInfo:
    """Detect GPU and return info. Does not fail if CUDA unavailable."""
    try:
        import torch
        if not torch.cuda.is_available():
            return GPUInfo(
                name="N/A",
                vram_total_mb=0,
                vram_free_mb=0,
                cuda_available=False,
            )
        device = torch.cuda.current_device()
        props = torch.cuda.get_device_properties(device)
        total_mb = props.total_memory / (1024 * 1024)
        free_mb = (props.total_memory - torch.cuda.memory_allocated(device)) / (1024 * 1024)
        return GPUInfo(
            name=props.name,
            vram_total_mb=round(total_mb, 1),
            vram_free_mb=round(free_mb, 1),
            cuda_available=True,
            compute_capability=(props.major, props.minor),
        )
    except ImportError:
        return GPUInfo(name="N/A", vram_total_mb=0, vram_free_mb=0, cuda_available=False)


def log_gpu_info() -> GPUInfo:
    """Log GPU information and return it."""
    info = get_gpu_info()
    if info.cuda_available:
        logger.info(f"GPU: {info.name}")
        logger.info(f"VRAM Total: {info.vram_total_mb:.0f} MB")
        logger.info(f"VRAM Free: {info.vram_free_mb:.0f} MB")
        if info.compute_capability:
            logger.info(f"Compute Capability: {info.compute_capability[0]}.{info.compute_capability[1]}")
    else:
        logger.warning("CUDA is not available. Training will fail without GPU.")
    return info


def get_peak_vram_mb() -> float:
    """Return peak VRAM usage in MB since last reset."""
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.max_memory_allocated() / (1024 * 1024), 1)
    except ImportError:
        pass
    return 0.0


def reset_peak_vram() -> None:
    """Reset peak VRAM counter."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except ImportError:
        pass


def estimate_qlora_vram_gb(model_params_billion: float = 9.0) -> dict:
    """Estimate QLoRA VRAM usage for a given model size."""
    # Rough estimates for 4-bit NF4 QLoRA
    model_gb = model_params_billion * 0.5  # ~0.5 GB per B params in 4-bit
    lora_gb = model_params_billion * 0.02  # LoRA adapters (r=8)
    optimizer_gb = model_params_billion * 0.04  # Optimizer states
    activation_gb = 2.0  # Gradient checkpointing reduces this
    overhead_gb = 1.0  # CUDA overhead

    total_gb = model_gb + lora_gb + optimizer_gb + activation_gb + overhead_gb

    return {
        "model_4bit_gb": round(model_gb, 1),
        "lora_gb": round(lora_gb, 1),
        "optimizer_gb": round(optimizer_gb, 1),
        "activation_gb": round(activation_gb, 1),
        "overhead_gb": round(overhead_gb, 1),
        "total_estimated_gb": round(total_gb, 1),
    }
