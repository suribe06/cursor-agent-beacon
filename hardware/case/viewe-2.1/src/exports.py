from pathlib import Path

from cadgen import export

from case import fit_check, lid, stand

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    export(stand(), ROOT / "3MF/stand.3mf", ROOT / "STL/stand.stl")
    export(lid(), ROOT / "3MF/lid.3mf", ROOT / "STL/lid.stl")
    export(fit_check(), ROOT / "preview/fit_check.stl")  # review only, not for printing
