"""Vault wikilinks become a bounded serial graph."""

import json
from pathlib import Path

from cursor_agent_beacon.obsidian_graph import build_vault_graph


def test_color_groups_follow_graph_json(tmp_path: Path):
    notes = tmp_path / "Notes"
    work = tmp_path / "Work"
    notes.mkdir()
    work.mkdir()
    (notes / "a.md").write_text("See [[b]].", encoding="utf-8")
    (work / "b.md").write_text("x", encoding="utf-8")
    obsidian = tmp_path / ".obsidian"
    obsidian.mkdir()
    (obsidian / "graph.json").write_text(
        json.dumps(
            {
                "colorGroups": [
                    {"query": "path:Notes", "color": {"rgb": 111}},
                    {"query": "path:Work", "color": {"rgb": 222}},
                ]
            }
        ),
        encoding="utf-8",
    )

    graph = build_vault_graph(tmp_path)
    colors = {node.label: node.color for node in graph.nodes}

    assert colors["a"] == 111
    assert colors["b"] == 222
    lines = "\n".join(graph.serial_lines())
    assert "|00006F|" in lines
    assert "|0000DE|" in lines


def test_wikilink_becomes_an_edge(tmp_path: Path):
    (tmp_path / "alpha.md").write_text("See [[beta]] today.", encoding="utf-8")
    (tmp_path / "beta.md").write_text("Alone.", encoding="utf-8")

    graph = build_vault_graph(tmp_path)
    lines = graph.serial_lines()

    assert lines[0] == "GRAPH|BEGIN|2|1"
    assert lines[-1] == "GRAPH|END"
    assert any(line.startswith("GRAPH|E|") for line in lines)
    assert {node.label for node in graph.nodes} == {"alpha", "beta"}
    assert all(0 <= node.x <= 1000 and 0 <= node.y <= 1000 for node in graph.nodes)


def test_graph_keeps_the_busiest_notes(tmp_path: Path):
    hub = tmp_path / "hub.md"
    hub.write_text(
        "\n".join(f"[[n{index}]]" for index in range(90)),
        encoding="utf-8",
    )
    for index in range(90):
        (tmp_path / f"n{index}.md").write_text("x", encoding="utf-8")

    graph = build_vault_graph(tmp_path)

    assert len(graph.nodes) == 80
    assert len(graph.edges) <= 160
    assert "hub" in {node.label for node in graph.nodes}
