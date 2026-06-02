"""Merge LoRA adapter into base model."""
import argparse
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.merge_utils import merge_lora
from training_pipeline.paths import DEFAULT_MODEL_DIR, LORA_DIR, MERGED_DIR

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Merge LoRA adapter into base model")
    parser.add_argument("--base-model", default=str(DEFAULT_MODEL_DIR),
                        help="Path to base HF model (non-quantized)")
    parser.add_argument("--lora-path", default=str(LORA_DIR / "qwen35_9b_campus_lora"),
                        help="Path to LoRA adapter")
    parser.add_argument("--output-dir", default=str(MERGED_DIR / "qwen35_9b_campus_merged"),
                        help="Output directory for merged model")
    parser.add_argument("--dtype", default="bfloat16",
                        help="Model dtype (default: bfloat16)")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Only print merge plan (default)")
    parser.add_argument("--do-merge", action="store_true",
                        help="Actually merge the model")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    dry_run = not args.do_merge

    logger.info("=" * 60)
    logger.info("LoRA Merge")
    logger.info("=" * 60)

    result = merge_lora(
        base_model_path=args.base_model,
        lora_adapter_path=args.lora_path,
        output_dir=args.output_dir,
        torch_dtype=args.dtype,
        dry_run=dry_run,
    )

    if dry_run:
        logger.info("\nTo actually merge, run with --do-merge")
    else:
        logger.info(f"\nMerge complete: {result}")


if __name__ == "__main__":
    main()
