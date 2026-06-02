"""Results comparison and report generation."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


logger = logging.getLogger(__name__)


def load_json_results(path: Path) -> Optional[dict]:
    """Load JSON results file if it exists."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_all_results(outputs_dir: Path) -> dict:
    """Load all evaluation results from outputs directory."""
    results = {}
    mmlu_base = load_json_results(outputs_dir / "mmlu_base" / "mmlu_pro_results.json")
    mmlu_ft = load_json_results(outputs_dir / "mmlu_finetuned" / "mmlu_pro_results.json")
    results["mmlu_base"] = mmlu_base
    results["mmlu_finetuned"] = mmlu_ft
    campus_base = load_json_results(outputs_dir / "campus_eval_base" / "campus_eval_results.json")
    campus_ft = load_json_results(outputs_dir / "campus_eval_finetuned" / "campus_eval_results.json")
    results["campus_base"] = campus_base
    results["campus_finetuned"] = campus_ft
    return results


def generate_markdown_report(results: dict) -> str:
    """Generate a Markdown comparison report."""
    lines = []
    lines.append("# 微调效果对比报告")
    lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append("## 1. MMLU-Pro 通用能力评测\n")
    mmlu_base = results.get("mmlu_base")
    mmlu_ft = results.get("mmlu_finetuned")

    if mmlu_base or mmlu_ft:
        lines.append("| 模型 | 准确率 | 评测时间(s) | 样本数 |")
        lines.append("|------|--------|-------------|--------|")
        if mmlu_base:
            acc = mmlu_base.get("accuracy", "N/A")
            t = mmlu_base.get("eval_time_seconds", "N/A")
            limit = mmlu_base.get("limit", "N/A")
            lines.append(f"| 基座模型 | {acc} | {t} | {limit} |")
        if mmlu_ft:
            acc = mmlu_ft.get("accuracy", "N/A")
            t = mmlu_ft.get("eval_time_seconds", "N/A")
            limit = mmlu_ft.get("limit", "N/A")
            lines.append(f"| 微调后 | {acc} | {t} | {limit} |")
        if mmlu_base and mmlu_ft:
            base_acc = mmlu_base.get("accuracy", 0)
            ft_acc = mmlu_ft.get("accuracy", 0)
            if base_acc and ft_acc:
                diff = ft_acc - base_acc
                lines.append(f"\n**通用能力变化: {diff:+.4f}**")
                if diff < -0.05:
                    lines.append("> ⚠️ 通用能力出现显著下降 (>5%)，建议降低学习率或增加通用数据比例")
                elif diff < 0:
                    lines.append("> ⚠️ 通用能力略有下降 (<5%)，属于正常微调范围")
                else:
                    lines.append("> ✅ 通用能力未下降")
    else:
        lines.append("暂无 MMLU-Pro 评测数据。")


    lines.append("## 2. 校园问答能力评测\n")
    campus_base = results.get("campus_base")
    campus_ft = results.get("campus_finetuned")

    if campus_base or campus_ft:
        lines.append("| 模型 | Exact Match | Keyword Hit Rate | ROUGE-L |")
        lines.append("|------|-------------|------------------|---------|")
        if campus_base:
            em = campus_base.get("exact_match", "N/A")
            kh = campus_base.get("keyword_hit_rate", "N/A")
            rl = campus_base.get("rougeL", "N/A")
            lines.append(f"| 基座模型 | {em} | {kh} | {rl} |")
        if campus_ft:
            em = campus_ft.get("exact_match", "N/A")
            kh = campus_ft.get("keyword_hit_rate", "N/A")
            rl = campus_ft.get("rougeL", "N/A")
            lines.append(f"| 微调后 | {em} | {kh} | {rl} |")
        if campus_base and campus_ft:
            base_em = campus_base.get("exact_match", 0)
            ft_em = campus_ft.get("exact_match", 0)
            if base_em is not None and ft_em is not None:
                diff = ft_em - base_em
                lines.append(f"\n**校园问答 Exact Match 变化: {diff:+.4f}**")
                if diff > 0.05:
                    lines.append("> ✅ 校园问答能力显著提升 (>5%)")
                elif diff > 0:
                    lines.append("> ✅ 校园问答能力有所提升")
                else:
                    lines.append("> ⚠️ 校园问答能力未见提升，建议检查训练数据质量或增加训练轮数")
    else:
        lines.append("暂无校园问答评测数据。")


    lines.append("\n## 3. 总结与建议\n")
    lines.append("### 通用能力 vs 专项能力\n")
    lines.append("| 评测 | 基座 | 微调后 | 变化 | 状态 |")
    lines.append("|------|------|--------|------|------|")

    if mmlu_base and mmlu_ft:
        mb = mmlu_base.get("accuracy", 0)
        mf = mmlu_ft.get("accuracy", 0)
        if mb and mf:
            md = mf - mb
            status = "✅" if md >= 0 else "⚠️"
            lines.append(f"| MMLU-Pro | {mb:.4f} | {mf:.4f} | {md:+.4f} | {status} |")

    if campus_base and campus_ft:
        cb = campus_base.get("exact_match", 0)
        cf = campus_ft.get("exact_match", 0)
        if cb is not None and cf is not None:
            cd = cf - cb
            status = "✅" if cd > 0 else "⚠️"
            lines.append(f"| 校园QA | {cb:.4f} | {cf:.4f} | {cd:+.4f} | {status} |")

    lines.append("\n### 后续建议\n")
    lines.append("1. 如果通用能力下降明显，可以降低学习率 (1e-4 或 5e-5)")
    lines.append("2. 如果专项能力提升不明显，可以增加训练轮数或数据量")
    lines.append("3. 如果出现 OOM，降低 max_seq_length 或切换到 Qwen3.5-4B")
    lines.append("4. 建议使用 LLM Judge 对回答质量做更细致的评估")

    return "\n".join(lines)


def generate_comparison_report(outputs_dir: Path, reports_dir: Path) -> dict:
    """Generate comparison report in Markdown and JSON formats.

    Args:
        outputs_dir: Directory containing evaluation outputs
        reports_dir: Directory to save reports

    Returns:
        Dict with report paths and summary
    """
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    results = load_all_results(Path(outputs_dir))

    md_report = generate_markdown_report(results)
    md_path = reports_dir / "compare_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    logger.info(f"Markdown report saved to {md_path}")

    json_report = {
        "generated_at": datetime.now().isoformat(),
        "results": results,
    }
    json_path = reports_dir / "compare_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    logger.info(f"JSON report saved to {json_path}")

    return {
        "markdown_path": str(md_path),
        "json_path": str(json_path),
        "results": results,
    }
