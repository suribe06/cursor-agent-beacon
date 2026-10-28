// VIEWE 2.1" case — viewer only. The model's source is src/case.py (build123d);
// these meshes are exported from it, so edits belong there, not here.
// Regenerate: ~/.local/bin/cadgen +0.8.1 run src/exports.py

// "print": the two parts you print. "fit": stand with dummy display, adapter and lid in place.
view = "print"; // [print, fit]

if (view == "fit") {
  color([0.12, 0.64, 0.88]) import("preview/fit_check.stl");
} else {
  color([0.12, 0.64, 0.88]) import("STL/stand.stl");
  translate([60, 0, 0]) color([0.12, 0.64, 0.88]) import("STL/lid.stl");
}
