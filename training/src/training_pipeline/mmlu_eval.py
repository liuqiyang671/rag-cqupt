"""MMLU-Pro evaluation using lm-evaluation-harness."""
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def run_mmlu_pro_eval(
    model_path: str,
    output_dir: Path,
    limit: int = 100,
    task: str = "mmlu_pro",
    batch_size: str = "auto",
    num_fewshot: int = 0,
    dry_run: bool = True,
    trust_remote_code: bool = True,
    dtype: str = "bfloat16",
) -> dict:
    """Run MMLU-Pro evaluation.

    Args:
        model_path: Path to HF model or model ID
        output_dir: Directory to save results
        limit: Limit number of samples (0 = full)
        task: Task name
        batch_size: Batch size
        num_fewshot: Number of few-shot examples
        dry_run: If True, only print the command
        trust_remote_code: Trust remote code
        dtype: Model dtype

    Returns:
        Dictionary with evaluation results
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_args = f"pretrained={model_path},trust_remote_code={trust_remote_code},dtype={dtype}"

    cmd = [
        "lm_eval",
        "--model", "hf",
        "--model_args", model_args,
        "--tasks", task,
        "--batch_size", batch_size,
        "--num_fewshot", str(num_fewshot),
        "--output_path", str(output_dir),
    ]
    if limit > 0:
        cmd.extend(["--limit", str(limit)])

    cmd_str = " ".join(cmd)
    logger.info(f"MMLU-Pro evaluation command:\n  {cmd_str}")

    if dry_run:
        logger.info("[DRY RUN] Would execute the above command.")
        return {
            "status": "dry_run",
            "command": cmd_str,
            "model_id": model_path,
            "task": task,
            "limit": limit,
        }

    logger.info("Starting MMLU-Pro evaluation...")
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time

    if result.returncode != 0:
        logger.error(f"MMLU-Pro evaluation failed:\n{result.stderr}")
        raise RuntimeError(f"lm_eval failed with return code {result.returncode}")

    # Parse results from output
    results = {
        "status": "completed",
        "model_id": model_path,
        "task": task,
        "limit": limit,
        "eval_time_seconds": round(elapsed, 1),
        "command": cmd_str,
    }

    # Primary: parse JSON result file written by lm_eval
    # lm_eval writes to {output_dir}/{model_path_sanitized}/{task}.json
    json_found = False
    for json_file in output_dir.rglob("*.json"):
        if json_file.name == "mmlu_pro_results.json":
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                eval_data = json.load(f)
            # lm_eval JSON structure: {"results": {task: {"acc": val, ...}}, ...}
            task_results = eval_data.get("results", {})
            if task in task_results:
                acc_val = task_results[task].get("acc")
                if acc_val is not None:
                    results["accuracy"] = acc_val
                    json_found = True
                    logger.info("Parsed accuracy=%.4f from %s", acc_val, json_file)
                    break
            # Also check for "acc,none" key variant
            for key in task_results:
                if task in key and "acc" in key:
                    acc_val = task_results[key].get("acc")
                    if acc_val is not None:
                        results["accuracy"] = acc_val
                        json_found = True
                        logger.info("Parsed accuracy=%.4f from %s (key=%s)", acc_val, json_file, key)
                        break
            if json_found:
                break
        except (json.JSONDecodeError, KeyError, TypeError):
            continue

    # Fallback: parse accuracy from stdout (less reliable)
    if not json_found:
        logger.warning("Could not parse JSON output, falling back to stdout parsing")
        for line in result.stdout.split("\n"):
            if "acc" in line.lower() and "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                for part in parts:
                    try:
                        val = float(part)
                        results["accuracy"] = val
                        json_found = True
                        break
                    except ValueError:
                        continue
            if json_found:
                break

    if "accuracy" not in results:
        logger.warning("Could not extract accuracy from evaluation output")

    # Save results
    results_file = output_dir / "mmlu_pro_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to {results_file}")

    return results
