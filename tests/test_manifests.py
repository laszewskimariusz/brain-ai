import re

from conftest import PLUGIN


def test_marketplace_lists_brain_core_with_relative_source(load_json):
    mp = load_json(".claude-plugin/marketplace.json")
    assert mp["name"] == "brain-ai"
    core = [p for p in mp["plugins"] if p["name"] == "brain-core"]
    assert len(core) == 1 and core[0]["source"] == "./plugins/brain-core"
    assert "version" not in core[0]  # the version lives only in plugin.json


def test_plugin_json_version_and_hook(load_json):
    pj = load_json("plugins/brain-core/.claude-plugin/plugin.json")
    assert pj["name"] == "brain-core" and pj["version"] == "4.0.1"
    hooks = pj["hooks"]["PreToolUse"]
    commands = [h["command"] for entry in hooks for h in entry["hooks"]]
    assert any("${CLAUDE_PLUGIN_ROOT}/hooks/secret_guard.py" in c for c in commands)
    assert (PLUGIN / "hooks/secret_guard.py").is_file()
    matcher = hooks[0]["matcher"]
    for tool in ("Write", "Edit", "MultiEdit", "Read", "Grep", "Bash"):
        assert re.search(rf"\b{tool}\b", matcher), tool
