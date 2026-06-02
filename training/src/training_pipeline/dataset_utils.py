"""Dataset preparation and splitting utilities."""
import json
import logging
import random
from collections import defaultdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_jsonl(path: Path) -> list:
    """Load a JSONL file into a list of dicts."""
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def save_jsonl(entries: list, path: Path) -> None:
    """Save a list of dicts to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info(f"Saved {len(entries)} entries to {path}")


def split_dataset(
    entries: list,
    train_ratio: float = 0.8,
    valid_ratio: float = 0.1,
    test_ratio: float = 0.1,
    group_by: str = "source_id",
    seed: int = 42,
) -> tuple:
    """Split dataset into train/valid/test, grouped by source_id to prevent data leakage.

    Args:
        entries: List of data entries
        train_ratio: Ratio for training set
        valid_ratio: Ratio for validation set
        test_ratio: Ratio for test set
        group_by: Key in meta to group by (prevents data leakage)
        seed: Random seed

    Returns:
        (train, valid, test) tuple of lists
    """
    assert abs(train_ratio + valid_ratio + test_ratio - 1.0) < 1e-6, \
        "Ratios must sum to 1.0"

    # Group entries by source_id
    groups = defaultdict(list)
    ungrouped = []
    for entry in entries:
        meta = entry.get("meta", {})
        source_id = meta.get(group_by)
        if source_id:
            groups[source_id].append(entry)
        else:
            ungrouped.append(entry)

    group_keys = list(groups.keys())
    random.seed(seed)
    random.shuffle(group_keys)

    n = len(group_keys)
    n_train = int(n * train_ratio)
    n_valid = int(n * valid_ratio)

    train_keys = set(group_keys[:n_train])
    valid_keys = set(group_keys[n_train:n_train + n_valid])
    test_keys = set(group_keys[n_train + n_valid:])

    train = ungrouped[:int(len(ungrouped) * train_ratio)]  # ungrouped split
    valid = []
    test = []

    for key in train_keys:
        train.extend(groups[key])
    for key in valid_keys:
        valid.extend(groups[key])
    for key in test_keys:
        test.extend(groups[key])

    logger.info(f"Split by '{group_by}': {n} groups -> "
                f"train={len(train_keys)} groups ({len(train)} entries), "
                f"valid={len(valid_keys)} groups ({len(valid)} entries), "
                f"test={len(test_keys)} groups ({len(test)} entries)")

    return train, valid, test


def compute_dataset_stats(entries: list) -> dict:
    """Compute statistics for a dataset."""
    stats = {
        "total": len(entries),
        "avg_question_len": 0,
        "avg_answer_len": 0,
        "categories": defaultdict(int),
    }
    if not entries:
        return stats

    q_lens = []
    a_lens = []
    for entry in entries:
        messages = entry.get("messages", [])
        for msg in messages:
            if msg.get("role") == "user":
                q_lens.append(len(msg["content"]))
            elif msg.get("role") == "assistant":
                a_lens.append(len(msg["content"]))
        meta = entry.get("meta", {})
        cat = meta.get("category", "unknown")
        stats["categories"][cat] += 1

    if q_lens:
        stats["avg_question_len"] = round(sum(q_lens) / len(q_lens), 1)
    if a_lens:
        stats["avg_answer_len"] = round(sum(a_lens) / len(a_lens), 1)
    stats["categories"] = dict(stats["categories"])
    return stats
