"""Prepare SFT dataset: split into train/valid/test."""
import argparse
import json
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.dataset_utils import (
    load_jsonl, save_jsonl, split_dataset, compute_dataset_stats,
)
from training_pipeline.paths import DATA_GENERATED, DATA_PROCESSED

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Prepare SFT dataset splits")
    parser.add_argument("--input", default=str(DATA_GENERATED / "campus_qa_generated.jsonl"),
                        help="Input JSONL path")
    parser.add_argument("--output-dir", default=str(DATA_PROCESSED),
                        help="Output directory")
    parser.add_argument("--train-ratio", type=float, default=0.8,
                        help="Training set ratio (default: 0.8)")
    parser.add_argument("--valid-ratio", type=float, default=0.1,
                        help="Validation set ratio (default: 0.1)")
    parser.add_argument("--test-ratio", type=float, default=0.1,
                        help="Test set ratio (default: 0.1)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--group-by", default="source_id",
                        help="Group by this meta key to prevent data leakage")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        logger.error("Please run 03_generate_campus_qa.py first.")
        return

    # Load data
    entries = load_jsonl(input_path)
    logger.info(f"Loaded {len(entries)} entries from {input_path}")

    if not entries:
        logger.error("No entries found in input file.")
        return

    # Split
    train, valid, test = split_dataset(
        entries,
        train_ratio=args.train_ratio,
        valid_ratio=args.valid_ratio,
        test_ratio=args.test_ratio,
        group_by=args.group_by,
        seed=args.seed,
    )

    # Save splits
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    save_jsonl(train, out_dir / "campus_sft_train.jsonl")
    save_jsonl(valid, out_dir / "campus_sft_valid.jsonl")
    save_jsonl(test, out_dir / "campus_sft_test.jsonl")

    # Also save test to eval dir
    from training_pipeline.paths import DATA_EVAL
    DATA_EVAL.mkdir(parents=True, exist_ok=True)
    save_jsonl(test, DATA_EVAL / "campus_eval.jsonl")

    # Stats
    logger.info("\n" + "=" * 50)
    logger.info("Dataset Statistics")
    logger.info("=" * 50)

    for name, dataset in [("train", train), ("valid", valid), ("test", test)]:
        stats = compute_dataset_stats(dataset)
        logger.info(f"\n[{name}]")
        logger.info(f"  Total: {stats['total']}")
        logger.info(f"  Avg question length: {stats['avg_question_len']} chars")
        logger.info(f"  Avg answer length: {stats['avg_answer_len']} chars")
        logger.info(f"  Categories: {stats['categories']}")

    logger.info(f"\nFiles saved to {out_dir}")
    logger.info("Done!")


if __name__ == "__main__":
    main()
