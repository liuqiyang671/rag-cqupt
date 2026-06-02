"""Create Ollama model from GGUF file."""
import argparse
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.ollama_utils import create_ollama_model, check_ollama_installed
from training_pipeline.paths import GGUF_DIR, OLLAMA_DIR

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Create Ollama model from GGUF")
    parser.add_argument("--gguf-path",
                        default=str(GGUF_DIR / "qwen35_9b_campus_q4_k_m.gguf"),
                        help="Path to GGUF file")
    parser.add_argument("--model-name", default="qwen35-campus:9b",
                        help="Ollama model name")
    parser.add_argument("--ollama-dir", default=str(OLLAMA_DIR),
                        help="Directory for Modelfile")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Only generate Modelfile (default)")
    parser.add_argument("--do-create", action="store_true",
                        help="Actually create the Ollama model")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    dry_run = not args.do_create

    logger.info("=" * 60)
    logger.info("Ollama Model Creation")
    logger.info("=" * 60)

    if not dry_run and not check_ollama_installed():
        logger.error(
            "Ollama is not installed.\n"
            "Download from: https://ollama.com/download\n"
            "After installing, re-run this script."
        )
        return

    result = create_ollama_model(
        gguf_path=args.gguf_path,
        model_name=args.model_name,
        ollama_dir=args.ollama_dir,
        dry_run=dry_run,
    )

    if dry_run:
        logger.info("\nTo actually create model, run with --do-create")
    else:
        logger.info(f"\nResult: {result}")


if __name__ == "__main__":
    main()
