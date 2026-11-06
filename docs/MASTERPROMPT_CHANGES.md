# Master prompt changes: version 1 to version 2 (2026-11-06)

Basis: review of version 1, read-only exploration of D:\Nomivox and E:\NeuralCensor, inspection of D:\Raumlot\test_PW\eingang_buero.e57, and the user's decisions in the review session.

## User decisions applied
| # | Decision | Where |
|---|---|---|
| U1 | Name `raumlot` everywhere (package, CLI, property sets Raumlot_Quality, Raumlot_Location, Raumlot_User, specs/raumlot.ids). `scan2ifc` is gone. | all |
| U2 | Command line path E57 → IFC first (v0.1 = M0 to M5), viewer, AI and app later. | 15 |
| U3 | All data sources come. First TLS indoors and SLAM or photogrammetry delivered as E57 with 360 degree images. Both use a depth map from the image pose. | 3.0, 3.2, 3.3 |
| U4 | Adopt and improve Nomivox instead of rebuilding. Own code, no license notices. | 1, 4.2, 15 M2/M3 |
| U5 | SAM 3.1 weights and Hugging Face assets are in D:\Raumlot\models. | 6.1, 13 |
| U6 | AI through several backends: OpenRouter default, plus Claude, Gemini and Codex subscriptions. | 8.1, 8.5, 12.1 |
| U7 | From NeuralCensor only the SAM parts. No Ollama, no Falcon. Only SAM 3.1 processes the images. | 4.2, 6.1, 12.1, 17 |
| U8 | The IFC must look like a model made in ArchiCAD. | 1, 10, 10.2 |
| U9 | Viewer shows cloud, model and cameras. Click a camera, see the photo and blend in cloud and model. | 12.3, 12.5, 15 M8 |
| U10 | Click elements, see and edit all attributes and the geometry. Every element is parametric, which helps scripts and the AI. | 5.1, 12.6, 8.7 |
| U11 | Test with D:\Raumlot\test_PW\eingang_buero.e57 (SLAM, entrance, room, corridor, windows, furnishings). | 14.7, 15 |
| U12 | Furniture: ready-made objects to choose from, like the ArchiCAD library. | 9, 15 M10 |

## Contradictions resolved
| # | Version 1 | Version 2 | Reason |
|---|---|---|---|
| C1 | "GPU is optional and never required" and at the same time a mandatory SAM pass on the RTX 4090 | GPU required only for the intake. All other stages and all default tests run without a GPU. | Both cannot be true. |
| C2 | Images are required (section 1), but stage 4 mentions "projects without images" | Image mode with_images (default) or no_images (classified cloud only, no SAM, no image tasks) | Makes the edge case explicit. |
| C3 | Store per point and per image a visible flag and pixel position | Store compressed depth maps per image view, compute visibility on demand per unit | Does not scale to hundreds of images and hundreds of millions of points. Same approach as Nomivox. |
| C4 | The data source decided the visibility method | New derived setting visibility mode: station or free_camera, set per image by the importer | An E57 from SLAM or photogrammetry with posed 360 degree images uses the same path as photogrammetry. The data source now only sets tolerances and noise. |
| C5 | Rust kernels and an equivalence suite from M0 and M2 | M0 only proves the maturin build. Kernels only after a benchmark shows the need. | Nomivox already has numpy and torch CUDA kernels. Rust first would be work without measured benefit. |
| C6 | Strict determinism | Determinism with cached masks. GPU paths compared within a documented tolerance. | SAM on CUDA is not bitwise reproducible. |
| C7 | Wizard steps and the viewer in M2 before any pipeline exists | Viewer in M8, wizard in M11, `raumlot init` before that | Follows U2. |

## Facts corrected from the code
| # | Version 1 | Version 2 |
|---|---|---|
| F1 | Nomivox preset: 34 classes, 246 prompts | 36 classes, 268 prompts, auxiliary groups sky, mirror_mask, glass_mask, reflective_mask |
| F2 | Q1 asks for class ids for people, license plates and screens | These are flag bits in their own LAS extra dimension (anon_flags), not class ids. A screen point keeps its building class. |
| F3 | NeuralCensor uses a contour mask with strong blur | Confirmed (blur plus quantization). Raumlot implements pixelation and compares both. |
| F4 | Vote accumulator: top-4 counters in a memmap | The proven Nomivox VoteStore (SQLite on disk) stays. The memmap is built only if the large memory test fails. |
| F5 | Point label budget 7 bytes | 10 bytes (mirror state and scan or source id added). |
| F6 | Generic stack versions | Start from the Nomivox pins: Python 3.12, torch 2.11 cu128, sam3 commit 0570b3a5, pye57 0.4.19, laspy 2.7 with lazrs, PySide6 6.12, numpy 1.26.4 (numpy conflict check in M0, Q18). |
| F7 | VRAM planner for SAM, Falcon and a vision model (18 GB together) | SAM only plus viewer headroom (follows U7). |

## Gaps closed (needed to build and test)
| # | Addition | Where |
|---|---|---|
| G1 | Roles: Claude orchestrates, Codex or Gemini implement, the verifier checks. Milestones cut into work packages. Graphify in M0. | 2.1, 15 |
| G2 | Fake providers (segmentation from label renders, scripted AI) so all default tests run without GPU and network | 14.1, 14.6 |
| G3 | Test tiers with pytest markers (gpu, realdata, network, slow) and nox sessions | 14.6 |
| G4 | Real test data outside git through RAUMLOT_TESTDATA, `raumlot e57 crop` for small fixtures | 14.7 |
| G5 | Re-run policy that keeps locked and manual elements and stable ids | 5 |
| G6 | Patch records store inverse operations for exact undo | 5 |
| G7 | Parameter schemas per element type, one geometry module, dependency graph | 5.1 |
| G8 | Rule A defined precisely (plane-to-plane distance over the element extent plus a quantile check) | 7 |
| G9 | Coverage radius and minimum coverage moved to tolerances.yaml | 7 |
| G10 | Input hashing strategy (xxhash once, cached by path, size, mtime) | 4 |
| G11 | Windows multiprocessing rules (spawn, picklable stages, no CUDA in the parent) | 4 |
| G12 | Full CLI surface with one demo command per milestone | 4, 15 |
| G13 | Project folder with runs/<run_id>/ and logs/ | 4 |
| G14 | Docs created when first needed, not as 16 empty files in M0 | 13 |
| G15 | Camera marker export for Cyclone 3DR before the viewer exists, colored LAS from M4 | 3.2, 12.4 |
| G16 | First level space boundaries only in version 1, height system named in Q4 | 10, 16 |
| G17 | Walls seen from one side get an assumed thickness with a note | 6 stage 5i |
| G18 | SAM 3.1 multiplex checkpoint smoke test in M0, SAM 3 fallback by path | 6.1, 15 M0 |
| G19 | Each milestone has goal, WPs, demo command, acceptance and what is not included | 15 |

## Milestone order
| Version 1 | Version 2 |
|---|---|
| M0 scaffold | M0 scaffold, environment check, SAM smoke test, Rust smoke build |
| M1 scene model and IFC | M1 plus parameter schemas, dependency graph, ArchiCAD-ready IFC |
| M2 wizard, ingest, viewer, Rust kernels, PDAL and renderer ADRs | M2 Nomivox port and ingest (CLI) |
| M2b intake | M3 intake |
| M3 interior structure | M4 interior structure, first real IFC, colored LAZ, minimal QA report |
| M4 photo linking | merged into M8 camera mode |
| M5 openings | M5 openings and stairs |
| M5b outdoor | M7 outdoor |
| M6 furniture | M10 furniture with templates, catalog and choice |
| M7 AI | M9 AI with several backends |
| M8 floor plans and QA report | M6 floor plans (QA report moved to M4) |
| M9 review editing | M8 attribute and parameter editing, M12 drag handles and split or merge |
| (part of M2) wizard | M11 wizard and run panel |
| (part of 3.2) importers | M13 more importers |
| M10 instance refinement | M14 |
| M11 hardening | M15 |

## Questions
- Answered: Q8, Q16.
- Partly answered from the code, the test data or the user: Q1, Q3, Q5, Q6, Q7, Q9, Q11, Q12.
- New: Q16b (Nomivox source commit), Q17 (test data inventory), Q18 (numpy and environment), Q19 (furniture catalog sources).
- Every question now has a status, the milestone where it is asked at the latest and, where sensible, a default.
- Q17 is new and already partly answered (the two test datasets are known).

## Also changed after review
- CLI list includes `raumlot synth`, `--ai off`, `--labeled`, `--colored` and comma separated formats.
- Sanitary templates map to IfcSanitaryTerminal. Furniture PredefinedType sits on the type object.
- Wall joins: X crossings become two T joins. The ArchiCAD use of IfcRelConnectsPathElements is tested in M1, and wall bodies are cut in any case.
- First level space boundaries only for walls, floors and ceilings.
- Candidate Qto set names listed for verification in M1.
- The status unsure is computed by the script, never set by the AI.
- Catalog promotion is delivered in M10.

## Removed
- Falcon Perception and the local verification model (Ollama) from stack, intake, wizard, VRAM planner and risks (U7).
- License and attribution notes for Nomivox and NeuralCensor (U4). Licenses remain for third-party assets.
- The research dataset based furniture library as the main path (now templates plus the IFC catalog, U12).
