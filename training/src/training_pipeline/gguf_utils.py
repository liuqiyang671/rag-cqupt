"""GGUF export utilities using Unsloth."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_gguf(
    source_model_path: str,
    output_dir: str,
    llama_cpp_path: str = "llama.cpp",
    f16_output: str = "model_f16.gguf",
    q4km_output: str = "model_q4_k_m.gguf",
    quant_type: str = "Q4_K_M",
    dry_run: bool = True,
) -> dict:
    """Export model to GGUF using Unsloth (no llama.cpp needed)."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        logger.info("[DRY RUN] Would export GGUF:")
        logger.info("  Source: %s", source_model_path)
        logger.info("  Output: %s", out_dir)
        logger.info("  To export, run with --do-export")
        return {"status": "dry_run"}

    from unsloth import FastLanguageModel

    logger.info("Loading model for GGUF export...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=source_model_path,
        max_seq_length=2048,
        load_in_4bit=False,
    )

    logger.info("Exporting Q4_K_M GGUF to %s", out_dir)
    model.save_pretrained_gguf(str(out_dir), tokenizer, quantization_method="q4_k_m")

    gguf_files = list(out_dir.glob("*.gguf"))
    if gguf_files:
        logger.info("GGUF exported: %s", gguf_files)

    return {
        "status": "completed",
        "output_dir": str(out_dir),
        "gguf_files": [str(f) for f in gguf_files],
    }
