"""Run MMLU-Pro evaluation on base model."""
import argparse
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.mmlu_eval import run_mmlu_pro_eval
from training_pipeline.paths import MMLU_BASE_DIR, MMLU_FINETUNED_DIR, DEFAULT_MODEL_DIR

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run MMLU-Pro evaluation")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_DIR),
                        help="Path to HF model")
    parser.add_argument("--output-dir", default=str(MMLU_BASE_DIR),
                        help="Output directory for results")
    parser.add_argument("--limit", type=int, default=100,
                        help="Limit samples (0 for full, default: 100 for quick)")
    parser.add_argument("--task", default="mmlu_pro",
                        help="Task name (default: mmlu_pro)")
    parser.add_argument("--batch-size", default="auto",
                        help="Batch size (default: auto)")
    parser.add_argument("--num-fewshot", type=int, default=0,
                        help="Number of few-shot examples")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Only print command (default)")
    parser.add_argument("--full-eval", action="store_true",
                        help="Run full evaluation (no limit)")
    parser.add_argument("--do-eval", action="store_true",
                        help="Actually run evaluation")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    limit = args.limit if not args.full_eval else 0
    dry_run = not args.do_eval

    results = run_mmlu_pro_eval(
        model_path=args.model_path,
        output_dir=Path(args.output_dir),
        limit=limit,
        task=args.task,
        batch_size=args.batch_size,
        num_fewshot=args.num_fewshot,
        dry_run=dry_run,
    )

    if dry_run:
        logger.info("\nTo actually evaluate, run with --do-eval")
        logger.info("For full evaluation, run with --full-eval --do-eval")
    else:
        logger.info(f"\nEvaluation complete. Results: {results}")


if __name__ == "__main__":
    main()
