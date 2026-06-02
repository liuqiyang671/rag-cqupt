"""Campus QA generation from knowledge base."""
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

# Patterns that may indicate fabricated contact information
_FAKE_CONTACT_PATTERNS = [
    re.compile(r'\b1[3-9]\d{9}\b'),           # Chinese mobile numbers
    re.compile(r'\b0\d{2,3}-?\d{7,8}\b'),     # Landline numbers
    re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # Email
    re.compile(r'https?://[^\s）)]+'),          # URLs
]

logger = logging.getLogger(__name__)

QA_TYPE_PROMPTS = {
    "single_turn": (
        "根据知识生成问答对。只输出JSON，不要其他文字。\n\n"
        "知识：{knowledge}\n\n"
        "输出：{{\"question\": \"学生的问题\", \"answer\": \"准确的回答\"}}"
    ),
    "multi_turn": (
        "根据知识生成2轮对话。只输出JSON，不要其他文字。\n\n"
        "知识：{knowledge}\n\n"
        "输出：{{\"turns\": [{{\"user\": \"问题1\", \"assistant\": \"回答1\"}}, {{\"user\": \"追问\", \"assistant\": \"回答2\"}}]}}"
    ),
    "rag_qa": (
        "根据知识生成问答对。只输出JSON，不要其他文字。\n\n"
        "知识：{knowledge}\n\n"
        "输出：{{\"question\": \"学生的问题\", \"answer\": \"回答\", \"context\": \"引用的知识片段\"}}"
    ),
    "process_qa": (
        "根据知识生成办事流程问答。只输出JSON，不要其他文字。\n\n"
        "知识：{knowledge}\n\n"
        "输出：{{\"question\": \"如何办理某事\", \"answer\": \"办理步骤\"}}"
    ),
    "tool_call": (
        "根据知识生成意图识别样例。只输出JSON，不要其他文字。\n\n"
        "知识：{knowledge}\n\n"
        "输出：{{\"question\": \"学生的需求\", \"intent\": \"意图类型\", \"answer\": \"回答\"}}"
    ),
    "reject": (
        "生成一个无法回答的问答样例。只输出JSON，不要其他文字。\n\n"
        "知识：{knowledge}\n\n"
        "输出：{{\"question\": \"超出知识范围的问题\", \"answer\": \"抱歉，这个问题我无法回答\"}}"
    ),
}

SYSTEM_PROMPT = (
    "你是重庆邮电大学的智能校园助手，负责回答师生关于校园生活、"
    "教务管理、校园设施等方面的问题。请根据提供的资料准确回答，"
    "如果资料中没有相关信息，请如实告知。"
)


def load_knowledge_base(kb_path: Path) -> list:
    """Load knowledge base from JSONL file."""
    entries = []
    with open(kb_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    logger.info(f"Loaded {len(entries)} knowledge entries from {kb_path}")
    return entries


def generate_qa_via_api(
    knowledge: str,
    qa_type: str,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    max_retries: int = 3,
    timeout: int = 60,
) -> Optional[dict]:
    """Generate a single QA pair using OpenAI-compatible API."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    prompt = QA_TYPE_PROMPTS.get(qa_type, QA_TYPE_PROMPTS["single_turn"]).format(
        knowledge=knowledge
    )

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content.strip()
            # Try to parse JSON from response
            # Handle potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            # Clean control characters that break JSON parsing
            content = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', content)
            # Fix common JSON issues: trailing commas, unescaped quotes
            content = re.sub(r',\s*}', '}', content)
            content = re.sub(r',\s*]', ']', content)
            return json.loads(content)
        except Exception as e:
            logger.warning(f"API attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2.0)
            # Log actual content for debugging
            if attempt == max_retries - 1:
                logger.debug(f"Raw API response: {repr(content[:500])}")
    return None


def validate_qa_entry(entry: dict, check_no_fake_contact: bool = True) -> bool:
    """Validate a QA entry has required fields and optionally no fake contact info.

    Args:
        entry: QA entry dict with 'messages' key.
        check_no_fake_contact: If True, reject entries containing phone numbers,
            email addresses, or URLs that may be fabricated by the LLM.

    Returns:
        True if entry is valid, False otherwise.
    """
    if not isinstance(entry, dict):
        return False
    messages = entry.get("messages", [])
    if not messages:
        return False
    for msg in messages:
        if not msg.get("role") or not msg.get("content"):
            return False
        if msg["role"] == "user" and not msg["content"].strip():
            return False
        if msg["role"] == "assistant" and not msg["content"].strip():
            return False

    # Check for fabricated contact info in assistant responses
    if check_no_fake_contact:
        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            content = msg["content"]
            for pattern in _FAKE_CONTACT_PATTERNS:
                if pattern.search(content):
                    logger.debug("Entry rejected: contains potential fake contact info")
                    return False
    return True


def _char_ngrams(text: str, n: int = 3) -> set:
    """Extract character n-grams from text."""
    text = text.replace(" ", "")
    return {text[i:i+n] for i in range(max(0, len(text) - n + 1))}


def _jaccard_similarity(a: set, b: set) -> float:
    """Compute Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def deduplicate_qa(entries: list, similarity_threshold: float = 0.85) -> list:
    """Deduplicate QA entries using exact match + fuzzy n-gram similarity.

    Args:
        entries: List of QA entry dicts with 'messages' key.
        similarity_threshold: Jaccard similarity threshold for fuzzy dedup.

    Returns:
        Deduplicated list of entries.
    """
    seen_questions: list[tuple[set, dict]] = []  # (ngrams, entry) pairs
    unique = []
    exact_seen = set()

    for entry in entries:
        messages = entry.get("messages", [])
        user_msg = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_msg = msg["content"].strip().lower()
                break
        if not user_msg:
            continue

        # Exact dedup
        if user_msg in exact_seen:
            continue

        # Fuzzy dedup via character 3-gram Jaccard
        ngrams = _char_ngrams(user_msg)
        is_dup = False
        for seen_ngrams, _ in seen_questions:
            if _jaccard_similarity(ngrams, seen_ngrams) >= similarity_threshold:
                is_dup = True
                break

        if not is_dup:
            exact_seen.add(user_msg)
            seen_questions.append((ngrams, entry))
            unique.append(entry)

    logger.info(f"Deduplication: {len(entries)} -> {len(unique)} entries "
                f"(threshold={similarity_threshold})")
    return unique


def format_qa_messages(
    question: str,
    answer: str,
    source_id: str,
    category: str,
    system_prompt: str = SYSTEM_PROMPT,
) -> dict:
    """Format QA into messages format."""
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ],
        "meta": {
            "source_id": source_id,
            "category": category,
        },
    }


def format_multi_turn_messages(
    turns: list,
    source_id: str,
    category: str,
    system_prompt: str = SYSTEM_PROMPT,
) -> dict:
    """Format multi-turn conversation into messages format."""
    messages = [{"role": "system", "content": system_prompt}]
    for turn in turns:
        if "user" in turn:
            messages.append({"role": "user", "content": turn["user"]})
        if "assistant" in turn:
            messages.append({"role": "assistant", "content": turn["assistant"]})
    return {
        "messages": messages,
        "meta": {
            "source_id": source_id,
            "category": category,
        },
    }
