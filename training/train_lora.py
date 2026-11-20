"""
Specialized Small LM (7B–32B) QLoRA SFT + Adversarial DPO Training Skeleton
===========================================================================
Trains an open-weights mathematical/code LLM (e.g. Qwen2.5-Math-7B-Instruct,
Qwen2.5-14B-Instruct, Qwen2.5-32B-Instruct, or DeepSeek-Prover-V1.5) on:
  Stage 1 (SFT): Literal Lean 4 InfoTree -> Faithful LaTeX + Justification JSON
  Stage 2 (DPO): Adversarial & Human-in-the-Loop preference pairs penalizing
                 semantic drift, dropped hypotheses, and opaque-tactic handwaving.

Install optional training dependencies:
  uv pip install -e "backend[training]"

Dry-run config validation (no GPU required):
  python training/train_lora.py --config training/configs/qwen25_14b_qlora.yaml --dry-run
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_yaml_simple(path: Path) -> dict:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        # Minimal fallback parser for simple key: value YAML during dry runs
        cfg: dict = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            clean = line.split("#")[0].strip()
            if ":" in clean:
                k, v = clean.split(":", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
        return cfg


def run_training(config_path: Path, stage: str, dry_run: bool) -> None:
    cfg = load_yaml_simple(config_path)
    print(f"[LIT Trainer] Loaded config: {config_path}")
    print(json.dumps(cfg, indent=2))

    if dry_run:
        print(f"[LIT Trainer] Dry-run OK for stage='{stage}'. Ready for GPU execution.")
        return

    try:
        import torch  # type: ignore
        from datasets import load_dataset  # type: ignore
        from peft import LoraConfig  # type: ignore
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # type: ignore
        from trl import DPOConfig, DPOTrainer, SFTConfig, SFTTrainer  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            f"Missing training dependency ({exc}). Install with: uv pip install -e 'backend[training]'"
        ) from exc

    base_model = cfg["base_model"]
    output_dir = Path(cfg["output_dir"]) / stage
    output_dir.mkdir(parents=True, exist_ok=True)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=bool(cfg.get("load_in_4bit", True)),
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    peft_config = LoraConfig(
        r=int(cfg.get("lora_r", 32)),
        lora_alpha=int(cfg.get("lora_alpha", 64)),
        lora_dropout=float(cfg.get("lora_dropout", 0.05)),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    if stage == "sft":
        ds = load_dataset("json", data_files=cfg["sft_dataset"], split="train")
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=ds,
            peft_config=peft_config,
            args=SFTConfig(
                output_dir=str(output_dir),
                num_train_epochs=int(cfg.get("epochs", 3)),
                per_device_train_batch_size=int(cfg.get("batch_size", 2)),
                gradient_accumulation_steps=int(cfg.get("grad_accum", 8)),
                learning_rate=float(cfg.get("learning_rate", 2e-4)),
                bf16=True,
                logging_steps=10,
                save_strategy="epoch",
            ),
        )
        trainer.train()
        trainer.save_model(str(output_dir))
    elif stage == "dpo":
        ds = load_dataset("json", data_files=cfg["dpo_dataset"], split="train")
        trainer = DPOTrainer(
            model=model,
            ref_model=None,
            processing_class=tokenizer,
            train_dataset=ds,
            peft_config=peft_config,
            args=DPOConfig(
                output_dir=str(output_dir),
                beta=float(cfg.get("dpo_beta", 0.1)),
                num_train_epochs=int(cfg.get("dpo_epochs", 2)),
                per_device_train_batch_size=1,
                gradient_accumulation_steps=8,
                learning_rate=float(cfg.get("dpo_lr", 5e-5)),
                bf16=True,
                logging_steps=10,
            ),
        )
        trainer.train()
        trainer.save_model(str(output_dir))
    else:
        raise ValueError(f"Unknown stage '{stage}'; expected 'sft' or 'dpo'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a specialized small LM for Lost In Translation.")
    parser.add_argument("--config", required=True, help="Path to YAML training configuration.")
    parser.add_argument("--stage", choices=["sft", "dpo"], default="sft")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without loading GPU weights.")
    args = parser.parse_args()
    run_training(Path(args.config), args.stage, args.dry_run)


if __name__ == "__main__":
    main()
