import re

from conftest import ROOT

DOCS = ["README.md", "docs/why-v4.md", "docs/architecture.md", "docs/adr/0001-brain-core-projects-plugins.md",
        "docs/migrating-from-v3.md", "CHANGELOG.md"]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def test_expected_documents_exist():
    for d in DOCS:
        assert (ROOT / d).is_file(), d


def test_relative_links_resolve():
    for md in ROOT.rglob("*.md"):
        if ".git" in md.parts or ".pytest_cache" in md.parts:
            continue
        for target in LINK.findall(md.read_text()):
            if re.match(r"^(https?:|mailto:|#)", target):
                continue
            path = (md.parent / target.split("#", 1)[0]).resolve()
            assert path.exists(), f"{md.relative_to(ROOT)} -> {target}"


def test_readme_points_to_v3_and_quick_start():
    t = (ROOT / "README.md").read_text()
    assert "v3.0.0" in t
    assert "/plugin marketplace add laszewskimariusz/brain-ai" in t
    assert "/plugin install brain-core@brain-ai" in t


def test_changelog_has_v4_entry():
    assert re.search(r"^## \[4\.0\.0\] — \d{4}-\d{2}-\d{2}", (ROOT / "CHANGELOG.md").read_text(), re.M)


def test_docs_do_not_promise_per_project_pinning_the_kit_does_not_do():
    # project-kit settings carry no ref, so docs must not claim projects pin a release
    claim = re.compile(r"(?i)pinned per project|pins a release|pinned version|pin a release|pinned plugin")
    for d in DOCS:
        assert not claim.search((ROOT / d).read_text()), d
