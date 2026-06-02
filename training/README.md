# Qwen3.5-9B Campus Q&A Fine-Tuning Pipeline

Fine-tuning pipeline for adapting Qwen3.5-9B into a campus knowledge Q&A assistant using QLoRA (4-bit NF4 + LoRA). Designed for RTX 5060 Ti 16GB.

## Why Hugging Face, Not Ollama for Training

Ollama qwen3.5:9b is a GGUF-quantized inference-only model. It lacks gradient computation, backpropagation, and full-precision weights. It cannot be fine-tuned.

Hugging Face Qwen/Qwen3.5-9B provides full BF16/FP16 weights compatible with PyTorch autograd, native LoRA/QLoRA via PEFT, gradient checkpointing, and proper tokenizer support.

**Correct flow:** HF model download -> QLoRA training -> LoRA merge -> GGUF export -> Ollama deploy

## Pipeline Overview

```
Step 0:  Check Environment        scripts/00_check_env.py
Step 1:  Download HF Model        scripts/01_download_model.py
Step 2:  MMLU-Pro Base Eval       scripts/02_eval_mmlu_pro.py
Step 3:  Generate Campus QA       scripts/03_generate_campus_qa.py
Step 4:  Prepare SFT Dataset      scripts/04_prepare_sft_dataset.py
Step 5:  QLoRA Training           scripts/05_train_qlora.py
Step 6:  LoRA Merge               scripts/06_merge_lora.py
Step 7:  GGUF Export              scripts/07_export_gguf.py
Step 8:  Create Ollama Model      scripts/08_create_ollama_model.py
Step 9:  Campus QA Eval           scripts/09_eval_campus_qa.py
Step 10: Compare Results          scripts/10_compare_results.py
```

## Quick Commands

```bash
python scripts/00_check_env.py
python scripts/run_pipeline.py --stage all
python scripts/run_pipeline.py --stage all --do-train
python scripts/02_eval_mmlu_pro.py --do-eval
```

## Installation

```bash
cd training
pip install -r requirements.txt
cp .env.example .env
```

## Quick Mode vs Full Mode

| Script | Quick | Full |
|--------|-------|------|
| 01_download_model.py | --dry-run | --do-download |
| 02_eval_mmlu_pro.py | limit=100 | --do-eval --full-eval |
| 03_generate_campus_qa.py | --dry-run | --do-generate |
| 05_train_qlora.py | --dry-run | --do-train |
| 06_merge_lora.py | --dry-run | --do-merge |
| 07_export_gguf.py | --dry-run | --do-export |
| 08_create_ollama_model.py | --dry-run | --do-create |
| 09_eval_campus_qa.py | --dry-run | --do-eval |

## RTX 5060 Ti 16GB Recommended Parameters

| Parameter | Value |
|-----------|-------|
| batch_size | 1 |
| gradient_accumulation | 16 |
| max_seq_length | 1024 |
| quantization | 4-bit NF4 |
| double_quant | True |
| gradient_checkpointing | True |
| bf16 | True |
| lora_r | 8 |
| lora_alpha | 16 |
| epochs | 2 |
| learning_rate | 2e-4 |

## Campus Knowledge Base

Place 90 campus KB entries in data/raw/ as JSONL:
```json
{"id": "kb_001", "category": "category", "content": "knowledge text"}
```

See data/raw/campus_kb.example.jsonl for format example.

## Common Errors

**CUDA not available:** pip install torch --index-url https://download.pytorch.org/whl/cu121
**bitsandbytes:** pip install bitsandbytes --upgrade
**OOM:** --max-seq-length 512 or --model-path models/Qwen3.5-4B
**llama.cpp:** git clone https://github.com/ggerganov/llama.cpp
**Ollama:** https://ollama.com/download

## Fallback: Qwen3.5-4B

```bash
python scripts/01_download_model.py --model-id Qwen/Qwen3.5-4B --do-download
python scripts/05_train_qlora.py --do-train --model-path models/Qwen3.5-4B
```