"""Evaluate campus QA performance on base or fine-tuned model."""
import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(TRAINING_ROOT / "src"))

from training_pipeline.logging_utils import setup_logging
from training_pipeline.dataset_utils import load_jsonl
from training_pipeline.paths import (
    DATA_EVAL, DATA_PROCESSED, DEFAULT_MODEL_DIR,
    CAMPUS_EVAL_BASE_DIR, CAMPUS_EVAL_FINETUNED_DIR,
)

logger = logging.getLogger(__name__)


def exact_match(predicted: str, expected: str) -> bool:
    """Check exact match after normalization."""
    pred = predicted.strip().lower()
    gold = expected.strip().lower()
    return pred == gold


def keyword_hit_rate(predicted: str, keywords: List[str]) -> float:
    """Check what fraction of keywords appear in the prediction."""
    if not keywords:
        return 1.0
    pred_lower = predicted.lower()
    hits = sum(1 for kw in keywords if kw.lower() in pred_lower)
    return hits / len(keywords)


def compute_rouge_l(predicted: str, expected: str) -> float:
    """Compute ROUGE-L score."""
    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
        scores = scorer.score(expected, predicted)
        return scores["rougeL"].fmeasure
    except ImportError:
        return 0.0


def extract_keywords_from_answer(answer: str) -> List[str]:
    """Extract simple keywords from answer for keyword matching."""
    # Simple approach: extract significant words
    words = re.findall(r'[一-鿿]+|[a-zA-Z]+', answer)
    # Filter short words
    keywords = [w for w in words if len(w) >= 2]
    return keywords[:10]  # Top 10 keywords


def evaluate_model(
    model_path: str,
    eval_data: List[Dict],
    output_dir: Path,
    use_ollama: bool = False,
    ollama_model: str = "qwen35-campus:9b",
    use_rouge: bool = False,
    dry_run: bool = True,
) -> dict:
    """Evaluate model on campus QA test set."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        logger.info("[DRY RUN] Would evaluate model:")
        logger.info(f"  Model: {'Ollama:' + ollama_model if use_ollama else model_path}")
        logger.info(f"  Test samples: {len(eval_data)}")
        logger.info(f"  Output: {output_dir}")
        logger.info("  To actually evaluate, run with --do-eval")
        return {"status": "dry_run"}

    system_prompt = (
        "你是重庆邮电大学的智能校园助手，负责回答师生关于校园生活、"
        "教务管理、校园设施等方面的问题。请根据提供的资料准确回答。"
    )

    if use_ollama:
        import requests
        ollama_url = "http://localhost:11434/api/generate"

        def generate(question: str) -> str:
            resp = requests.post(ollama_url, json={
                "model": ollama_model,
                "prompt": question,
                "stream": False,
                "system": system_prompt,
            })
            return resp.json().get("response", "")
    else:
        # Use HF model
        from training_pipeline.hf_utils import load_model_for_inference
        model, tokenizer = load_model_for_inference(model_path)

        def generate(question: str) -> str:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ]
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
            inputs = tokenizer(text, return_tensors="pt").to(model.device)
            outputs = model.generate(
                **inputs, max_new_tokens=512, do_sample=True, temperature=0.7,
            )
            response = tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True,
            )
            return response

    # Evaluate
    results_list = []
    em_scores = []
    kh_scores = []
    rl_scores = []

    for i, item in enumerate(eval_data):
        messages = item.get("messages", [])
        question = ""
        expected = ""
        for msg in messages:
            if msg["role"] == "user":
                question = msg["content"]
            elif msg["role"] == "assistant":
                expected = msg["content"]

        if not question or not expected:
            continue

        predicted = generate(question)
        keywords = extract_keywords_from_answer(expected)

        em = exact_match(predicted, expected)
        kh = keyword_hit_rate(predicted, keywords)
        rl = compute_rouge_l(predicted, expected) if use_rouge else 0.0

        em_scores.append(1.0 if em else 0.0)
        kh_scores.append(kh)
        if use_rouge:
            rl_scores.append(rl)

        results_list.append({
            "question": question,
            "expected": expected,
            "predicted": predicted,
            "exact_match": em,
            "keyword_hit_rate": kh,
            "rougeL": rl if use_rouge else None,
        })

        if (i + 1) % 10 == 0:
            logger.info(f"  Evaluated {i+1}/{len(eval_data)}")

    # Aggregate
    summary = {
        "model_path": model_path,
        "total_samples": len(results_list),
        "exact_match": round(sum(em_scores) / len(em_scores), 4) if em_scores else 0,
        "keyword_hit_rate": round(sum(kh_scores) / len(kh_scores), 4) if kh_scores else 0,
    }
    if use_rouge and rl_scores:
        summary["rougeL"] = round(sum(rl_scores) / len(rl_scores), 4)

    # Save
    results_file = output_dir / "campus_eval_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    details_file = output_dir / "campus_eval_details.json"
    with open(details_file, "w", encoding="utf-8") as f:
        json.dump(results_list, f, indent=2, ensure_ascii=False)

    logger.info(f"\nResults: {json.dumps(summary, indent=2)}")
    logger.info(f"Saved to {results_file}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate campus QA performance")
    parser.add_argument("--eval-data",
                        default=str(DATA_EVAL / "campus_eval.jsonl"),
                        help="Path to evaluation data")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_DIR),
                        help="Path to HF model")
    parser.add_argument("--output-dir", default=str(CAMPUS_EVAL_BASE_DIR),
                        help="Output directory")
    parser.add_argument("--ollama", action="store_true",
                        help="Use Ollama model instead of HF model")
    parser.add_argument("--ollama-model", default="qwen35-campus:9b",
                        help="Ollama model name")
    parser.add_argument("--use-rouge", action="store_true",
                        help="Compute ROUGE-L scores")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Only show evaluation plan (default)")
    parser.add_argument("--do-eval", action="store_true",
                        help="Actually run evaluation")
    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    eval_path = Path(args.eval_data)
    if not eval_path.exists():
        logger.error(f"Evaluation data not found: {eval_path}")
        logger.error("Run 04_prepare_sft_dataset.py first to create test set.")
        return

    eval_data = load_jsonl(eval_path)
    logger.info(f"Loaded {len(eval_data)} evaluation samples")

    result = evaluate_model(
        model_path=args.model_path,
        eval_data=eval_data,
        output_dir=Path(args.output_dir),
        use_ollama=args.ollama,
        ollama_model=args.ollama_model,
        use_rouge=args.use_rouge,
        dry_run=not args.do_eval,
    )

    if not args.do_eval:
        logger.info("\nTo actually evaluate, run with --do-eval")


if __name__ == "__main__":
    main()
