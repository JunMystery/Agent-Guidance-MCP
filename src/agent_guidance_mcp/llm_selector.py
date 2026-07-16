"""Small LLM-based skill selector for task-driven skill recommendations.

Two-stage approach:
  1. Embedding search narrows 168 catalog → ~20 candidates
  2. Qwen2.5-0.5B-Instruct receives candidates + task → picks top N

Falls back to embedding ranking if LLM unavailable.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import Any

logger = logging.getLogger("agent-guidance-mcp.llm-selector")

_LLM_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
_DEFAULT_CANDIDATES = 20
_DEFAULT_LIMIT = 3


class LLMSelector:
    """Lazy-loaded small LLM that selects skills from a candidate list."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or os.environ.get("AGENT_SKILL_LLM", _LLM_MODEL)
        self._tokenizer: Any = None
        self._model: Any = None
        self._loaded = False

    def _load(self) -> None:
        """Load tokenizer and model on first use."""
        if self._loaded:
            return
        if os.environ.get("AGENT_SKILL_LLM") == "" or "pytest" in sys.modules:
            return
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            logger.info("loading LLM skill selector: %s", self._model_name)
            local_files_only = _model_already_cached(self._model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_name,
                local_files_only=local_files_only,
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_name,
                torch_dtype="auto",
                device_map="auto",
                local_files_only=local_files_only,
            )
            self._loaded = True
            logger.info("LLM skill selector loaded (local_files_only=%s)", local_files_only)
        except Exception as e:
            logger.warning("failed to load LLM skill selector: %s", e)
            self._loaded = False

    def _build_prompt(self, task: str, candidates: list[dict[str, str]], limit: int) -> str:
        """Build a chat-style prompt for skill selection."""
        entries_text = "\n".join(
            f"- {c['identifier']}: {c.get('title', '')} — {c.get('description', '')}"
            for c in candidates
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a skill selector for an AI coding assistant. "
                    "Given a task and a list of available skills, pick the "
                    f"{limit} most relevant skills. "
                    "Respond with ONLY the skill identifiers, one per line. "
                    "Do not explain. Do not add extra text."
                ),
            },
            {
                "role": "user",
                "content": f"Task: {task}\n\nAvailable skills:\n{entries_text}",
            },
        ]
        try:
            prompt = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            prompt = f"Task: {task}\n\nSkills:\n{entries_text}\n\nSelected:"
        return prompt

    def _parse_skills(self, text: str, candidates: list[dict[str, str]]) -> list[str]:
        """Extract skill identifiers from LLM output."""
        found: list[str] = []
        candidate_ids = {c["identifier"] for c in candidates}
        for line in text.strip().split("\n"):
            line = line.strip().strip("-*").strip()
            if line in candidate_ids and line not in found:
                found.append(line)
        return found

    def select(
        self,
        task: str,
        candidates: list[dict[str, str]],
        limit: int = _DEFAULT_LIMIT,
    ) -> list[str]:
        """Select top N skill identifiers from candidates using LLM.

        Returns empty list if LLM unavailable or fails (caller falls back).
        """
        self._load()
        if not self._loaded or self._model is None or self._tokenizer is None:
            return []

        try:
            import time as _time

            _t0 = _time.time()
            prompt = self._build_prompt(task, candidates, limit)
            inputs = self._tokenizer(prompt, return_tensors="pt")
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=128,
                temperature=0.1,
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )
            response = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Strip the input prompt from the response
            if prompt in response:
                response = response[len(prompt):].strip()
            picks = self._parse_skills(response, candidates)
            _dt_ms = int((_time.time() - _t0) * 1000)
            try:
                from .server import get_usage

                _u = get_usage()
                if _u is not None:
                    _u.record_llm_query(
                        query_text=task,
                        model_name=self._model_name,
                        duration_ms=_dt_ms,
                        result_count=len(picks),
                    )
            except Exception:
                pass
            return picks
        except Exception as e:
            logger.warning("LLM skill selection failed: %s", e)
            return []


def _model_already_cached(repo_id: str) -> bool:
    """Return True if a model repo is fully present in the local HF hub cache.

    Lets pre_download_llm() skip the heavy in-memory load when the weights are
    already on disk (re-run of the installer / `--update`).
    """
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id, local_files_only=True)
        return True
    except Exception:
        return False


def pre_download_llm() -> bool:
    """Pre-download the LLM model so first task_pipeline call is fast.

    Skips the in-memory load when the model is already cached, avoiding a
    redundant heavyweight load on a re-run of `--update` / the installer.
    """
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM  # noqa: F401
    except ImportError:
        logger.warning(
            "The 'transformers' package is not installed. "
            "LLM skill selector will fall back to embedding ranking."
        )
        return False
    model = os.environ.get("AGENT_SKILL_LLM", _LLM_MODEL)
    if _model_already_cached(model):
        logger.info("LLM model already cached, skipping load: %s", model)
        return True
    AutoTokenizer.from_pretrained(model)
    AutoModelForCausalLM.from_pretrained(model, torch_dtype="auto", device_map="auto")
    return True
