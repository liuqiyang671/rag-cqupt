"""One-click pipeline runner for all stages."""
import argparse
import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging

logger = logging.getLogger(__name__)

STAGES = [
    "check_env",
    "download_model",
    "eval_base",
    "generate_qa",
    "prepare_dataset",
    "train",
    "merge",
    "export_gguf",
    "create_ollama",
    "eval_finetuned",
    "compare",
]

STAGE_SCRIPTS = {
    "check_env": "00_check_env.py",
    "download_model": "01_download_model.py",
    "eval_base": "02_eval_mmlu_pro.py",
    "generate_qa": "03_generate_campus_qa.py",
    "prepare_dataset": "04_prepare_sft_dataset.py",
    "train": "05_train_qlora.py",
    "merge": "06_merge_lora.py",
    "export_gguf": "07_export_gguf.py",
    "create_ollama": "08_create_ollama_model.py",
    "eval_finetuned": "09_eval_campus_qa.py",
    "compare": "10_compare_results.py",
}

# Extra args for specific stages when using --do-train or --full-eval
STAGE_EXTRA_ARGS = {
    "train": ["--do-train"],
    "eval_base": ["--do-eval"],
    "eval_finetuned": ["--do-eval"],
}


def run_stage(stage: str, extra_args: list = None, dry_run: bool = True) -> bool:
    """Run a single pipeline stage."""
    script = STAGE_SCRIPTS.get(stage)
    if not script:
        logger.error(f"Unknown stage: {stage}")
        return False

    script_path = SCRIPT_DIR / script
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False

    cmd = [sys.executable, str(script_path)]

    if not dry_run and stage in STAGE_EXTRA_ARGS:
        cmd.extend(STAGE_EXTRA_ARGS[stage])

    if extra_args:
        cmd.extend(extra_args)

    logger.info(f"\n{'='*60}")
    logger.info(f"Stage: {stage}")
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info(f"{'='*60}")

    result = subprocess.run(cmd, cwd=str(TRAINING_ROOT))
    if result.returncode != 0:
        logger.error(f"Stage '{stage}' failed with return code {result.returncode}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run training pipeline stages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available stages:\n  " + "\n  ".join(STAGES) + "\n  all - Run all stages",
    )
    parser.add_argument("--stage", required=True,
                        help="Stage to run (or 'all')")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="All heavy tasks in dry-run mode (default)")
    parser.add_argument("--do-train", action="store_true",
                        help="Actually run training (overrides dry-run for training)")
    parser.add_argument("--full-eval", action="store_true",
                        help="Run full evaluation (not quick)")
    parser.add_argument("--start-from", default=None,
                        help="When using --stage all, start from this stage")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    if args.stage == "all":
        stages_to_run = STAGES[:]
        if args.start_from:
            if args.start_from in stages_to_run:
                idx = stages_to_run.index(args.start_from)
                stages_to_run = stages_to_run[idx:]
            else:
                logger.error(f"Unknown stage: {args.start_from}")
                return

        logger.info(f"Running all stages: {', '.join(stages_to_run)}")
        dry_run = not args.do_train

        for stage in stages_to_run:
            success = run_stage(stage, dry_run=dry_run)
            if not success:
                logger.error(f"Pipeline stopped at stage: {stage}")
                return

        logger.info("\n" + "=" * 60)
        logger.info("Pipeline complete!")
        logger.info("=" * 60)
    else:
        if args.stage not in STAGES:
            logger.error(f"Unknown stage: {args.stage}")
            logger.error(f"Available: {', '.join(STAGES)}")
            return

        dry_run = not args.do_train
        success = run_stage(args.stage, dry_run=dry_run)
        if not success:
            logger.error(f"Stage '{args.stage}' failed")


if __name__ == "__main__":
    main()
