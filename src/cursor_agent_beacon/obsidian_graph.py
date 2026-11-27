"""Obsidian vault → serial graph for the VIEWE vault page.

The panel does not read notes. It draws dots the PC already placed.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

MAX_NODES = 80
MAX_EDGES = 160
LABEL_LIMIT = 16
_DEFAULT_COLOR = 0x94A3B8
_LINK = re.compile(r"\[\[([^\]|#^]+)(?:[#^][^\]|]*)?(?:\|[^\]]*)?\]\]")


@dataclass(frozen=True, slots=True)
class GraphNode:
    label: str
    x: int
    y: int
    deg: int
    color: int = _DEFAULT_COLOR


@dataclass(frozen=True, slots=True)
class VaultGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[tuple[int, int], ...]

    def serial_lines(self) -> list[str]:
        lines = [f"GRAPH|BEGIN|{len(self.nodes)}|{len(self.edges)}"]
        for index, node in enumerate(self.nodes):
            lines.append(
                f"GRAPH|N|{index}|{node.x}|{node.y}|{node.deg}|{node.color:06X}|{node.label}"
            )
        for left, right in self.edges:
            lines.append(f"GRAPH|E|{left}|{right}")
        lines.append("GRAPH|END")
        return lines


def _notes(vault: Path) -> list[Path]:
    return sorted(
        path
        for path in vault.rglob("*.md")
        if ".obsidian" not in path.parts and ".trash" not in path.parts
    )


def fingerprint(vault: Path) -> tuple[tuple[str, int], ...]:
    """Changes when a note is added, removed, or edited."""
    found = []
    for path in _notes(vault):
        try:
            stamp = path.stat().st_mtime_ns
        except OSError:
            continue
        found.append((str(path), stamp))
    return tuple(found)


def _ascii_label(text: str) -> str:
    cleaned = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in text)
    cleaned = " ".join(cleaned.split())
    return cleaned[:LABEL_LIMIT] or "?"


def _layout(count: int, edges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if count == 0:
        return []
    if count == 1:
        return [(500, 500)]
    pos = []
    for index in range(count):
        angle = 2 * math.pi * index / count
        pos.append([500 + 280 * math.cos(angle), 500 + 280 * math.sin(angle)])
    span = 180.0
    for _step in range(25):
        disp = [[0.0, 0.0] for _ in range(count)]
        for left in range(count):
            for right in range(left + 1, count):
                dx = pos[left][0] - pos[right][0]
                dy = pos[left][1] - pos[right][1]
                dist = math.hypot(dx, dy) or 0.01
                push = (span * span) / dist
                ux, uy = dx / dist, dy / dist
                disp[left][0] += ux * push
                disp[left][1] += uy * push
                disp[right][0] -= ux * push
                disp[right][1] -= uy * push
        for left, right in edges:
            dx = pos[left][0] - pos[right][0]
            dy = pos[left][1] - pos[right][1]
            dist = math.hypot(dx, dy) or 0.01
            pull = dist * dist / span
            ux, uy = dx / dist, dy / dist
            disp[left][0] -= ux * pull
            disp[left][1] -= uy * pull
            disp[right][0] += ux * pull
            disp[right][1] += uy * pull
        for index in range(count):
            pos[index][0] += max(-24.0, min(24.0, disp[index][0] * 0.02))
            pos[index][1] += max(-24.0, min(24.0, disp[index][1] * 0.02))
    xs = [point[0] for point in pos]
    ys = [point[1] for point in pos]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    placed = []
    for point in pos:
        placed.append(
            (
                int(80 + (point[0] - min_x) / span_x * 840),
                int(80 + (point[1] - min_y) / span_y * 840),
            )
        )
    return placed


def _color_groups(vault: Path) -> list[tuple[str, int]]:
    """Obsidian graph color groups: path:Folder → rgb from .obsidian/graph.json."""
    path = vault / ".obsidian" / "graph.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    groups: list[tuple[str, int]] = []
    for item in data.get("colorGroups") or []:
        query = str(item.get("query") or "").strip()
        if not query.startswith("path:"):
            continue
        folder = query[5:].strip().strip('"').strip("/")
        rgb = (item.get("color") or {}).get("rgb")
        if folder and isinstance(rgb, int):
            groups.append((folder, rgb & 0xFFFFFF))
    return groups


def _color_for(relative: str, groups: list[tuple[str, int]]) -> int:
    for folder, rgb in groups:
        if relative == folder or relative.startswith(folder + "/"):
            return rgb
    return _DEFAULT_COLOR


def build_vault_graph(vault: Path) -> VaultGraph:
    """Wikilinks become edges. The busiest notes are kept when the vault is large."""
    notes = _notes(vault)
    groups = _color_groups(vault)
    by_name: dict[str, Path] = {}
    for path in notes:
        by_name.setdefault(path.stem.lower(), path)
    ids: dict[str, int] = {}
    labels: list[str] = []
    relatives: list[str] = []

    def node_id(key: str, label: str, relative: str) -> int:
        if key not in ids:
            ids[key] = len(labels)
            labels.append(label)
            relatives.append(relative)
        return ids[key]

    for path in notes:
        relative = path.relative_to(vault).as_posix()
        node_id(str(path), path.stem, relative)
    raw_edges: set[tuple[int, int]] = set()
    for path in notes:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        left = ids[str(path)]
        for match in _LINK.finditer(text):
            name = Path(match.group(1).strip()).name.removesuffix(".md").lower()
            target = by_name.get(name)
            if target is not None:
                right = ids[str(target)]
            else:
                right = node_id("?" + name, Path(match.group(1).strip()).name, "")
            if left != right:
                raw_edges.add((min(left, right), max(left, right)))
    degree = [0] * len(labels)
    for left, right in raw_edges:
        degree[left] += 1
        degree[right] += 1
    keep = sorted(range(len(labels)), key=lambda index: -degree[index])[:MAX_NODES]
    remap = {old: new for new, old in enumerate(keep)}
    edges = [
        (remap[left], remap[right])
        for left, right in raw_edges
        if left in remap and right in remap
    ][:MAX_EDGES]
    degree_kept = [0] * len(keep)
    for left, right in edges:
        degree_kept[left] += 1
        degree_kept[right] += 1
    placed = _layout(len(keep), edges)
    nodes = tuple(
        GraphNode(
            label=_ascii_label(labels[old]),
            x=placed[new][0],
            y=placed[new][1],
            deg=degree_kept[new],
            color=_color_for(relatives[old], groups),
        )
        for new, old in enumerate(keep)
    )
    return VaultGraph(nodes=nodes, edges=tuple(edges))
