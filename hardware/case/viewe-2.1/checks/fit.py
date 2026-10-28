"""Fit check: dummy display/adapter/lid vs the stand.

Run: cadgen +0.8.1 run checks/fit.py
"""

import sys
from pathlib import Path

import build123d as bd
from cadgen.geometry import closest_points, overlap_volume

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from case import USB_HOLE_X, USB_HOLE_Z, fit_check  # noqa: E402


def world_parts(node, parent=None):
    here = (bd.Location() if parent is None else parent) * node.location
    if node.children:
        for child in node.children:
            yield from world_parts(child, here)
    else:
        yield node.located(here)


def find_part(tree, label):
    matches = [p for p in world_parts(tree) if p.label == label]
    if len(matches) != 1:
        raise ValueError(f"Expected one part labelled {label!r}, found {len(matches)}")
    return matches[0]


tree = fit_check().shape
stand = find_part(tree, "stand")
ok = True
for label in ("display", "adapter_pcb", "usb_c", "j2_fpc", "lid"):
    v = overlap_volume(stand, find_part(tree, label))
    print(f"overlap stand/{label}: {v:.3f} mm3")
    ok &= v < 1e-3

d = closest_points(stand, find_part(tree, "adapter_pcb")).distance
print(f"pcb to posts: {d:.3f} mm (0 = resting on the posts)")
ok &= d < 1e-3

usb = find_part(tree, "usb_c")
gap = closest_points(stand, usb).distance
print(f"usb-c receptacle to nearest stand wall: {gap:.3f} mm")
print(f"rear opening: {USB_HOLE_Z} tall x {USB_HOLE_X} wide")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
