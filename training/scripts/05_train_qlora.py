"""QLoRA fine-tuning for Qwen3.5 model."""
import argparse
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.train_utils import load_train_config, train
from training_pipeline.paths import CONFIGS_DIR

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="QLoRA fine-tuning for Qwen3.5")
    parser.add_argument("--config", default=str(CONFIGS_DIR / "qlora_train_qwen35_9b.yaml"),
                        help="Path to training config YAML")
    parser.add_argument("--model-path", default=None,
                        help="Override model path from config")
    parser.add_argument("--train-file", default=None,
                        help="Override training data path")
    parser.add_argument("--output-dir", default=None,
                        help="Override output directory")
    parser.add_argument("--max-seq-length", type=int, default=None,
                        help="Override max sequence length")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Override number of epochs")
    parser.add_argument("--learning-rate", type=float, default=None,
                        help="Override learning rate")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Only show config and estimate VRAM (default)")
    parser.add_argument("--do-train", action="store_true",
                        help="Actually start training")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    # Load config
    cfg = load_train_config(args.config)

    # Apply overrides (config is a nested dict: model/data/training/lora)
    if args.model_path:
        cfg.setdefault("model", {})["model_name_or_path"] = args.model_path
    if args.train_file:
        cfg.setdefault("data", {})["train_file"] = args.train_file
    if args.output_dir:
        cfg.setdefault("training", {})["output_dir"] = args.output_dir
    if args.max_seq_length:
        cfg.setdefault("data", {})["max_seq_length"] = args.max_seq_length
    if args.epochs:
        cfg.setdefault("training", {})["num_train_epochs"] = args.epochs
    if args.learning_rate:
        cfg.setdefault("training", {})["learning_rate"] = args.learning_rate

    dry_run = not args.do_train

    logger.info("=" * 60)
    logger.info("QLoRA Fine-tuning: Qwen3.5-9B Campus Q&A")
    logger.info("=" * 60)

    try:
        train(cfg, dry_run=dry_run)
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            logger.error(
                "\n" + "=" * 60 + "\n"
                "OUT OF MEMORY ERROR\n"
                "Suggestions:\n"
                "  1. Reduce --max-seq-length to 512\n"
                "  2. Use Qwen3.5-4B: --model-path models/Qwen3.5-4B\n"
                "  3. Close other GPU-using processes\n"
                "  4. Check GPU with: python scripts/00_check_env.py\n"
                + "=" * 60
            )
        raise

    if dry_run:
        logger.info("\nTo actually train, run with --do-train")


if __name__ == "__main__":
    main()
