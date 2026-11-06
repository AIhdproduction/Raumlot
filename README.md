# Raumlot

Raumlot converts point clouds and E57 images into parametric, ArchiCAD-ready IFC models.

## Setup

Install Python 3.12 and [uv](https://docs.astral.sh/uv/), then run:

```powershell
uv sync --all-extras
uv run raumlot doctor
uv run nox -s check
```

Run `uv run raumlot doctor --sam` to load a local SAM checkpoint and process the E57 smoke-test image on CUDA.

The full project specification is in `docs/MASTERPROMPT.md`.
