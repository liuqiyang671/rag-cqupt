"""LoRA merge utilities (Unsloth-based)."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def merge_lora(
    base_model_path: str,
    lora_adapter_path: str,
    output_dir: str,
    torch_dtype: str = "bfloat16",
    trust_remote_code: bool = True,
    dry_run: bool = True,
) -> Path:
    """Merge LoRA adapter into base model using Unsloth."""
    output_dir = Path(output_dir)

    if dry_run:
        logger.info("[DRY RUN] Would merge LoRA:")
        logger.info("  Base: %s", base_model_path)
        logger.info("  LoRA: %s", lora_adapter_path)
        logger.info("  Output: %s", output_dir)
        return output_dir

    from unsloth import FastLanguageModel

    logger.info("Loading model + LoRA...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=lora_adapter_path,
        max_seq_length=2048,
        load_in_4bit=False,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Saving merged model to %s", output_dir)
    model.save_pretrained_merged(str(output_dir), tokenizer, save_method="merged_16bit")
    logger.info("Merge complete: %s", output_dir)
    return output_dir
