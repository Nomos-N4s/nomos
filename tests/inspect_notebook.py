"""Inspect the prove.ipynb notebook."""
import json

with open("prove.ipynb") as f:
    nb = json.load(f)

for i, cell in enumerate(nb["cells"]):
    ctype = cell["cell_type"]
    src = cell["source"]
    first_line = src[0].strip()[:80] if src else "(empty)"
    print(f"Cell {i}: {ctype} - {first_line}")
