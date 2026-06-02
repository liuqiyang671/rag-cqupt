"""Check environment: Python, torch, CUDA, GPU, and required packages."""
import argparse
import importlib
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.gpu_utils import get_gpu_info

logger = logging.getLogger(__name__)

REQUIRED_PACKAGES = [
    ("torch", "PyTorch"),
    ("transformers", "Hugging Face Transformers"),
    ("datasets", "Hugging Face Datasets"),
    ("peft", "PEFT (LoRA)"),
    ("trl", "TRL (SFT)"),
    ("bitsandbytes", "BitsAndBytes (4-bit quantization)"),
    ("accelerate", "Accelerate"),
    ("openai", "OpenAI SDK"),
    ("yaml", "PyYAML"),
    ("rouge_score", "ROUGE Score"),
    ("sentencepiece", "SentencePiece"),
]

OPTIONAL_PACKAGES = [
    ("lm_eval", "LM Evaluation Harness"),
    ("pandas", "Pandas"),
    ("numpy", "NumPy"),
    ("dotenv", "python-dotenv"),
    ("sklearn", "scikit-learn"),
]


def check_package(module_name: str, display_name: str) -> bool:
    """Check if a package is importable."""
    try:
        mod = importlib.import_module(module_name)
        version = getattr(mod, "__version__", "unknown")
        logger.info(f"  ✓ {display_name} ({module_name}) - version: {version}")
        return True
    except ImportError:
        logger.warning(f"  ✗ {display_name} ({module_name}) - NOT INSTALLED")
        return False


def main():
    parser = argparse.ArgumentParser(description="Check environment for training pipeline")
    parser.add_argument("--verbose", action="store_true", help="Show detailed info")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    logger.info("=" * 60)
    logger.info("Environment Check for Qwen3.5-9B Training Pipeline")
    logger.info("=" * 60)

    # Python version
    logger.info(f"\n[Python]")
    logger.info(f"  Version: {sys.version}")
    py_ver = sys.version_info
    if py_ver < (3, 10):
        logger.warning("  ⚠ Python 3.10+ is recommended")

    # GPU
    logger.info(f"\n[GPU]")
    gpu = get_gpu_info()
    if gpu.cuda_available:
        logger.info(f"  ✓ CUDA available")
        logger.info(f"  GPU: {gpu.name}")
        logger.info(f"  VRAM: {gpu.vram_total_mb:.0f} MB total, {gpu.vram_free_mb:.0f} MB free")
        if gpu.vram_total_mb < 12000:
            logger.warning("  ⚠ Less than 12GB VRAM. QLoRA for 9B model may OOM.")
            logger.warning("    Consider using Qwen3.5-4B as fallback.")
    else:
        logger.error("  ✗ CUDA NOT available")
        logger.error("    Training requires a CUDA-capable GPU.")
        logger.error("    Install PyTorch with CUDA: https://pytorch.org/get-started/locally/")

    # Required packages
    logger.info(f"\n[Required Packages]")
    all_required = True
    for mod, name in REQUIRED_PACKAGES:
        if not check_package(mod, name):
            all_required = False

    # Optional packages
    logger.info(f"\n[Optional Packages]")
    for mod, name in OPTIONAL_PACKAGES:
        check_package(mod, name)

    # Summary
    logger.info(f"\n{'=' * 60}")
    if all_required and gpu.cuda_available:
        logger.info("✓ Environment looks good! Ready for training.")
    else:
        logger.warning("⚠ Some issues found. Please fix them before training.")
        if not gpu.cuda_available:
            logger.error("  → Install CUDA-enabled PyTorch")
        if not all_required:
            logger.error("  → Install missing packages: pip install -r requirements.txt")

    logger.info("=" * 60)


if __name__ == "__main__":
    main()
