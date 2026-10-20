import json

import yaml

from conftest import PLUGIN, ROOT, json_block_after

KIT = ROOT / "project-kit"
BRAIN = ROOT / "brain-template"


def test_project_kit_settings_enable_existing_plugin():
    cfg = json.loads((KIT / ".claude/settings.json").read_text())
    mp = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    (key,) = cfg["enabledPlugins"]
    plugin, market = key.split("@")
    assert market == mp["name"] and plugin in {p["name"] for p in mp["plugins"]}
    assert cfg["extraKnownMarketplaces"][market]["source"] == {"source": "github", "repo": "laszewskimariusz/brain-ai"}


def test_project_kit_matches_project_init_template():
    kit = json.loads((KIT / ".claude/settings.json").read_text())
    tmpl = json_block_after((PLUGIN / "skills/project-init/SKILL.md").read_text(), "## Template: .claude/settings.json")
    assert kit == tmpl


def test_project_kit_claude_md_is_short():
    assert len((KIT / "CLAUDE.md").read_text().splitlines()) <= 100


def test_brain_claude_md_under_2kb():
    assert len((BRAIN / "CLAUDE.md").read_bytes()) < 2048


def test_brain_folders_exist_with_readme():
    for d in ("decisions", "knowledge", "infra"):
        assert (BRAIN / d / "README.md").is_file(), d


def test_portfolio_entries_have_required_fields():
    projects = yaml.safe_load((BRAIN / "portfolio.yaml").read_text())["projects"]
    stages = {"idea", "build", "live", "maintain", "archived"}
    for p in projects:
        assert {"slug", "name", "stage", "repo"} <= p.keys(), p
        assert p["stage"] in stages, p


def test_project_kit_turns_the_bash_sandbox_on():
    cfg = json.loads((KIT / ".claude/settings.json").read_text())
    assert cfg["sandbox"]["enabled"] is True
    assert cfg["sandbox"]["filesystem"]["denyRead"]
