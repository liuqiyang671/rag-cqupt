"""Centralized path management for the training pipeline."""
import os
from pathlib import Path
from typing import Optional

# Project root: training/
TRAINING_ROOT = Path(__file__).resolve().parent.parent.parent

# Data directories
DATA_RAW = TRAINING_ROOT / "data" / "raw"
DATA_GENERATED = TRAINING_ROOT / "data" / "generated"
DATA_PROCESSED = TRAINING_ROOT / "data" / "processed"
DATA_EVAL = TRAINING_ROOT / "data" / "eval"

# Config directory
CONFIGS_DIR = TRAINING_ROOT / "configs"

# Output directories
OUTPUTS_DIR = TRAINING_ROOT / "outputs"
MMLU_BASE_DIR = OUTPUTS_DIR / "mmlu_base"
MMLU_FINETUNED_DIR = OUTPUTS_DIR / "mmlu_finetuned"
CAMPUS_EVAL_BASE_DIR = OUTPUTS_DIR / "campus_eval_base"
CAMPUS_EVAL_FINETUNED_DIR = OUTPUTS_DIR / "campus_eval_finetuned"
REPORTS_DIR = OUTPUTS_DIR / "reports"

# Save directories
SAVES_DIR = TRAINING_ROOT / "saves"
LORA_DIR = SAVES_DIR / "lora"
MERGED_DIR = SAVES_DIR / "merged"
GGUF_DIR = SAVES_DIR / "gguf"
OLLAMA_DIR = SAVES_DIR / "ollama"

# Model directory
MODELS_DIR = TRAINING_ROOT / "models"

# Default model paths
DEFAULT_MODEL_ID = "Qwen/Qwen3.5-9B"
DEFAULT_MODEL_DIR = MODELS_DIR / "Qwen3.5-9B"
FALLBACK_MODEL_ID = "Qwen/Qwen3.5-4B"
FALLBACK_MODEL_DIR = MODELS_DIR / "Qwen3.5-4B"


def ensure_dirs() -> None:
    """Create all required directories if they don't exist."""
    dirs = [
        DATA_RAW, DATA_GENERATED, DATA_PROCESSED, DATA_EVAL,
        CONFIGS_DIR, OUTPUTS_DIR, MMLU_BASE_DIR, MMLU_FINETUNED_DIR,
        CAMPUS_EVAL_BASE_DIR, CAMPUS_EVAL_FINETUNED_DIR, REPORTS_DIR,
        SAVES_DIR, LORA_DIR, MERGED_DIR, GGUF_DIR, OLLAMA_DIR, MODELS_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def resolve_path(path_str: str, base: Optional[Path] = None) -> Path:
    """Resolve a path string relative to training root if not absolute."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (base or TRAINING_ROOT) / p
