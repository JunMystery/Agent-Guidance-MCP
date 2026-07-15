"""Tests for cache-aware model pre-download skip behavior.

Verifies that pre_download_models() / pre_download_llm() skip the heavy
in-memory model load when the weights are already in the local HF hub cache
(the requested "skip downloading LLMs when they exist" behavior).

Skipped when the optional deps (huggingface_hub / transformers) are not
installed, mirroring the project's optional ML dependency model.
"""
import pytest

pytest.importorskip("huggingface_hub")


def _patch_cache(monkeypatch, present: bool) -> None:
    import huggingface_hub

    if present:
        monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda *a, **k: "/cached")
    else:
        def boom(*a, **k):
            raise huggingface_hub.LocalEntryNotFoundError("not cached")

        monkeypatch.setattr(huggingface_hub, "snapshot_download", boom)


def test_e5_cache_probe(monkeypatch):
    from agent_guidance_mcp import embeddings

    _patch_cache(monkeypatch, present=True)
    assert embeddings._model_already_cached(embeddings._E5_MODEL) is True

    _patch_cache(monkeypatch, present=False)
    assert embeddings._model_already_cached(embeddings._E5_MODEL) is False


def test_llm_cache_probe(monkeypatch):
    from agent_guidance_mcp import llm_selector

    _patch_cache(monkeypatch, present=True)
    assert llm_selector._model_already_cached(llm_selector._LLM_MODEL) is True

    _patch_cache(monkeypatch, present=False)
    assert llm_selector._model_already_cached(llm_selector._LLM_MODEL) is False


def test_pre_download_llm_skips_load_when_cached(monkeypatch):
    pytest.importorskip("transformers")
    import transformers
    from agent_guidance_mcp import llm_selector

    _patch_cache(monkeypatch, present=True)

    loaded = []

    monkeypatch.setattr(
        transformers,
        "AutoModelForCausalLM",
        type("M", (), {"from_pretrained": staticmethod(lambda *a, **k: loaded.append(1))}),
    )
    monkeypatch.setattr(
        transformers,
        "AutoTokenizer",
        type("T", (), {"from_pretrained": staticmethod(lambda *a, **k: None)}),
    )

    assert llm_selector.pre_download_llm() is True
    assert loaded == [], "heavy model load must be skipped when already cached"
