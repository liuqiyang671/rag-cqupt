"""Generate campus QA pairs from knowledge base."""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.qa_generation import (
    load_knowledge_base, generate_qa_via_api, validate_qa_entry,
    deduplicate_qa, format_qa_messages, format_multi_turn_messages,
    QA_TYPE_PROMPTS, SYSTEM_PROMPT,
)
from training_pipeline.paths import DATA_RAW, DATA_GENERATED

logger = logging.getLogger(__name__)


def generate_from_api(
    kb_entries: list,
    output_path: Path,
    qa_per_entry_min: int = 3,
    qa_per_entry_max: int = 6,
    temperature: float = 0.8,
    max_tokens: int = 1024,
    max_retries: int = 3,
) -> list:
    """Generate QA pairs using API."""
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    base_url = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    model = os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")

    if not api_key:
        logger.error(
            "SILICONFLOW_API_KEY not set. Please set it in .env or environment.\n"
            "Example: export SILICONFLOW_API_KEY=your_key_here"
        )
        return []

    all_qa = []
    qa_types = list(QA_TYPE_PROMPTS.keys())

    for i, entry in enumerate(kb_entries):
        knowledge = entry.get("content", "") or entry.get("text", "")
        source_id = entry.get("id", f"kb_{i}")
        category = entry.get("category", "general")

        if not knowledge:
            logger.warning(f"Entry {i} has no content, skipping")
            continue

        # Generate 3-6 QA pairs per entry across different types
        num_to_generate = min(qa_per_entry_max, max(qa_per_entry_min, len(qa_types)))

        for j in range(num_to_generate):
            qa_type = qa_types[j % len(qa_types)]
            logger.info(f"[{i+1}/{len(kb_entries)}] Generating {qa_type} QA for entry {source_id}")

            result = generate_qa_via_api(
                knowledge=knowledge,
                qa_type=qa_type,
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                max_retries=max_retries,
            )

            if result is None:
                logger.warning(f"Failed to generate {qa_type} for entry {source_id}")
                continue

            # Format into messages
            if qa_type == "multi_turn" and "turns" in result:
                msg_entry = format_multi_turn_messages(
                    result["turns"], source_id, qa_type,
                )
            else:
                question = result.get("question", "")
                answer = result.get("answer", "")
                if question and answer:
                    msg_entry = format_qa_messages(
                        question, answer, source_id, qa_type,
                    )
                else:
                    continue

            if validate_qa_entry(msg_entry):
                all_qa.append(msg_entry)
            else:
                logger.warning(f"Validation failed for {qa_type} of entry {source_id}")

            # Rate limiting
            time.sleep(0.5)

        logger.info(f"  Generated {len(all_qa)} total QA pairs so far")

    # Deduplicate
    all_qa = deduplicate_qa(all_qa)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for qa in all_qa:
            f.write(json.dumps(qa, ensure_ascii=False) + "\n")
    logger.info(f"Saved {len(all_qa)} QA pairs to {output_path}")

    return all_qa


def main():
    parser = argparse.ArgumentParser(description="Generate campus QA pairs")
    parser.add_argument("--input", default=str(DATA_RAW / "campus_kb.example.jsonl"),
                        help="Path to knowledge base JSONL")
    parser.add_argument("--output", default=str(DATA_GENERATED / "campus_qa_generated.jsonl"),
                        help="Output path for generated QA")
    parser.add_argument("--min-per-entry", type=int, default=3,
                        help="Min QA pairs per KB entry")
    parser.add_argument("--max-per-entry", type=int, default=6,
                        help="Max QA pairs per KB entry")
    parser.add_argument("--temperature", type=float, default=0.8,
                        help="Generation temperature")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Only show what would be generated (default)")
    parser.add_argument("--do-generate", action="store_true",
                        help="Actually generate QA pairs")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    kb_path = Path(args.input)
    if not kb_path.exists():
        logger.error(
            f"Knowledge base not found: {kb_path}\n"
            "Please place your campus knowledge base in data/raw/.\n"
            "Format: JSONL with 'content'/'text', 'id', 'category' fields."
        )
        return

    kb_entries = load_knowledge_base(kb_path)
    logger.info(f"Loaded {len(kb_entries)} knowledge entries")

    target_total = (args.min_per_entry + args.max_per_entry) // 2 * len(kb_entries)
    logger.info(f"Target: {target_total} QA pairs ({args.min_per_entry}-{args.max_per_entry} per entry)")

    if args.dry_run and not args.do_generate:
        logger.info("[DRY RUN] Would generate QA pairs using API")
        logger.info(f"  Input: {kb_path}")
        logger.info(f"  Output: {args.output}")
        logger.info(f"  QA types: {list(QA_TYPE_PROMPTS.keys())}")
        logger.info(f"  API: SILICONFLOW_BASE_URL + SILICONFLOW_MODEL")
        logger.info("\nTo actually generate, run with --do-generate")
        return

    results = generate_from_api(
        kb_entries=kb_entries,
        output_path=Path(args.output),
        qa_per_entry_min=args.min_per_entry,
        qa_per_entry_max=args.max_per_entry,
        temperature=args.temperature,
    )
    logger.info(f"\nGeneration complete: {len(results)} QA pairs")


if __name__ == "__main__":
    main()
