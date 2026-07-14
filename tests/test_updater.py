import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

import agent_guidance_mcp.updater as updater


def test_updater_skips_when_commit_matches(tmp_path, monkeypatch):
    state_file = tmp_path / "update-state.json"
    monkeypatch.setattr(updater, "_STATE_FILE", state_file)

    dest_root = tmp_path / ".agent-guidance"
    dest_root.mkdir()

    for repo_info in updater.UPDATER_REPOS.values():
        (dest_root / repo_info["check_dir"]).parent.mkdir(parents=True, exist_ok=True)
        (dest_root / repo_info["check_dir"]).mkdir(parents=True, exist_ok=True)

    initial_state = {
        "last_update": "2026-07-14T00:00:00",
        "server_version": "1.0.0",
        "commits": {
            "ecc": "sha123_ecc",
            "ui_ux": "sha123_ui_ux",
            "anthropic": "sha123_anth",
            "owasp": "sha123_owasp",
            "system_design": "sha123_sys",
        }
    }
    state_file.write_text(json.dumps(initial_state), encoding="utf-8")

    mock_get_sha = MagicMock(side_effect=lambda owner, repo, branch: {
        "ECC": "sha123_ecc",
        "ui-ux-pro-max-skill": "sha123_ui_ux",
        "skills": "sha123_anth",
        "CheatSheetSeries": "sha123_owasp",
        "system-design-primer": "sha123_sys"
    }.get(repo))
    monkeypatch.setattr(updater, "_get_latest_commit_sha", mock_get_sha)

    mock_updates = {}
    for key, info in updater.UPDATER_REPOS.items():
        mock_fn = MagicMock(return_value=True)
        mock_updates[key] = mock_fn
        monkeypatch.setitem(updater.UPDATER_REPOS[key], "update_fn", mock_fn)

    mock_exit = MagicMock()
    monkeypatch.setattr("sys.exit", mock_exit)
    monkeypatch.setattr("agent_guidance_mcp.embeddings.pre_download_models", MagicMock(return_value=True))
    monkeypatch.setattr("pathlib.Path.home", MagicMock(return_value=tmp_path))

    updater.run_update()

    for key, mock_fn in mock_updates.items():
        assert mock_fn.call_count == 0

    mock_exit.assert_called_once_with(0)


def test_updater_updates_when_commit_mismatches_or_missing(tmp_path, monkeypatch):
    state_file = tmp_path / "update-state.json"
    monkeypatch.setattr(updater, "_STATE_FILE", state_file)

    dest_root = tmp_path / ".agent-guidance"
    dest_root.mkdir()

    initial_state = {
        "last_update": "2026-07-14T00:00:00",
        "server_version": "1.0.0",
        "commits": {
            "ecc": "old_ecc",
        }
    }
    state_file.write_text(json.dumps(initial_state), encoding="utf-8")

    mock_get_sha = MagicMock(side_effect=lambda owner, repo, branch: {
        "ECC": "new_ecc",
        "ui-ux-pro-max-skill": "new_ui_ux",
        "skills": "new_anth",
        "CheatSheetSeries": "new_owasp",
        "system-design-primer": "new_sys"
    }.get(repo))
    monkeypatch.setattr(updater, "_get_latest_commit_sha", mock_get_sha)

    mock_updates = {}
    for key, info in updater.UPDATER_REPOS.items():
        mock_fn = MagicMock(return_value=True)
        mock_updates[key] = mock_fn
        monkeypatch.setitem(updater.UPDATER_REPOS[key], "update_fn", mock_fn)

    mock_exit = MagicMock()
    monkeypatch.setattr("sys.exit", mock_exit)
    monkeypatch.setattr("agent_guidance_mcp.embeddings.pre_download_models", MagicMock(return_value=True))
    monkeypatch.setattr("pathlib.Path.home", MagicMock(return_value=tmp_path))

    updater.run_update()

    for key, mock_fn in mock_updates.items():
        assert mock_fn.call_count == 1

    new_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert new_state["commits"]["ecc"] == "new_ecc"
    assert new_state["commits"]["ui_ux"] == "new_ui_ux"
