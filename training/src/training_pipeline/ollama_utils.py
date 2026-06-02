"""Ollama model creation utilities."""
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def check_ollama_installed() -> bool:
    """Check if ollama CLI is available."""
    return shutil.which("ollama") is not None


def create_ollama_model(
    gguf_path: str,
    model_name: str = "qwen35-campus:9b",
    ollama_dir: str = "saves/ollama",
    dry_run: bool = True,
) -> dict:
    """Create Ollama model from GGUF file.

    Args:
        gguf_path: Path to the GGUF file
        model_name: Ollama model name
        ollama_dir: Directory to store Modelfile
        dry_run: If True, only generate Modelfile

    Returns:
        Dict with status and paths
    """
    gguf_p = Path(gguf_path).resolve()
    ollama_d = Path(ollama_dir)
    ollama_d.mkdir(parents=True, exist_ok=True)

    if not gguf_p.exists():
        logger.error("GGUF file not found: %s", gguf_p)
        return {"status": "error", "message": f"GGUF not found: {gguf_p}"}

    # Build Modelfile
    q = chr(34)
    stop1 = "PARAMETER stop " + q + "<!-->" + q
    stop2 = "PARAMETER stop " + q + "<!--start>" + q

    mf_lines = [
        f"FROM ./{gguf_p.name}",
        "",
        "# Qwen chat template",
        "PARAMETER temperature 0.7",
        "PARAMETER top_p 0.8",
        stop1,
        stop2,
        "",
    ]
    modelfile_content = chr(10).join(mf_lines)
    modelfile_path = ollama_d / "Modelfile"
    with open(modelfile_path, "w", encoding="utf-8") as f:
        f.write(modelfile_content)
    logger.info("Modelfile generated: %s", modelfile_path)

    # Copy GGUF to ollama dir
    gguf_copy = ollama_d / gguf_p.name
    if not gguf_copy.exists():
        if dry_run:
            logger.info("[DRY RUN] Would copy GGUF to %s", gguf_copy)
        else:
            logger.info("Copying GGUF to %s ...", gguf_copy)
            shutil.copy2(str(gguf_p), str(gguf_copy))

    create_cmd = f"ollama create {model_name} -f {modelfile_path}"
    logger.info("Ollama create command: %s", create_cmd)

    if dry_run:
        logger.info("[DRY RUN] Run without --dry-run to create model.")
        return {
            "status": "dry_run",
            "modelfile_path": str(modelfile_path),
            "command": create_cmd,
        }

    if not check_ollama_installed():
        logger.error("Ollama not installed. Download from https://ollama.com/download")
        return {"status": "error", "message": "Ollama not installed"}

    logger.info("Creating Ollama model: %s", model_name)
    result = subprocess.run(
        ["ollama", "create", model_name, "-f", str(modelfile_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        logger.error("ollama create failed: %s", result.stderr)
        return {"status": "error", "message": result.stderr}

    logger.info("Ollama model created: %s", model_name)
    return {"status": "completed", "model_name": model_name, "modelfile_path": str(modelfile_path)}
