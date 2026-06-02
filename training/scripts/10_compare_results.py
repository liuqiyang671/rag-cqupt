"""Generate comparison report for before/after fine-tuning."""
import argparse
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.compare_utils import generate_comparison_report
from training_pipeline.paths import OUTPUTS_DIR, REPORTS_DIR

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Generate comparison report")
    parser.add_argument("--outputs-dir", default=str(OUTPUTS_DIR),
                        help="Outputs directory with eval results")
    parser.add_argument("--reports-dir", default=str(REPORTS_DIR),
                        help="Directory to save reports")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    logger.info("=" * 60)
    logger.info("Generating Comparison Report")
    logger.info("=" * 60)

    result = generate_comparison_report(
        outputs_dir=Path(args.outputs_dir),
        reports_dir=Path(args.reports_dir),
    )

    logger.info(f"\nReports generated:")
    logger.info(f"  Markdown: {result['markdown_path']}")
    logger.info(f"  JSON: {result['json_path']}")


if __name__ == "__main__":
    main()
