# Decisions

- 2026-11-06 — Name: `raumlot` everywhere.
- 2026-11-06 — Milestone order: command-line E57 to IFC first (M0 to M5).
- 2026-11-06 — Data sources: all will be supported; first are TLS indoors and SLAM or photogrammetry as E57 with 360-degree images using `free_camera` visibility.
- 2026-11-06 — Nomivox is adopted as the foundation by copying and improving its code without license notices. The user commits the 86 open Nomivox changes present on 2026-11-06 (last commit `3fa4149`) before the port; M2 uses that new commit.
- 2026-11-06 — Intake uses SAM 3.1 only. Weights are local in `models/` (`sam3.1_multiplex.pt` plus Hugging Face assets); the fallback SAM 3 checkpoint is `D:\Nomivox\models\sam3.pt`.
- 2026-11-06 — AI backends: OpenRouter is the default; Claude, Gemini, and Codex subscriptions are supported.
- 2026-11-06 — IFC target: ArchiCAD-native editability. The ArchiCAD version remains open.
- 2026-11-06 — Every element is parametric; the viewer provides camera mode and attribute editing.
- 2026-11-06 — Furniture uses templates, an imported IFC catalog, and an automatically growing catalog as specified in section 9.4.
- 2026-11-06 — Q1: Nomivox preset class IDs are used unchanged. SAM 3.1 further splits structure classes into instances per wall face and segment; optional subclasses are stored in a separate per-point field rather than as new class IDs. M3 defines the details.
- 2026-11-06 — Q11 hardware: Intel Core i9-13900K (24 cores, 32 threads), 127.7 GB RAM, NVIDIA RTX 4090 24 GB (driver 610.88), free disk C: 183 GB, D: 562 GB, E: 2621 GB. Python 3.12.9 and uv 0.9.30. Largest project size and acceptable times remain open; initial budgets are in `docs/PERFORMANCE.md`.
- 2026-11-06 — Rust was not installed at M0 start. The user will install rustup with the MSVC toolchain, after which the minimal maturin build follows. (superseded: installed 2026-11-06)
- 2026-11-06 — Graphify is installed project-locally in `.codex-tools/` and excluded from Git.
- 2026-11-06 — Q17 test data: `test_PW/eingang_buero.e57` is 182 MB with one SLAM scan, 1,053,511 XYZ/intensity/RGB/normals points, and 29 posed 8192×4096 spherical images. `test_PW/pointcloud.e57` is 1.38 GB with one scan, 17,009,444 XYZ/normals/intensity/RGB points, and 151 posed 8192×4096 spherical images. Both use `free_camera`; images containing people, license plates, and screens remain open for M3.
- 2026-11-06 — Q18: answered. `uv lock` resolved the complete environment with NumPy 1.26.4. A trial constraint of `numpy>=2` failed because sam3 0.1.0 (pinned commit 0570b3a5) requires `numpy>=1.26,<2`; all other dependencies import and work with NumPy 1.26.4. Decision: one environment, NumPy pinned by sam3 to `<2`; revisit when sam3 supports NumPy 2. New dependencies must support NumPy 1.26; no separate intake environment is needed. See ADR 0003.
- 2026-11-06 — SAM check: `models/sam3.1_multiplex.pt` loads in the sam3 image predictor (`build_sam3_image_model` + `Sam3Processor`), load 7.1 s, inference 1.1 s on a 1024x1024 crop, peak VRAM 4.1 GB. SAM 3.1 is usable for still images; the SAM 3 fallback is not needed for now.
- 2026-11-06 — Rust toolchain installed: rustc 1.99.1, cargo 1.99.1, MSVC. PyO3 0.30.1 and maturin 1.16.0 are the current versions.
