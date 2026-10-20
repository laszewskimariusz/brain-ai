import re

from conftest import PLUGIN, frontmatter

AGENTS = PLUGIN / "agents"
EXPECTED = {"architect": "opus", "developer": "sonnet", "reviewer": "sonnet", "security": "sonnet",
            "devops": "sonnet", "designer": "sonnet", "researcher": "sonnet"}
READ_ONLY = {"reviewer", "security", "researcher"}
SECTIONS = ("## Procedure", "## Hard rules", "## Done when", "## Report")


def test_expected_role_agents_with_pinned_models():
    assert {p.stem for p in AGENTS.glob("*.md")} == set(EXPECTED)
    for name, model in EXPECTED.items():
        fields, body, text = frontmatter(AGENTS / f"{name}.md")
        assert fields["name"] == name and fields["model"] == model, name
        assert fields.get("tools"), name
        assert 40 <= len(fields["description"]) <= 300, name
        assert len(text.splitlines()) <= 120, name
        for section in SECTIONS:
            assert section in body, (name, section)


def test_read_only_agents_cannot_write():
    for name in READ_ONLY:
        tools = frontmatter(AGENTS / f"{name}.md")[0]["tools"]
        assert not re.search(r"\b(Edit|Write|MultiEdit|NotebookEdit)\b", tools), name


def test_no_personas():
    for p in AGENTS.glob("*.md"):
        assert not re.search(r"(?i)\b(personality|persona|you are a (?:friendly|cheerful))\b", p.read_text()), p


def test_hook_enforces_read_only_for_the_same_agents():
    from test_protected_paths import sg
    assert sg.READ_ONLY_AGENTS == READ_ONLY


def test_readme_says_read_only_is_enforced():
    readme = (PLUGIN.parents[1] / "README.md").read_text()
    for name in READ_ONLY:
        row = next(line for line in readme.splitlines() if line.startswith(f"| `{name}` |"))
        assert "read-only (tool list + hook)" in row, name
    # the Bash check is pattern-based: docs must not sell it as a hard guarantee
    assert "best-effort" in readme
    assert "read-only by enforcement" not in (PLUGIN.parents[1] / "CHANGELOG.md").read_text()
