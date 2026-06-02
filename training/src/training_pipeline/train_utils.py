"""QLoRA training utilities using Unsloth."""
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def load_train_config(yaml_path: str) -> dict:
    """Load training config from YAML file."""
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        logger.warning("Config not found: %s, using defaults", yaml_path)
        return {}
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def train(cfg: dict, dry_run: bool = True) -> None:
    """Run QLoRA training using Unsloth."""
    from .gpu_utils import log_gpu_info, estimate_qlora_vram_gb

    model_cfg = cfg.get("model", {})
    data_cfg = cfg.get("data", {})
    train_cfg = cfg.get("training", {})
    lora_cfg = cfg.get("lora", {})

    model_path = model_cfg.get("model_name_or_path", "models/Qwen3.5-9B")
    max_seq_length = data_cfg.get("max_seq_length", 1024)
    train_file = data_cfg.get("train_file", "data/processed/campus_sft_train.jsonl")
    output_dir = train_cfg.get("output_dir", "saves/lora/qwen35_9b_campus_lora")

    gpu_info = log_gpu_info()
    vram_est = estimate_qlora_vram_gb(9.0 if "9B" in model_path else 4.0)
    logger.info("Estimated VRAM: %s", vram_est)

    if dry_run:
        logger.info("=" * 60)
        logger.info("[DRY RUN] Unsloth QLoRA Training Config:")
        logger.info("  Model: %s", model_path)
        logger.info("  Max seq length: %s", max_seq_length)
        logger.info("  Train file: %s", train_file)
        logger.info("  Output dir: %s", output_dir)
        logger.info("  LoRA r=%s, alpha=%s", lora_cfg.get("r", 8), lora_cfg.get("alpha", 16))
        logger.info("=" * 60)
        logger.info("[DRY RUN] To train, run with --do-train")
        return

    from unsloth import FastLanguageModel
    from datasets import load_dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments

    logger.info("Loading model with Unsloth: %s", model_path)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
        dtype=None,
    )

    logger.info("Adding LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_cfg.get("r", 8),
        lora_alpha=lora_cfg.get("alpha", 16),
        lora_dropout=lora_cfg.get("dropout", 0.05),
        target_modules=lora_cfg.get("target_modules", [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ]),
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    logger.info("Loading dataset: %s", train_file)
    dataset = load_dataset("json", data_files=train_file, split="train")

    def format_messages(examples):
        texts = []
        for messages in examples.get("messages", []):
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(format_messages, batched=True)

    valid_file = data_cfg.get("validation_file")
    eval_dataset = None
    if valid_file and Path(valid_file).exists() and Path(valid_file).stat().st_size > 10:
        try:
            eval_dataset = load_dataset("json", data_files=valid_file, split="train")
            if len(eval_dataset) > 0:
                eval_dataset = eval_dataset.map(format_messages, batched=True)
            else:
                eval_dataset = None
        except Exception:
            eval_dataset = None

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=train_cfg.get("per_device_train_batch_size", 1),
        gradient_accumulation_steps=train_cfg.get("gradient_accumulation_steps", 16),
        num_train_epochs=train_cfg.get("num_train_epochs", 2),
        learning_rate=train_cfg.get("learning_rate", 2e-4),
        lr_scheduler_type=train_cfg.get("lr_scheduler_type", "cosine"),
        warmup_ratio=train_cfg.get("warmup_ratio", 0.1),
        logging_steps=train_cfg.get("logging_steps", 10),
        save_steps=train_cfg.get("save_steps", 100),
        bf16=True,
        fp16=False,
        optim="adamw_8bit",
        seed=train_cfg.get("seed", 42),
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        args=args,
    )

    logger.info("Starting Unsloth QLoRA training...")
    from .gpu_utils import get_peak_vram_mb, reset_peak_vram
    reset_peak_vram()

    try:
        trainer.train()
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            peak = get_peak_vram_mb()
            logger.error("OOM at peak VRAM: %.0f MB", peak)
        raise

    peak = get_peak_vram_mb()
    logger.info("Training complete. Peak VRAM: %.0f MB", peak)

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info("LoRA adapter saved to %s", output_dir)
