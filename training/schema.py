"""
Dataset schemas for Lost In Translation fine-tuning (SFT + DPO/ORPO).

Our central thesis:
  Generic frontier LLMs are RLHF-trained to be "helpful" and fluent, which causes them
  to smooth over gaps, silently invent justifications, drop domain constraints (like ℕ
  truncated subtraction or positivity preconditions), or misrepresent opaque tactics.
  Instead, Lost In Translation trains specialized open-weights small LMs (7B–32B) on
  literal InfoTree-grounded pairs plus adversarial negatives harvested from HITL flagging.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass
class SFTExample:
    messages: list[dict[str, str]]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DPOPreferenceExample:
    prompt: str
    chosen: str
    rejected: str
    perturbation_type: Literal[
        "human_hitl_correction",
        "dropped_hypothesis",
        "quantifier_flip",
        "hidden_opaque_leap",
        "domain_coercion_error",
        "hallucinated_sorry_fill",
    ]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
