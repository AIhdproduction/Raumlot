# Raumlot – project rules

The full spec is docs/MASTERPROMPT.md. Every decision is recorded in docs/DECISIONS.md and docs/adr/. This file is the short form. Keep it current.

## What it is
Point cloud plus images (E57 first) → parametric, ArchiCAD-ready IFC, floor plans and a QA report. CLI `raumlot` comes first, then the desktop viewer.

## Roles
- Claude orchestrates. Code is written by Codex or Gemini, and checks are done by the verifier (global CLAUDE.md).
- Each milestone (spec §15) is split into work packages. One brief per work package.
- Every brief contains the verbatim line about never deleting files, forbids placeholder tests, and forbids commits by the worker.
- Codex cannot run pytest in its sandbox. Claude or the verifier runs `uv run nox -s check` after every job.

## Fixed decisions
- The name is `raumlot` everywhere. The property sets are Raumlot_Quality, Raumlot_Location and Raumlot_User. The IDS file is specs/raumlot.ids.
- Nomivox (D:\Nomivox) is the foundation. Its code is copied and improved, never changed in place, and needs no license notices (§4.2). NeuralCensor is used only for its SAM logic.
- The intake uses SAM 3.1 only. No Ollama, no Falcon. The weights live in models/ and are never committed. SAM 3 is the fallback, loaded by path.
- Visibility mode is `station` or `free_camera`. Both test datasets are free_camera.
- Every element is parametric (§5.1). Geometry comes from parameters, a dependency graph drives recomputation, and every change is a JSON patch with an inverse.
- The IFC must import into ArchiCAD as native, editable elements (§10, checklist in §10.2).
- AI backends: OpenRouter is the default. Claude, Gemini and Codex subscriptions are optional, through their CLIs. Only anonymized images are ever sent (intake run id gate).
- Furniture: templates, an IFC catalog and a catalog that grows automatically (§9.4).
- The GPU is needed only for the SAM passes. Default tests run without a GPU and without network.

## Technical rules
- Python 3.12 with uv. All geometry math in float64. Large coordinates use an origin offset.
- Stream and chunk. Never load a full cloud into memory. Stages are cached by input hash.
- On Windows, multiprocessing uses spawn. Never create CUDA in the parent process.
- Rust (PyO3/maturin) is used only for kernels a benchmark proves too slow.
- Check current library docs before using an API. Do not rely on memory.

## Tests
- Run `uv run nox -s check` for ruff, mypy and pytest without the gpu, realdata, network and slow markers.
- Run the `nox -s gpu`, `-s realdata` and `-s network` sessions at the end of each milestone.
- Real data lives in test_PW/ (RAUMLOT_TESTDATA) and is never committed or sent anywhere:
  - eingang_buero.e57: SLAM scan, 1.05M points, 29 spherical images. This is the reference dataset.
  - pointcloud.e57: 17M points, 151 spherical images.

## Git
- No Co-Authored-By and no AI notes in commits or PRs.
- Commit only when Domenic asks.
- Brief files `_codex_brief*.md` are excluded and get deleted after use.
