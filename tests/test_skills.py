import re

from conftest import PLUGIN, frontmatter, json_block_after

SKILLS = PLUGIN / "skills"
NAMES = {"spec", "test-plan", "docs", "project-init"}


def test_skills_present_and_sized():
    assert {p.parent.name for p in SKILLS.glob("*/SKILL.md")} == NAMES
    for p in SKILLS.glob("*/SKILL.md"):
        fields, body, text = frontmatter(p)
        assert fields["name"] == p.parent.name, p
        assert 40 <= len(fields["description"]) <= 1536, p
        assert len(text.splitlines()) <= 500, p


def test_skills_are_self_contained():
    for d in SKILLS.iterdir():
        assert {f.name for f in d.iterdir()} == {"SKILL.md"}, d


def test_project_init_settings_template_enables_plugin_and_denies_secrets():
    text = (SKILLS / "project-init/SKILL.md").read_text()
    assert "## Template: CLAUDE.md" in text
    cfg = json_block_after(text, "## Template: .claude/settings.json")
    assert cfg["enabledPlugins"]["brain-core@brain-ai"] is True
    source = cfg["extraKnownMarketplaces"]["brain-ai"]["source"]
    assert source["repo"] == "laszewskimariusz/brain-ai"
    deny = cfg["permissions"]["deny"]
    assert any(".env" in d for d in deny) and any("printenv" in d for d in deny)


def test_no_secret_values_in_skills():
    for p in SKILLS.glob("*/SKILL.md"):
        t = p.read_text()
        assert not re.search(r"(?i)(token|key|password|secret)\w*\s*=\s*[A-Za-z0-9+/_\-]{12,}", t), p
        assert "PRIVATE KEY" not in t, p
