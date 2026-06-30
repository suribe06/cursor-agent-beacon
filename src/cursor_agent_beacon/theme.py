"""Theme pack loading and custom GIF resolution."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from cursor_agent_beacon.paths import default_themes_dir


@dataclass(frozen=True, slots=True)
class ThemeAnimation:
    agent_state: str
    path: Path
    loop: bool
    caption: str


@dataclass(frozen=True, slots=True)
class ThemePack:
    theme_id: str
    name: str
    root: Path
    manifest: dict
    animations: dict[str, ThemeAnimation]

    def animation_for(
        self,
        agent_state: str,
        *,
        hook_event_name: str | None = None,
    ) -> ThemeAnimation | None:
        if hook_event_name == "stop" and agent_state in {"success", "idle"}:
            stop_anim = self.animations.get("stop")
            if stop_anim is not None:
                return stop_anim
        return self.animations.get(agent_state)


def default_themes_root() -> Path:
    return default_themes_dir()


def default_theme_id() -> str:
    return os.environ.get("CURSOR_AGENT_BEACON_THEME", "standard")


def load_theme(
    theme_id: str | None = None,
    themes_root: Path | None = None,
) -> ThemePack:
    theme_id = theme_id or default_theme_id()
    root_base = themes_root or default_themes_root()

    if theme_id == "standard":
        theme_root = root_base / "standard"
    elif theme_id.startswith("custom/"):
        theme_root = root_base / theme_id.removeprefix("custom/")
    else:
        theme_root = root_base / "custom" / theme_id

    manifest_path = theme_root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Theme manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    states = manifest.get("states") or {}
    animations: dict[str, ThemeAnimation] = {}

    for agent_state, cfg in states.items():
        rel = cfg.get("animation")
        if not rel:
            continue
        path = (theme_root / rel).resolve()
        animations[agent_state] = ThemeAnimation(
            agent_state=agent_state,
            path=path,
            loop=bool(cfg.get("loop", True)),
            caption=str(cfg.get("caption", agent_state)),
        )

    return ThemePack(
        theme_id=str(manifest.get("id", theme_id)),
        name=str(manifest.get("name", theme_id)),
        root=theme_root,
        manifest=manifest,
        animations=animations,
    )
