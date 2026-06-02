"""Hugging Face model download utilities."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def download_model(
    model_id: str = "Qwen/Qwen3.5-9B",
    local_dir: Optional[Path] = None,
    dry_run: bool = True,
    resume: bool = True,
    token: Optional[str] = None,
) -> Path:
    """Download a model from Hugging Face Hub.

    Args:
        model_id: HF model ID (e.g., "Qwen/Qwen3.5-9B")
        local_dir: Local directory to save the model
        dry_run: If True, only print the download command
        resume: Resume interrupted downloads
        token: HF token for gated models

    Returns:
        Path to the downloaded model directory
    """
    from .paths import MODELS_DIR, DEFAULT_MODEL_DIR

    if local_dir is None:
        local_dir = MODELS_DIR / model_id.split("/")[-1]
    local_dir = Path(local_dir)

    if dry_run:
        logger.info("[DRY RUN] Would download model:")
        logger.info(f"  Model ID: {model_id}")
        logger.info(f"  Local dir: {local_dir}")
        logger.info(f"  Resume: {resume}")
        logger.info("  To actually download, run without --dry-run")
        return local_dir

    if local_dir.exists() and any(local_dir.iterdir()):
        logger.info(f"Model already exists at {local_dir}")
        return local_dir

    logger.info(f"Downloading {model_id} to {local_dir} ...")
    local_dir.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=model_id,
        local_dir=str(local_dir),
        resume_download=resume,
        token=token,
    )
    logger.info(f"Download complete: {local_dir}")
    return local_dir


def load_model_for_inference(
    model_path: str,
    device_map: str = "auto",
    torch_dtype: str = "bfloat16",
    trust_remote_code: bool = True,
):
    """Load a Hugging Face model for inference (not training)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dtype_map = {
        "bfloat16": torch.bfloat16,
        "float16": torch.float16,
        "float32": torch.float32,
    }
    dtype = dtype_map.get(torch_dtype, torch.bfloat16)

    logger.info(f"Loading model from {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=trust_remote_code
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map=device_map,
        torch_dtype=dtype,
        trust_remote_code=trust_remote_code,
    )
    return model, tokenizer
