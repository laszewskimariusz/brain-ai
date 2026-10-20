import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/brain-core"


def frontmatter(path):
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, f"{path} has no frontmatter"
    fields = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", m.group(1), re.M))
    return fields, m.group(2), text


def json_block_after(text, heading):
    """First ```json block after a markdown heading."""
    return json.loads(text.split(heading, 1)[1].split("```json", 1)[1].split("```", 1)[0])


@pytest.fixture
def load_json():
    return lambda p: json.loads((ROOT / p).read_text())
