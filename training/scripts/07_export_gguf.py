"""Export merged model to GGUF format using llama.cpp."""
import argparse
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.gguf_utils import export_gguf
from training_pipeline.paths import MERGED_DIR, GGUF_DIR

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Export model to GGUF format")
    parser.add_argument("--source-model", default=str(MERGED_DIR / "qwen35_9b_campus_merged"),
                        help="Path to merged HF model")
    parser.add_argument("--output-dir", default=str(GGUF_DIR),
                        help="Output directory for GGUF files")
    parser.add_argument("--llama-cpp-path", default="llama.cpp",
                        help="Path to llama.cpp directory")
    parser.add_argument("--f16-name", default="qwen35_9b_campus_f16.gguf",
                        help="Filename for f16 GGUF")
    parser.add_argument("--q4km-name", default="qwen35_9b_campus_q4_k_m.gguf",
                        help="Filename for Q4_K_M GGUF")
    parser.add_argument("--quant-type", default="Q4_K_M",
                        help="Quantization type")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Only print commands (default)")
    parser.add_argument("--do-export", action="store_true",
                        help="Actually export GGUF")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    dry_run = not args.do_export

    logger.info("=" * 60)
    logger.info("GGUF Export")
    logger.info("=" * 60)

    result = export_gguf(
        source_model_path=args.source_model,
        output_dir=args.output_dir,
        llama_cpp_path=args.llama_cpp_path,
        f16_output=args.f16_name,
        q4km_output=args.q4km_name,
        quant_type=args.quant_type,
        dry_run=dry_run,
    )

    if dry_run:
        logger.info("\nTo actually export, run with --do-export")
    else:
        logger.info(f"\nExport complete: {result}")


if __name__ == "__main__":
    main()
