"""Download Qwen3.5-9B from Hugging Face Hub."""
import argparse
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.hf_utils import download_model
from training_pipeline.paths import DEFAULT_MODEL_ID, DEFAULT_MODEL_DIR

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Download model from Hugging Face")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID,
                        help=f"HF model ID (default: {DEFAULT_MODEL_ID})")
    parser.add_argument("--local-dir", default=None,
                        help="Local directory to save model")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Only print download command (default)")
    parser.add_argument("--do-download", action="store_true",
                        help="Actually download the model")
    parser.add_argument("--hf-token", default=None,
                        help="HF token (or set HF_TOKEN env var)")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    dry_run = not args.do_download
    local_dir = Path(args.local_dir) if args.local_dir else None

    result = download_model(
        model_id=args.model_id,
        local_dir=local_dir,
        dry_run=dry_run,
        resume=True,
        token=args.hf_token,
    )

    if dry_run:
        logger.info("\nTo actually download, run with --do-download")
    else:
        logger.info(f"\nModel downloaded to: {result}")


if __name__ == "__main__":
    main()
