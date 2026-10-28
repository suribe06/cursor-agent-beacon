"""Vault wikilinks become a bounded serial graph."""

from cursor_agent_beacon.obsidian_graph import build_vault_graph


def test_wikilink_becomes_an_edge(tmp_path):
    (tmp_path / "alpha.md").write_text("See [[beta]] today.", encoding="utf-8")
    (tmp_path / "beta.md").write_text("Alone.", encoding="utf-8")

    graph = build_vault_graph(tmp_path)
    lines = graph.serial_lines()

    assert lines[0] == "GRAPH|BEGIN|2|1"
    assert lines[-1] == "GRAPH|END"
    assert any(line.startswith("GRAPH|E|") for line in lines)
    assert {node.label for node in graph.nodes} == {"alpha", "beta"}
    assert all(0 <= node.x <= 1000 and 0 <= node.y <= 1000 for node in graph.nodes)


def test_graph_keeps_the_busiest_notes(tmp_path):
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
