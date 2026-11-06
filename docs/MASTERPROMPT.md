# Raumlot Master Prompt

Version 2 (2026-11-06). Changes from version 1 and the reasons are listed in docs/MASTERPROMPT_CHANGES.md.

How to use this file:
1. The repository is D:\Raumlot. This file is docs/MASTERPROMPT.md.
2. Tell Claude Code: "Read docs/MASTERPROMPT.md completely. Ask the open questions of section 16 that are marked for M0 in one batch. Then work through the milestones in section 15, one at a time."
3. Claude Code derives a short CLAUDE.md from sections 2, 3.0, 4.1, 5.1, 6.1, 13 and 14 and keeps it current.

## 1. Mission

Build a desktop application and a command line tool named Raumlot. They turn a point cloud with images into a parametric building model.

Inputs:
- one E57 file with points and images (no classification needed), or
- a LAS or LAZ cloud (classified or not) plus images with known camera poses and camera models (from E57 files, SLAM photo sets or photogrammetry exports).

The E57 file is the primary container. It covers stationary scans (TLS), SLAM scans and photogrammetry projects, as long as the images carry poses and camera models, for example 360 degree spherical images.

Outputs:
- for indoor scope: an accurate, semantically complete IFC model (walls, floors, ceilings, windows, doors, stairs, spaces and optionally furniture) and 2D floor plans derived from that model,
- for outdoor scope: a terrain model and building models in IFC.

The IFC must arrive in ArchiCAD like a model that was drawn in ArchiCAD: native walls, slabs, doors, windows and zones with types, layers, properties and quantities, ready for editing there (section 10).

Every modeled element is parametric. Its geometry is generated from a small set of parameters, so scripts, the AI and the human change the same few numbers (section 5.1).

What gets built is decided at the start of every project (section 3.0). The first processing step is the intake block (section 6.1): one SAM 3.1 pass on the local GPU anonymizes the images and segments the cloud at the same time. External AI models only ever see anonymized images. The run is automatic. The human reviews at the end in the viewer (section 12), sees what is good and what is doubtful, clicks elements, reads and edits their attributes and parameters, and corrects the model there.

Priorities in this order:
1. Accuracy and traceability. Every number has a source and a measured deviation.
2. IFC correctness and ArchiCAD editability. Clean classes, types, relations, units, georeferencing.
3. Automation. Minimal human intervention before the review stage.
4. Speed. Performance budgets are quality gates (section 4.1).
5. AI cost.

Reuse first: the user's project Nomivox (D:\Nomivox) already implements E57 reading, camera models, panorama tiling, visibility, the SAM 3 backend, voxel voting, mirror handling and LAS export. Raumlot adopts this code as its foundation and improves it. It is not rewritten from scratch (section 4.2).

## 2. Working rules

### 2.1 Roles
- The user's global CLAUDE.md applies. Claude Code is the orchestrator: it plans, writes the briefs, reviews and decides. Code changes are implemented by the configured code workers (Codex, or Gemini through the Antigravity CLI). Checks, test runs and code lookups go to the verifier subagent.
- Every milestone is cut into work packages (WP). One WP fits into one worker brief, touches a known set of files and has its own acceptance tests. Section 15 lists the WPs per milestone. Claude Code refines them at the start of each milestone.
- Graphify is set up in M0 and refreshed before each milestone, so every brief starts from a current overview.

### 2.2 Rules
- Code, comments, UI text, commit messages and documentation are in English.
- Complete, functional code only. No stubs, no TODO placeholders in delivered milestones, no omitted parts.
- Use current best practice and no deprecated APIs. Before using a library, check its current documentation and current stable version (for example with Context7 or the official docs). Do not rely on memory for API details of ifcopenshell, IfcTester, laspy, pye57, Open3D, PySide6, pyvista, PyO3, maturin, the sam3 repository, the OpenRouter API or the CLIs of the AI subscription backends. Pin versions after checking.
- If important information is missing, ask targeted questions and make no assumptions. Ask in one batch per milestone, at the start. Record every answer in docs/DECISIONS.md.
- Work milestone by milestone. At the end of each milestone: tests pass, docs are updated, the demo command is documented and runs, and you stop for the user to verify.
- Document every architecture decision as an ADR in docs/adr/ (short: context, decision, consequences).
- Never hardcode API keys. Never print keys to logs or the command line.
- Determinism: same input, same config and the same cached masks give the same output. Use fixed random seeds and log them. GPU inference (SAM) is not bitwise reproducible across driver or library versions. Its outputs are cached (mask cache, section 6.1), and tests of GPU paths compare within a documented tolerance.
- All geometry math in float64. Large coordinates (for example Swiss LV95) are handled with a stored origin offset, never by reducing precision.
- Speed is a requirement. Follow section 4.1. Measure before and after every optimization and record the numbers in docs/PERFORMANCE.md.
- The AI review is part of every standard run, for indoor and outdoor scope and for every data source. It must work with any model and any backend behind the AI layer. No stage may depend on one specific model. A script-only mode exists for tests, for the baseline comparison and as a fallback when the AI is unreachable. See section 8.
- Privacy order: no external AI model, no cache that later stages read and no export ever contains a non-anonymized image. Anonymization and segmentation happen first, in the intake block (section 6.1).
- Memory safety is a requirement. The intake block must run on an RTX 4090 with 24 GB VRAM and must keep peak RAM flat as the number of scans grows (section 6.1).
- Test data and model weights never enter git and never leave the machine (section 14.7).
- Be critical. If a requirement in this file is contradictory, physically unrealistic or risky, say so directly and propose an alternative before building it.

## 3. Inputs and project setup

### 3.0 Project setup choices

The user makes these choices in the project wizard (or in project.yaml for the CLI) before anything is imported. They are stored in project.yaml and in the scene model. They switch the input panels, the pipeline branches, the tolerance profile and the IFC output.

Choice 1: data source (required, one per project in version 1)
- tls_stationary: terrestrial scanner stations.
- slam: mobile scanner.
- photogrammetry: dense cloud from a photogrammetry software.
The data source sets the default tolerance profile, the expected noise and which noise warnings apply. It does not decide the visibility method (see visibility mode). Mixed sources in one project are out of scope for version 1. Ask before adding them.

Derived setting: visibility mode (set automatically by the importer, shown in the wizard, can be overridden)
- station: the image was taken from a scan station and the points of that station are known (per-scan membership in the E57, or point_source_id in a LAS). The scanner range image of that station is the depth map.
- free_camera: the image pose is not a scan station, or no per-station membership exists. Visibility comes from a Z-buffer depth map rendered from the image pose. This is the normal case for SLAM and photogrammetry, including E57 files that contain one merged cloud and many posed 360 degree images.
- Rule: if an image is associated with a scan and its pose matches the scan pose within a tolerance, use station. Otherwise use free_camera. The decision is logged per image.

Choice 2: scope (required)
- indoor_outdoor: buildings with exterior shell and interior.
- indoor_only: interior only.
- outdoor_only: terrain and buildings only.

Choice 3: indoor detail (only when scope includes indoor)
- structure_only: walls, floors, ceilings, windows, doors, spaces and stairs. Stairs have a toggle, default on.
- structure_and_furniture: structure plus furniture and fixtures (section 9).

Choice 4: outdoor output (only when scope includes outdoor)
- Terrain model: surface mesh from the ground class, with configurable resolution, hole filling and simplification.
- Building models: footprint, walls, roof planes, simplified to a configurable level of detail. Default is a simplified volume with roof shape. Facade openings, vegetation and vehicles are off by default and can be switched on later.
- The exact level of detail is open (Q13).

Choice 5: intake settings (section 6.1, defaults are on and recommended)
- Anonymization: on or off, classes (default people, license plates, computer screens), method and strength.
- SAM version and checkpoint (default 3.1, models/sam3.1_multiplex.pt), class preset (default: presets/default.json adopted from Nomivox), GPU memory budget.

Choice 6: image mode
- with_images (default): images are required and the intake block runs.
- no_images: allowed only for a cloud that is already classified. No SAM pass, no anonymization, no image-based AI tasks. Instances come from clustering (stage 4). The wizard and the QA report state the mode.

Effect of the choices:

| Choice | Pipeline effect |
|---|---|
| indoor_only | Storeys, interior structure, openings, furniture if enabled. No terrain. Floor plans per storey. |
| outdoor_only | Terrain and building extraction only. No storeys, no openings, no furniture. Output is a site model and building footprints. |
| indoor_outdoor | Both branches. The exterior shell is used as a constraint for the outer wall faces of the interior. Conflicts above tolerance are flagged. Everything shares one georeference. |
| structure_only | Furniture stages are skipped completely. |
| visibility station | Range image of the station as depth map, camera to scanner center offset applied. |
| visibility free_camera | Z-buffer depth map per image pose. With timestamps (SLAM): only points within a time window around the photo. |
| photogrammetry | Scale and georeference are checked in stage 1. Relaxed tolerance profile. |
| no_images | Stage 1 to 3 reduced to ingest and class mapping. Image-based review tasks are skipped and their elements go to the review queue as unsure. |

### 3.1 Point cloud (LAS/LAZ)
- Accept both LAS and LAZ. Read with laspy in chunks. The LAZ backend is lazrs (pinned in Nomivox as lazrs 0.8.2, check the current version), because it works on Windows without extra installs.
- The tool must handle clouds of 50 million points and more without loading everything into RAM.
- Read XYZ, classification, intensity, RGB (if present), point_source_id, gps_time (if present).
- The class ID to class name mapping is configurable in configs/classes.yaml. Do not assume IDs. Indoor and outdoor classes are mapped separately. The default map comes from presets/default.json, adopted from Nomivox: 36 classes, 268 English prompts, the special classes 1 (unclassified) and 68 (reflection), and the auxiliary prompt groups sky, mirror_mask, glass_mask and reflective_mask that are used during segmentation but never written as classes. Let the user confirm the map (Q1, Q13).
- The cloud may be unclassified. Stage 3 (section 6.1) classifies it from the images with SAM 3.1. Existing classes count as prior knowledge and conflicts are marked.

### 3.2 Images, camera poses and cameras
Every image source is converted into one internal ImageSet:
- images (file paths or E57 blob references, lazy loading),
- per image: position and orientation in the project frame, the associated scan if any, the visibility mode,
- per camera group: camera model (pinhole, fisheye, spherical, cylindrical), intrinsics, distortion parameters, image size, sensor size if known,
- optional timestamps.

Importers (each with its own tests and a documented pose convention):
- E57 (first priority, adopted from Nomivox): the full source for TLS, SLAM and photogrammetry projects. Read the scans (points, scan poses, per-scan membership) and the Image2D elements with their poses and camera representations: spherical, cylindrical and pinhole. Nomivox reads them through the pye57 libE57Format bindings (e57cls/io/reader.py E57Reader, blob access for images) and converts panoramas into perspective views (e57cls/geometry/cameras.py Camera, View, plan_views). Points go into the local cache per scan in blocks (e57cls/io/store.py) and never fully into memory. The inspection command `raumlot inspect <file.e57>` (based on e57cls/io/inspector.py) prints scans, point counts, fields, images, camera types, resolutions, poses and the derived visibility mode.
- Photogrammetry exports (milestone M13): COLMAP (text and binary), Agisoft Metashape camera XML, Pix4D camera parameter files, and a generic CSV or JSON with pose and intrinsics. Check the current specification of each format. Which software the user works with is open (Q12).
- SLAM native formats (milestone M13): see 3.3.
- Image folder plus pose file plus camera file as the generic fallback (M13).

Rules:
- Pose conventions differ between software (world-to-camera or camera-to-world, camera axes, rotation representation, units). Convert in one place (a conversion layer) and test it with synthetic cameras and known projected points.
- Distortion models differ (Brown-Conrady as in OpenCV, fisheye as in OpenCV fisheye, vendor models). Support undistortion and direct projection with distortion. Check the current OpenCV documentation.
- The viewer shows the camera positions as markers together with the cloud and the model (section 12.5). A wrong frame is visible immediately. Before the viewer exists (M2 to M7), `raumlot export cameras` writes the camera positions as a small LAZ or PLY of marker points with the camera id, so the check can be done in Cyclone 3DR.
- Projects can have thousands of images. The tool picks the best views per element by visibility. It never sends all images anywhere.

### 3.3 SLAM data
- SLAM projects delivered as E57 with posed spherical images (as the test dataset eingang_buero.e57) need no trajectory file. Each image already has its pose. Visibility mode is free_camera.
- Native SLAM sets (M13): photos with timestamps, a trajectory (format to be confirmed, Q6), camera intrinsics, fisheye model (equidistant or Kannala-Brandt as in OpenCV fisheye), and extrinsics between camera and LiDAR. Support a time offset parameter between LiDAR and camera. Nomivox contains a slam module (e57cls/slam). Check what it covers before writing new code.

### 3.4 Optional inputs
- Reference IFC of a scanned room or building for evaluation.
- Furniture catalog (section 9), only used when furniture is enabled.
- Ground control points for photogrammetry (used for the scale and georeference check).

## 4. Architecture

Strict separation:
- core library `raumlot` with no UI imports,
- CLI `raumlot` using the core,
- desktop UI using the core through a service layer.

Rules:
- The scene model (JSON) is the source of truth. IFC is an export, never the working format.
- Long tasks run in worker processes (multiprocessing), not threads, with progress reported through a queue. On Windows the start method is spawn: stage functions and their arguments must be picklable, and no CUDA context is created in the parent process.
- Every pipeline stage is a pure function of (inputs, config) and writes its result into the project cache. Stages are resumable and cacheable by input hash.
- Input hash: a streaming content hash (xxhash) of every source file is computed once during ingest and cached by (path, size, mtime). Stage hashes combine the input hashes, the stage config and the code version of the stage. Large files are never rehashed on every run.
- Providers behind interfaces: segmentation provider (SAM and a fake provider for tests), visibility provider, classification provider, AI provider (several backends, section 8.1).
- A project is a folder:
  project.yaml, cache/ (point store, indexes, depth maps, mask cache, anonymized images), scene/ (scene.json, patches.jsonl, mesh files), exports/, reports/, runs/<run_id>/ (log, config snapshot, seeds, timings), logs/.

CLI surface (every stage callable on its own, so every milestone has a demo command):
- `raumlot init <project> --source <file> --data-source ... --scope ...`
- `raumlot inspect <file>`
- `raumlot ingest <project>`
- `raumlot intake <project>`
- `raumlot extract <project> [--stage structure|openings|furniture|outdoor]`
- `raumlot review <project>` (AI loop, section 8)
- `raumlot export <project> --format ifc|las|dxf|svg|pdf|cameras`
- `raumlot report <project>`
- `raumlot run <project>` (all stages unattended)
- `raumlot library import <file.ifc>` (furniture catalog, section 9)
- `raumlot synth room|outdoor --out <project>` (synthetic test projects, section 14.1)
- common options: `--ai off` (script-only mode), `--ai-backend <name> --model <id>`, `--format` takes one or several comma separated formats, `export --format las --labeled` (labeled cloud) or `--colored` (tolerance colors)
- `raumlot e57 crop <file.e57> --box ... --out ...` (small real-data fixtures, section 14.7)
- `raumlot view <project>` (desktop viewer, from M8)

Stack (check and confirm versions in M0):
- Python 3.12 (Nomivox pins >=3.12,<3.13; raise only after checking all native dependencies), uv with pyproject.toml
- PyTorch with CUDA and the sam3 repository at a pinned commit, for the local SAM pass. Start from the pins in Nomivox (torch 2.11.0+cu128, torchvision 0.26.0+cu128, sam3 commit 0570b3a5, triton-windows, pye57 0.4.19, laspy 2.7.0, lazrs 0.8.2, scipy 1.17.1) and update after checking.
- numpy, scipy, shapely, laspy with lazrs, pye57, opencv-python, open3d (only where needed, for example Poisson meshing), scikit-learn
- numpy version: Nomivox pins numpy 1.26.4. Check in M0 whether ifcopenshell, open3d and the other packages work with one numpy in one environment (Q18). If not, the intake runs in a separate worker environment and communicates through files in the project cache. Decide in an ADR.
- ifcopenshell (IFC creation and validation), IfcTester (IDS), ezdxf (DXF), pydantic v2
- httpx or the official openai SDK pointed at OpenRouter (section 8), python-dotenv, keyring
- UI: PySide6 (Nomivox pins 6.12.0) with a renderer decided by benchmark in M8 (section 12.4)
- Rust (current stable) with PyO3 and maturin, only for kernels that a benchmark proves slow (section 4.1)
- ruff, mypy, pytest, nox, xxhash; cargo test and criterion once native code exists

### 4.1 Language and performance

Decision (confirm in an ADR in M0):
- Python orchestrates and implements the pipeline, IFC, the AI layer and the UI. The reasons are the ecosystem (ifcopenshell, Open3D, shapely, PySide6 are native libraries with Python bindings), the existing Nomivox code base and the fact that no other language offers a comparable IFC toolchain.
- Heavy point math runs in vectorized numpy or scipy, or in torch on the GPU where the GPU is already in use (Nomivox has a torch CUDA visibility kernel in e57cls/slam/visibility.py and a numpy Z-buffer in e57cls/geometry/visibility.py).
- Rust with PyO3 and maturin is the option for hot paths that stay too slow: LAS/LAZ chunk streaming and index build, point-to-image projection and Z-buffer on the CPU, plane and line RANSAC on large sets, point-to-surface distance, clustering. Parallelism with rayon, without the GIL while running.
- M0 builds a minimal Rust extension (one trivial function) with maturin and imports it on Windows. This proves the toolchain and the installer path early. Real kernels are written only after a benchmark shows the need.
- A full rewrite in Rust or C++ is rejected. It would lose the IFC ecosystem and the Nomivox code and gain nothing measurable.
- C++ with pybind11, Numba and Cython are the alternatives to record in the ADR. Switch only with measured numbers.

Method for every kernel:
1. A clear numpy or scipy reference implementation exists first (often the adopted Nomivox code). It is the test oracle and the fallback.
2. Benchmark it on synthetic and real data. Record the numbers in docs/PERFORMANCE.md.
3. If it misses its budget, write the Rust or torch version. Add equivalence tests (results match the reference within a documented float tolerance, using fixed seeds).
4. The new kernel ships when it is clearly faster or removes a memory limit. The default gate is a speedup of at least 3 times and is configurable in docs/PERFORMANCE.md.

Performance rules:
- Stream and chunk. Never load a full cloud into RAM. Use memory-mapped arrays and an on-disk index.
- Cache by input hash. A repeated run with unchanged inputs does no work.
- Workers are separate processes. Use all cores by default with a configurable limit.
- The GPU is required only for the SAM passes (the intake block and the optional second pass of stage 4 in M14). All other stages and all default tests run without a GPU. Torch kernels used outside the intake must have a CPU path.
- Budgets: after the hardware is known (Q11), propose time and memory budgets in M0 for ingest and index of 50 million points, intake per image view, visibility per image, structure extraction per room and the full pipeline. Record them in docs/PERFORMANCE.md. A benchmark run (`nox -s bench`) tracks them. A regression beyond the budget fails the milestone gate.

### 4.2 Adoption of Nomivox and NeuralCensor

Nomivox (D:\Nomivox) and NeuralCensor (E:\NeuralCensor) are the user's own projects. Their code may be taken over as is, without license notices or attribution. ADR 0002 records only the source repository and commit.

Nomivox is adopted as the foundation:
- Copy the needed modules and their tests from a fixed Nomivox commit (Q16b) into the raumlot package. D:\Nomivox itself is never changed.
- Adopted modules and their new place:
  - e57cls/io/reader.py (E57Reader, coordinates), io/inspector.py, io/store.py (ScanStore, build_store) → raumlot/io/e57/
  - e57cls/geometry/cameras.py (Pose, scan_pose, scan_to_camera, Camera, View, plan_views) → raumlot/io/cameras/
  - e57cls/geometry/visibility.py (DepthBuffer) and e57cls/slam/visibility.py (torch visibility) → raumlot/visibility/
  - e57cls/seg/backend.py (SAM3Backend with OOM halving and auto batching), seg/cache.py (tile_boxes, segment_view, MaskCache) → raumlot/intake/seg/
  - e57cls/vote/engine.py (voxel_keys, VoteStore) and the post-processing rules (vote/segments.py, dtm.py, shape_rules.py, geometry_rules.py, scene_context.py) → raumlot/intake/vote/
  - e57cls/mirror/ (reflection class 68 and the mirror state) → raumlot/intake/mirror/
  - e57cls/scene/presets.py and presets/default.json → raumlot/intake/presets/ and presets/
  - e57cls/output/las.py (write_cloud, make_header, verify_readback) → raumlot/io/las/
  - e57cls/slam/ (other parts) → evaluate in M13
  - e57cls/gui (PySide6) → evaluate in M8 as a starting point for the viewer
- The adopted tests (about 430 pytest functions in 44 files) run as the regression base. They must stay green after the port, apart from tests that are removed on purpose with a reason in the ADR.
- Improvements happen only where this file asks for more than Nomivox has: the config dict becomes typed pydantic settings, providers move behind interfaces, and anonymization flags, instance ids, scan level checkpoints, the VRAM planner, the intake report and the anonymized ImageSet are added.
- The SQLite based VoteStore stays. Its memory behavior is proven on clouds of about 94 million points. A different accumulator (for example a top-4 counter memmap) is built only if the large synthetic memory test (section 6.1) fails with the VoteStore.

NeuralCensor is a single GUI file without tests. Its code is not copied. Only its SAM logic and parameters are reimplemented in raumlot/intake/anonymize/:
- SAM text prompts for people, vehicles and license plates (person, car, truck, bus, motorcycle, license plate), extended with computer screens,
- confidence 0.15, retry pass at 0.12, a new mask is dropped if its IoU with already covered area is above 0.3, minimum mask size 100 px,
- mask dilation with an elliptical kernel of 4 percent of the mask extent, at least 3 px.
NeuralCensor also uses Falcon Perception and an Ollama vision check. Raumlot uses neither. SAM 3.1 is the only model in the intake block.

## 5. Scene model (data model)

Pydantic models, serialized to JSON. Documented in docs/DATA_MODEL.md.

Project settings (stored once): data_source, visibility mode per image group, scope, indoor_detail, outdoor_output, image mode, tolerance profile, class mapping, intake settings (anonymization classes and method, SAM version and checkpoint, GPU budget), AI settings (backend, models, without keys), origin offset and CRS.

Every element has:
- id (stable uuid), type, ifc_class, predefined_type, name, description, tag
- type_id (shared type object, for example a wall type or a furniture type)
- storey_id (indoor elements), space_ids (rooms the element belongs to or bounds), building_id, site_id
- params (typed per element type, section 5.1)
- param_origin per parameter: measured, fitted, snapped, template, assumed, manual
- properties: property set values that are not geometry (for example IsExternal, FireRating, a material name, user properties), each with its own origin
- provenance of the element: script, ai, manual
- locked (bool). Locked elements are never changed by scripts or AI. Only the user unlocks.
- source_instance_ids (point groups the element was derived from)
- metrics: deviation (rms, p95, max in meters), coverage (0 to 1), point_count, confidence (0 to 1)
- status: ok, warning, fail, unsure (derived from metrics and tolerances, never set by the AI)
- notes (list of strings, for example "tolerance below sensor noise"), ai_comments

Element types and parameters: see section 5.1.

Changes happen only as patches (JSON Patch, RFC 6902) with author, timestamp and reason. Every patch record stores the forward operations and the inverse operations, computed when the patch is applied. Patches are appended to scene/patches.jsonl. Undo applies the inverse operations, redo the forward operations. A patch touching a locked element is rejected with a clear error. A patch that breaks the parameter schema is rejected.

Re-run policy: running extraction again on a project that already has a reviewed model must not destroy work.
- Locked elements and elements with provenance manual are kept unchanged.
- New script results are matched to existing elements by type and geometric overlap (configurable thresholds). A match keeps the existing id, its manual parameters and its properties, and updates only parameters whose origin is not manual.
- Unmatched old script elements are removed through a patch with reason "not found in re-run". Unmatched new elements are added.
- The re-run is one patch group and can be undone as a whole.

### 5.1 Parametric elements

Every modeled element is a parametric object. Its geometry is always generated from its parameters and never stored as free geometry. Scripts, the AI and the human change the same parameters. The IFC writer, the viewer, the floor plans and the deviation computation all build geometry from the parameters through one geometry module.

Parameter schemas (version 1):
- Wall: axis as a straight segment (start point, end point in 2D), thickness, height, base elevation offset, axis justification (left, center, right), layer set (list of layers with material name and thickness, default one layer), wall type (interior, exterior, unknown), load_bearing (default unknown). A wall run with several segments is a chain of walls connected through wall joins.
- Wall join: the two walls, the join type (L corner, T join; X crossings are split into two T joins) and the join end. Corner geometry is derived from the join parameters in the geometry module, never from the IFC relation.
- Slab (floor): outline as a closed list of 2D vertices, thickness, top elevation, optional openings (closed outlines), layer set.
- Ceiling: outline, elevation, plane parameters (normal, offset) when not snapped to horizontal, sag value, thickness.
- Opening: host wall id, position along the host axis (distance from the wall start to the opening center), width, height, sill height, reveal depth, side (which wall face is the inside).
- Window: the opening it fills, operation type, frame depth if measured, sill_projection, sill_thickness.
- Door: the opening it fills, operation type (single swing left or right, double, sliding, other), swing side, frame depth if measured.
- Stair: start point, direction, width, step count, riser height, tread length, flights, landing outlines.
- Space: derived from its bounding walls, slabs and ceilings. Editable are name, number and the properties. Height, area and volume are computed.
- Furniture: either a parametric template (section 9) with its template id and template parameters plus placement (position, yaw), or a catalog entry (catalog id, placement, optional scale within the allowed range).
- Terrain: not parametric. Surface mesh (vertex and face arrays in a file referenced from the scene), extent, grid resolution, hole-fill flags, deviation to ground points. Marked non_parametric.
- Building (outdoor): footprint polygon(s), eaves height, ridge height, roof type (flat, gable, hip, shed, unknown), roof planes, wall segments, level of detail, link to its interior storeys if present.
- Mesh fallbacks (furniture mesh, simplified stair solid): marked non_parametric. Only placement and properties are editable.

Dependency graph:
- The scene keeps a dependency graph: openings depend on their host wall, windows and doors on their opening, wall joins on both walls, spaces on their bounding elements, quantities on the geometry, metrics on the geometry and the assigned points.
- After every patch the graph recomputes the affected elements in order: an opening moves with its wall, joins are recut, spaces, areas, volumes and quantities are recomputed, deviation and status are measured again.
- The recomputation is deterministic and is itself not a patch (it only derives values). Derived values are never edited directly.

Rules for parameters:
- Each parameter has a unit, a valid range and a step in the schema. The UI and the AI tools use the same schema.
- A parameter changed by the user gets origin manual. A parameter changed by the AI keeps the origin of the tool result it came from (for example fitted) and the element gets provenance ai.
- Optional auto-lock after a manual edit (config value, default off).
- User properties are free name and value pairs with a type (text, number, boolean). On export they go into the matching standard property set if the name belongs to one, otherwise into Raumlot_User.

## 6. Pipeline

Run order. Every stage logs inputs, outputs, parameters, duration, peak RAM and (for GPU stages) peak VRAM into runs/<run_id>/. Stages are skipped when the project setup (section 3.0) does not need them.

Stage 0 Ingest
Read the E57 scans or the LAS or LAZ in chunks into the local point store (adopted ScanStore from Nomivox) and build an on-disk spatial index. Decide the index format in an ADR in M2: memory-mapped NumPy plus a voxel grid, or Parquet or Zarr. Store the origin offset and CRS. Load the ImageSet from the chosen importer and derive the visibility mode per image. Image references, poses and camera models go to the cache. Image pixels are not copied into the cache here. Original images are read from the source files when needed, in memory only.
PDAL and COPC: compare laspy with lazrs (and a Rust streaming kernel if one exists) against PDAL on a real cloud of 50 million points in M8, together with the viewer tile format. Measure read speed, peak memory, LAZ decoding, filtering, tiling and index build. Check the current Windows distribution of PDAL and its Python bindings (it may be conda only, which would conflict with a uv based installer) and its fit. Evaluate COPC (Cloud Optimized Point Cloud) as the on-disk tile format for the viewer hierarchy in 12.4, and check the current COPC support of laspy. Default if the benchmark shows no clear gain: laspy with lazrs.

Stage 1 Frame alignment (first part of the intake block, 6.1)
Bring cloud, images and, if present, a SLAM trajectory into one frame. Verify with a projection test: project points into several images and compute an edge or depth consistency score per image and overall. Write the score to the report. If the score is below the configured threshold, stop and report instead of continuing silently.
For photogrammetry also check scale and georeference: compare with ground control points if supplied, otherwise report "scale unverified" in the report and in every element note. Photogrammetry is only as accurate as its scale and georeference.

Stage 2 Visibility and depth maps (second part of the intake block, 6.1)
Provider interface: `visibility(image_view, points) -> (mask, depth, pixel)`.
- station mode: use only the points of the station that took the image. The scanner range image is the depth map. Correct for the offset between camera and scanner center and apply a depth tolerance at edges.
- free_camera mode: Z-buffer. Project the points into the image with the camera model as small discs whose size grows with distance. The nearest depth wins. With timestamps (native SLAM) use only points within a time window around the photo. A point counts as visible when its depth matches the buffer within a tolerance of sensor noise plus a distance-dependent term (Nomivox default: max(0.03 m, 1 percent of the distance), configurable). Adopted kernels: DepthBuffer (numpy, CPU) and the torch visibility (GPU), which also handles azimuth wrap for spherical images and incidence angles.
- Optional later: depth from a Poisson mesh.
Storage: do not store a visible flag per point and per image. That does not scale (hundreds of images times hundreds of millions of points). Store one compressed depth map per image view (float16, downsampled where the tolerance allows) and recompute projections and visibility on demand for the active unit. Points, labels and votes are never duplicated per image.

Stage 3 Intake: anonymization and segmentation (third part of the intake block, 6.1)
One SAM 3.1 pass on the local GPU over every image view. It pixelates people, license plates and computer screens in the images, sets the matching points to gray, assigns a class and an instance id to every visible point and writes the anonymized ImageSet and the labeled cloud. It runs for every project with images, also for clouds that already have classes. Existing classes are prior knowledge and conflicts are marked for the review UI.

Stage 4 Instance refinement (only if furniture is enabled)
Stage 3 already delivers instance ids from the SAM masks. This stage checks and repairs them.
- Check without any model: Euclidean clustering or DBSCAN per class, compared with the instance ids from stage 3. Projects in no_images mode use the clusters as the instances.
- Suspect cluster rules: bounding box larger than a typical single object for the class, multi-peak height profile, chairs touching tables, rows of chairs.
- Version 1 (M10) reports suspect clusters and disagreements and sends them to the review queue.
- The second SAM 3.1 pass (M14): only suspect clusters, and instances where stage 3 and the clustering disagree, go through it. Input is the best photo crop chosen by visibility (image with the largest visible share of the cluster). Masks are lifted to 3D using the visibility depth and a multi-view vote. Erode masks slightly to avoid color bleeding.
- Measure the share of suspect clusters on the test rooms and report it.

Stage 5i Interior structure extraction (scope includes indoor, deterministic scripts)
- Storeys: z-histogram of floor and ceiling points, peaks give elevations.
- Floors and ceilings: robust plane fit, alpha shape or concave hull outline simplified to a polygon with few vertices, tolerance rules from section 7.
- Walls: project wall points to a horizontal section, find lines with RANSAC or Hough, merge parallel lines into wall axis plus thickness, snap per section 7, create wall joins at corners and T junctions. Compute wall height from floor and ceiling. A wall seen from one side only gets a thickness with origin assumed (default from configs, for example interior 0.12 m and exterior 0.30 m) and a note.
- Openings: cluster window and door points in the wall plane, measure width, height, sill height, reveal depth and sill projection where both sides or the reveal are visible. Create opening plus filling element. Values that cannot be seen get origin assumed.
- Stairs: bounding volume, step count from the z-histogram, flights (if enabled).
- Spaces: closed boundaries from walls, floors and ceilings.
- Exclude reflection points (class 68) from all fits.
- Version 1 targets orthogonal and mostly planar layouts. Curved walls and slopes are flagged and handled later.

Stage 5o Exterior extraction (scope includes outdoor, deterministic scripts)
- Terrain: ground class points, outlier filter, surface by grid or TIN, fill small holes under a configurable size, simplify to a configurable deviation. Measure the deviation to the ground points and show it in the tolerance view.
- Buildings: separate building points into instances, footprint by alpha shape of the projected points, roof planes by RANSAC, eaves and ridge heights, roof type from the plane arrangement, simplify to the chosen level of detail. Measure the deviation to the points.
- Vegetation, vehicles and other classes are ignored unless switched on.
- In indoor_outdoor scope, hand the outer wall faces to stage 5i as constraints.

Stage 6 Furniture (only if indoor_detail is structure_and_furniture, section 9)

Stage 7 AI review loop (section 8, runs in every standard project)

Stage 8 Verification
Script recomputes all deviations and statuses. The AI never sets a status.

Stage 9 Export
IFC (section 10), floor plans (section 11), QA report (section 14.3), colored cloud (section 12.4).

Unattended mode: no stage waits for the user. Uncertain items become entries in the review queue.

### 6.1 Intake block (stages 1 to 3): anonymize and segment first

Purpose
- Everything that looks at pixels starts here, and it runs for every project with images. One SAM 3.1 pass per image view does two jobs at once: it finds what must be anonymized and it segments the scene into classes and instances. Later stages and every external AI model work only on the results.
- The block is the adopted Nomivox pipeline (E57 points and images, SAM text prompts, projection with depth check, voxel voting, mirror handling, LAS or LAZ export), extended with anonymization (SAM logic from NeuralCensor, section 4.2) and instance ids in the same pass.
- No classified cloud is needed at import. Existing classes are prior knowledge. Conflicts are marked for the review.

Order inside the block
1. Alignment test (stage 1) on the original images in memory.
2. Visibility and depth per image view (stage 2), in station or free_camera mode.
3. View preparation: convert panoramas, fisheye and distorted images into overlapping perspective views and tiles for SAM (adopted plan_views and tile_boxes: profiles fast, balanced and high, about 95 degree field of view, tile size capped). Keep the exact mapping back to the source pixels.
4. SAM 3.1 pass per tile with text prompts: anonymization prompts and class prompts. Encode each tile once and run several prompts against it where the current sam3 API allows.
5. Anonymize the view: map the anonymization masks of all tiles back to the source image, unite them, pixelate them in the source image and write the anonymized image to the ImageSet cache. The original pixels are never written to the cache.
6. Lift to points: visible points whose projection falls into a mask get class votes and instance votes. Points inside an anonymization mask are flagged.
7. Vote and finalize per scan unit, write the labels to disk, free the memory, continue with the next unit.
8. Write the outputs, the intake report and the sample gallery.

Anonymization
- Default classes: people, license plates, computer screens (monitors and laptop screens). The list is configurable with English prompts, so classes such as vehicles, faces or documents can be added without code changes. Start from the NeuralCensor prompts (section 4.2) and add screen prompts. Test the screen prompts on real data.
- Only SAM 3.1 runs in this block. There is no second detector and no local vision model.
- Recall matters more than precision. A false positive costs some pixels. A miss exposes a person. Recall is secured by a low confidence threshold (default 0.15), a retry pass at a lower threshold (default 0.12) over the areas not yet covered, several prompt variants per class, and the sample gallery that the user inspects.
- Method: pixelation (mosaic). Block size follows the mask size so that no detail remains. Regions that carry text (license plates, screens) use the coarsest setting. The mask follows the object contour with the dilation margin from section 4.2. NeuralCensor currently uses blur with quantization. Compare mosaic and blur on real data, record the result in docs/INTAKE.md and keep the strength high. Neither method proves irreversibility.
- Point cloud: points that belong to an anonymization mask get RGB set to neutral gray (configurable). Geometry and class stay. The anonymization is recorded as flag bits in its own LAS extra dimension (anon_flags: 1 person, 2 license plate, 4 screen, further bits for configured classes). Anonymization classes are never class ids, because a screen point keeps its building class (for example furniture or appliances). Colors of all other points stay as they are.
- Gate: the anonymized ImageSet is the only image source for the AI layer, the viewer and the exports. Every anonymized image carries the run id of its intake pass in the ImageSet index. The AI tools and every AI backend adapter refuse images without it. A test proves that no code path hands an original image to an external model or to the viewer.
- Storage of anonymized images: JPEG with high quality (default 95, configurable) or PNG, decided in docs/INTAKE.md after a size test. The anonymized ImageSet is about as large as the original images.
- SAM sees the original images in memory on the user's machine. No image leaves the machine in this block.
- Anonymization is on by default and can be switched off per project. With it off, the wizard and the QA report say so, and ai.send_images is forced off until the user confirms again.
- The intake report shows a sample gallery of anonymized regions per scan or image group and counts per class. No tool guarantees complete anonymization. The user inspects the sample before any image goes to an external model.

Segmentation
- Class prompts come from the class preset presets/default.json (36 classes, 268 prompts, auxiliary groups). Let the user confirm it (Q1).
- Mirrors and glass follow the Nomivox rule: reflection points get their own class 68 and a mirror state (adopted e57cls/mirror). Structure fits exclude them.
- Instances: every SAM mask is an instance candidate. Per view, masks are lifted to points. Across views, candidates of the same class are merged by the overlap of their voxel sets with a minimum visibility share.
- Output per point: class, instance id (unique per project), confidence, anon_flags, mirror state, scan or source id.
- Stage 4 checks the instances for furniture. Structure extraction uses the classes.
- SAM version and checkpoint are config values: intake.sam.version (default 3.1) and intake.sam.checkpoint (default models/sam3.1_multiplex.pt in the repository folder, with the Hugging Face assets config.json, processor_config.json and the tokenizer files next to it). The SAM 3 checkpoint for the comparison is referenced by path (D:\Nomivox\models\sam3.pt) and never copied. Weights are never downloaded automatically and never committed.
- The 3.1 multiplex checkpoint is built mainly for video tracking with shared memory across objects. M0 runs a smoke test that loads it with the pinned sam3 commit in the image predictor and segments one test image. If that fails, the intake starts with SAM 3 and the question is settled in the M3 ADR.
- Benchmark SAM 3 against SAM 3.1 on the user's scans (class accuracy, instance split quality, anonymization recall, speed, VRAM) and record the result in an ADR. Also test whether the tracking of 3.1 gives stable instance ids across neighboring images of SLAM sequences.

Memory and GPU budget (target: NVIDIA RTX 4090 with 24 GB VRAM, RAM and disk to be confirmed in Q11)
- Hard rule: the block never loads a whole cloud and never keeps all masks. It works per scan position (station mode) or per spatial tile or image group (free_camera mode), writes the labels to disk and frees the memory before the next unit.
- Per-point labels live in memory-mapped arrays on disk. Plan about 10 bytes per point (class 1, instance id 4, confidence 1, anon_flags 1, mirror state 1, scan or source id 2). 500 million points need about 5 GB of disk.
- Voting uses the adopted VoteStore (sparse, SQLite on disk, default voxel 2 cm, one observation per scan position). Instance merging works on compact statistics (voxel id sets or hashes per mask), never on pixel masks.
- Masks are not kept at full resolution. The anonymization mask is applied at once and then dropped or stored as run length encoding for the sample gallery. Class masks are lifted at once and then dropped. The adopted MaskCache stores raw masks compressed (float16) on request and makes runs repeatable.
- GPU: a VRAM planner measures the free VRAM at start and plans one SAM instance on the GPU with a headroom for the desktop viewer (default budget 20 of 24 GB, configurable). SAM 3 needs about 5 GB according to its README. On an out-of-memory error it halves the prompt batch and then the tile size (adopted behavior, tile size down to 336 px), and logs each step. CPU workers project points, render the pixelation and write files in parallel with the GPU work.
- Scan level checkpoints: a stopped run resumes at the next unfinished unit. Peak VRAM, peak RAM and time per unit are logged and compared with the budgets in docs/PERFORMANCE.md. The block checks free disk space before it starts.
- Test: a synthetic project with many scan positions (165 as a target, Q11) must run with a flat memory curve, using the fake segmentation provider. Peak RAM must not grow with the number of scans.

Outputs
- The anonymized ImageSet (images with poses and camera models).
- The labeled cloud in the project cache, exportable as LAS or LAZ 1.4 with class, instance id, confidence, anon_flags, mirror state, scan id and the gray points. Optional copy without reflection points.
- The intake report: alignment score, counts per class, anonymization counts per scan or image group, VRAM and time, sample gallery. Documented in docs/INTAKE.md.

## 7. Tolerances

All values live in configs/tolerances.yaml with profiles per data source (tls, slam, photogrammetry). Nothing is hardcoded. Defaults for tls:

- planar_snap_tol = 0.02 m
- ceiling_sag_tol = 0.04 m
- opening_dimension_target = 0.02 m
- coverage_radius = 0.05 m (a surface sample counts as covered when a point lies within this distance)
- coverage_min = 0.3 (minimum coverage for status ok, to be tuned on the evaluation set)
- snap_quantile = 0.99
- tolerance view colors (section 12.4): green within the tolerance of the element type, red in front of the model surface beyond it, blue behind the model surface beyond it. Element status colors (ok, warning, fail) are separate and follow the status rules below.

The slam and photogrammetry profiles start from the noise estimate of the dataset (see noise floor) and are confirmed by the user. The first real dataset is a SLAM scan (section 14.7). Its profile is proposed in M4 from the measured noise.

Outdoor tolerances (terrain deviation, building footprint position, roof plane deviation, roof height) have no preset defaults. Propose values from the measured noise of the dataset and from the stated accuracy of the data source, write the reasoning into docs/TOLERANCES.md and ask the user to confirm them (Q13).

Rule A, snapping (walls, floors, ceilings):
1. Fit a plane robustly (RANSAC), then refine by least squares on the inliers.
2. Build the snapped candidate: the plane with the ideal orientation (vertical for walls, horizontal for floors and ceilings) through the centroid of the inliers.
3. Compute the maximum distance between the fitted plane and the snapped plane over the full element extent (at the corners of the element outline). This measures the tilt that snapping removes, independent of noise.
4. Compute the snap_quantile (default p99) of the absolute point distances to the snapped plane and to the fitted plane.
5. Snap if the maximum plane distance from step 3 is at most planar_snap_tol and the quantile to the snapped plane exceeds the quantile to the fitted plane by at most planar_snap_tol. Parameter origin becomes snapped.
6. Otherwise keep the fitted orientation. Parameter origin stays fitted.
7. Optionally snap wall-to-wall angles to 90 degrees under the same logic (configurable), measured as the displacement at the far wall end.

Rule B, sagging ceilings:
- A ceiling may deviate up to ceiling_sag_tol from its reference surface and still count as one element.
- Above that, the element is flagged red and the tool proposes splitting it into segments.
- Open question Q2: the reference of the 4 cm (fitted surface or horizontal). Default in code is the fitted surface, configurable. Ask before finalizing.

Noise floor:
- Estimate the sensor noise sigma per dataset by fitting planes on clearly flat regions.
- If a tolerance is smaller than 2 times sigma, write a warning into the report and into the affected elements. In that case deviation analysis shows noise, not model error. This is expected for SLAM and photogrammetry data.
- Photogrammetry profile: expect larger noise, outliers and holes on glass, mirrors and textureless surfaces. The profile starts with relaxed tolerances and stricter outlier filtering. The values are set from the noise estimate and confirmed by the user.

Deviation definition:
- Signed point-to-surface distance for all points assigned to the element. Each modeled face has a normal that points to the side it was observed from (the scanner or camera side). The sign is positive when the point lies in front of the model surface and negative when it lies behind it.
- Report rms, p95, max and coverage (fraction of the element surface that has a point within coverage_radius).
- Furniture uses one-sided deviation (scan point to model surface), because scans are incomplete.

Status:
- ok: p95 at most tolerance and coverage at least coverage_min
- warning: p95 up to 2 times tolerance, or coverage below coverage_min
- fail: above that
- unsure: the pipeline could not decide (for example the AI answered unsure or a script found contradicting evidence). The status is still computed by the script.

Parameters that cannot be measured (hidden sides, wall thickness seen from one side, load_bearing) are never reported as measured.

## 8. AI layer

Principle: the AI does not produce geometry numbers. Scripts measure. The AI decides semantics and structure: what an object is, which template or catalog entry applies, whether a result matches the photo, which element is suspicious. It changes the model only through parameter patches. The AI review runs in every standard project, for indoor and outdoor scope and for every data source. A script-only mode exists for tests, for the baseline comparison and as a fallback when no backend is configured or reachable. In that case every non-ok element goes to the review queue as unsure.

### 8.1 Backends and model choice
All AI calls go through one AIProvider interface. Behind it sit interchangeable backends. The backend is chosen per project in the wizard and with `--ai-backend` on the command line, and can be assigned per task in configs/pipeline.yaml (for example a strong vision model for the review loop and a cheaper one for routine checks).

| Backend | Access | Notes |
|---|---|---|
| openrouter (default) | OpenRouter API key | OpenAI-compatible API. One key gives access to many models. Model discovery, capability badges and prices (8.2). |
| claude_subscription | The user's Claude subscription through the locally installed Claude Code CLI in headless print mode, logged in by the user | Images passed as files, JSON loop mode, usage counted as calls and duration, not USD |
| gemini_subscription | The user's Google AI subscription through the Antigravity CLI (agy) in print and read-only plan mode, logged in by the user | as above |
| codex_subscription | The user's ChatGPT or Codex subscription through the Codex CLI (codex exec) in a read-only sandbox, with image attachments | as above |
| anthropic_api, gemini_api, openai_api (optional) | direct API keys | same capability logic as openrouter |

Rules for all backends:
- The same gates apply everywhere: only anonymized images with an intake run id, the ai.send_images switch, the cost and round caps, the cache and the pydantic validation of every answer.
- Subscription backends run as subprocesses with a hard timeout, without write access, in a fresh temporary working directory that contains only the files released for that call (prompt, anonymized images, tool results). They never see the project folder or the repository. Their tool calls use the JSON loop mode (8.2).
- Check the current command line help of each CLI at build time (M9): flags for headless mode, image input, JSON output, model selection and read-only operation. Do not rely on memory. Record the findings in configs/ai_models.yaml and docs/AI_MODELS.md.
- Check the current terms of use of each subscription for automated local calls and record them in docs/AI_MODELS.md. This is a personal project. A later commercial use would need a new check.
- Subscription backends report rate limit errors. The adapter backs off, retries within the cap and otherwise marks the items unsure. An unreachable or limited backend never blocks a run.
- The model is chosen by its id (an OpenRouter model id, or the model name of the CLI or API). Required capabilities per task are declared in code. Image tasks need image input. Loop tasks need tool calling or the JSON loop fallback.
- All AI outputs are validated against pydantic schemas. Invalid output is rejected and re-requested (max 2 retries), then the item becomes unsure.
- Cache by hash of (backend, model, prompt, images, tool results). For API backends log token counts and cost per call from the usage data in the response (check the current documentation for the fields). Compute prices with Decimal, never float. For subscription backends log calls, duration and rate limit events.

### 8.2 Model discovery and capability handling
- openrouter: the wizard fetches the model list from the OpenRouter models endpoint (GET /api/v1/models, with pagination if offered), caches it with a timestamp and refreshes on demand. Per model the list provides, according to the current OpenRouter documentation: architecture.input_modalities (image input), supported_parameters (tools, tool_choice, structured_outputs, response_format), context_length and pricing (USD per token as strings). There is no server-side filter for image input or structured output, so the client filters on these fields. Verify the field names again at build time.
- Subscription and direct API backends: capabilities come from configs/ai_models.yaml, filled in M9 from the checked documentation, and are confirmed by the qualification test (8.4).
- The model picker shows badges: backend, image input, tool calling, structured output, context length, price (or "subscription") and an estimated cost or call count per room based on previous runs.
- Capability handling:
  - No image input: allowed only for tasks without images.
  - No tool calling: use the JSON loop mode. The model answers each turn with a JSON object that names a tool and its arguments, and the code executes it. The same tool schemas apply.
  - No structured output: put the schema into the prompt, parse, validate and retry.
- OpenRouter: restrict routing to providers that support all requested parameters. Look up the exact option in the current OpenRouter provider selection documentation.

### 8.3 Context pack (any model must understand the task cleanly)
Every AI call is built by one context builder from versioned modules. Prompts are always in English, whatever the UI language.
1. Role and task of this call.
2. Glossary and conventions: units are meters, axes and the local origin offset, class names, element types, the parameter schemas of section 5.1, the meaning of param_origin, status and tolerances, what coverage and deviation mean.
3. Project settings: data source, visibility mode, scope, indoor detail, tolerance profile and noise estimate.
4. Scene summary of the current room or building as compact JSON with short ids. A mapping table in code resolves the ids.
5. Tool catalog with strict schemas and one-line purpose per tool.
6. Output schema with enumerations.
7. Few-shot examples per task: a good patch, a rejected patch, an unsure case.
8. Hard rules: never invent numbers, say unsure when unsure, never touch locked elements, geometry numbers come only from tool results, patches change parameters only.
Images always carry a legend and a text caption: camera id, what the image shows, scale or measured reference distances, instance numbers and the class color key.
Budget: the builder counts tokens against the context length of the chosen model, trims by priority, and logs what was trimmed. Trimming never removes the hard rules or the output schema.

### 8.4 Model profiles and qualification test
- configs/ai_models.yaml holds per-backend and per-model settings: temperature, max output tokens, tool mode (native or json_loop), maximum image size and count, timeout, known quirks. Defaults apply to every other model.
- Before the first real run with a backend and model, the tool runs a short fixed qualification test on a synthetic room: valid JSON rate, correct tool calls, reading instance numbers from a legend image, and a plausible patch. It reports pass or fail, token use or call count and estimated cost. A failed model triggers a warning and a suggestion to pick another one. The user may still override.
- The comparison harness (14.4) writes its results into docs/AI_MODELS.md and updates the recommended defaults.

### 8.5 API keys and logins
- Order of lookup for API keys: UI field (memory only, optional OS keyring), then environment variable, then .env file via python-dotenv.
- Keys are passed to subprocesses through environment variables only. Never as command line arguments, never in logs, never in project files.
- .env is in .gitignore and a .env.example is provided.
- Subscription backends use the login that the user made in the respective CLI. Raumlot never reads, stores or passes those credentials. If a CLI reports that a login is required, the run marks the AI items unsure and the run panel tells the user to log in in that CLI.

### 8.6 Privacy
- Images and crops can show customer property and people. The project setting ai.send_images comes with a confirmation dialog on first use per project that names the backend, its provider and the chosen model. Renders from the point cloud count as images. With the setting off, the AI works on numbers and text only (8.9).
- OpenRouter forwards requests to third-party providers whose data retention and training policies differ. Use the account-level and per-request restrictions described in the current OpenRouter privacy and provider selection documentation. The default is to exclude providers that train on or retain data. Allow a per-project list of permitted models or providers.
- Subscription backends follow the data policy of the respective subscription. The dialog says so, and docs/AI_MODELS.md records the policy found in M9.
- Check whether regional endpoints are available and whether they matter (Q9).
- Anonymization is not an optional hook. It is part of the intake block (6.1) and runs first. Every backend adapter accepts only images from the anonymized ImageSet (with the intake run id) and refuses all others. Renders from the point cloud use the gray points from the intake. The QA report records whether anonymization was on for the run.
- The user must be able to stop any data sharing. The switches ai.send_images and AI off are set per project, easy to reach, and their state is always visible in the run panel and written into the QA report.

### 8.7 Tools exposed to the AI (all computed by scripts)
- get_scene_summary(scope_id) for a room or a building
- get_param_schema(element_type) returns the parameter schema with units and ranges
- section_at(axis, value, region) returns an image and measured values
- fit_plane(region), fit_line(region)
- measure_opening(cluster_id)
- deviation(element_id) returns metrics and a deviation image
- render_view(position, direction, show=[classes|instances|elements]) returns an image with instance numbers
- crop_photo(instance_id) returns the best anonymized photo crop selected by visibility
- overlay_model(element_id, photo_id) returns the model wireframe over the anonymized photo
- search_catalog(query, dims) returns furniture template and catalog candidates with scores (furniture only)
- apply_patch(json_patch) validated against the parameter schema, rejected if it touches locked elements, edits derived values or breaks the schema

### 8.8 Loop (per room or building)
1. Scripts create the first draft.
2. Scripts compute deviations and statuses.
3. The AI receives only the non-ok elements with their images and tool access. It reviews and proposes parameter patches.
4. Scripts apply valid patches, run the dependency graph and recompute everything.
5. Stop when all elements are ok or after N rounds (default 4), or when a round brings no improvement, or when the cost or call cap per room is reached.
6. Remaining non-ok elements go to the review queue.

The AI sees one room or building at a time. Do not send the whole model.

### 8.9 AI tasks by scope and data source
The same loop, tools and context pack serve all scopes, all data sources and all backends. The ImageSet (3.2) makes images from E57, SLAM and photogrammetry look identical to the tools. The context pack states the data source and the noise estimate, so the model reads deviations against the right accuracy level.

Indoor structure:
- Check wall axes and thickness against sections and photos.
- Check that doors and windows sit in the right wall and have plausible sizes, sills, reveals and operation types.
- Flag missing, duplicate or merged walls.
- Judge wall type (interior, exterior). load_bearing stays unknown unless there is evidence.
- Name spaces.

Indoor furniture (only with structure_and_furniture): choose among the candidates of section 9, never invent dimensions.

Outdoor:
- Confirm that buildings are separated correctly (merged or split).
- Judge roof type from photos and plane arrangement.
- Find non-ground objects in the terrain (vehicles, hedges, walls, piles) and non-building objects in building clusters (sheds, carports, trees).
- Flag glass roofs and reflective areas.
- Judge terrain anomalies against photos.

indoor_outdoor:
- Review conflicts between the exterior shell and the outer wall faces of the interior. Propose which source to trust. Never average silently. Q14 decides the policy.

All scopes:
- Suspicious classification and class conflicts.
- The AI changes the model only through apply_patch. Geometry numbers come only from tool results.

Privacy setting ai.send_images: photos and renders from the point cloud count as images. With the setting off, the AI works on the scene summary, measured values and tool results only. Tasks that need images are skipped and their elements stay in the review queue as unsure.

Cost: because the AI runs every time, the cache, the cost or call cap per room or building and the stop rules in 8.8 are mandatory.

## 9. Furniture and objects

Only active when indoor_detail is structure_and_furniture. Otherwise skip this section completely.

Furniture comes from three sources. All of them produce editable objects with a type, and the user can pick among the candidates in the viewer.

### 9.1 Parametric furniture templates (the core)
Raumlot ships its own parametric templates, implemented in code with a parameter schema like section 5.1:
- table (rectangular, round, oval), desk, chair, office chair, sofa, cabinet, shelf, sideboard, bed, kitchen run, and the sanitary objects washbasin and toilet.
- Parameters per template, for example a table: width, depth, height, top thickness, top shape, leg count, leg profile, leg inset. A shelf: width, depth, height, board count, board thickness.
- Scripts fit the template parameters to the instance points: slice at the characteristic heights (for example the table top), fit circle, ellipse, rectangle and free polygon to the outline, the smallest residual wins. The circle versus ellipse threshold on the axis ratio is a config value (start at 1.05, tune on the evaluation set).
- The template choice comes from the instance class, the dimensions and, where unclear, the AI (it picks the template and the part structure, never the numbers).
- Result: IfcFurniture with IfcFurnitureType, sanitary objects as IfcSanitaryTerminal with IfcSanitaryTerminalType. Templates are always parametric and easy to adjust.

### 9.2 Furniture catalog from ready-made IFC objects
- Like the object library in ArchiCAD, Raumlot keeps a catalog of ready-made objects in library/.
- Source A (recommended): the user places objects from the ArchiCAD library in a dummy project and exports them as IFC. GDL objects cannot be read directly, so the IFC export is the path. `raumlot library import <file.ifc>` turns every furniture element of the file into a catalog entry: id, name, IFC class, predefined type, dimensions, geometry (stored as the IFC representation plus a tessellated copy for matching), preview image, source and terms of use.
- Source B: manufacturer BIM objects in IFC (for example from BIMobject or the NBS National BIM Library), downloaded manually by the user and imported the same way.
- Research datasets such as ShapeNet, 3D-FUTURE and ABO have restrictive licenses. Record the license of every entry. This is a personal project, but a later sale or company use would change what is allowed.
- Catalog entries are not parametric. They can be placed, rotated and scaled within the allowed range (default plus or minus 5 percent).

### 9.3 Matching and choice
The pipeline places the best fitting object automatically. The choice in the viewer is an optional correction, not a required step.

Order of attempts per instance:
1. Template fit (9.1) and catalog match (9.2) run side by side.
   - Catalog match: compare the instance points to each entry of the matching class. Search yaw about the vertical axis and scale within the allowed range. Use one-sided distance (scan to model) and coverage.
   - Keep the top 3 candidates over templates and catalog entries, with deviation and coverage.
   - If the best candidate is within tolerance and clearly ahead of the second (configurable margin), the script places it without AI.
   - If several candidates are within tolerance but close to each other, the AI sees the anonymized photo crop and the candidate overlays and picks one, or declares unsure.
2. Create a new object (no candidate within tolerance). The AI looks at the anonymized photo crops and the instance summary and proposes the object structure: which template fits best and which variant parameters apply (for example leg count, top shape, number of boards), or a new part structure built from template parts (top, leg set, seat, back, base, carcass, doors, drawers) with the profile per part. The AI gives no dimensions. The script fits all numbers to the points. The result is a new parametric object.
3. Mesh from points: for organic or designer shapes that step 2 cannot describe, a Poisson or alpha-shape mesh from the fused instance cloud, simplified, exported as a tessellated face set. Hidden sides are filled by symmetry and marked as assumed. Non-parametric.
4. Oriented box, flagged as simplified and shown red in the review.

A result that looks clean but deviates from the points is worse than an honest box. The deviation check decides, not the appearance.

### 9.4 Growing catalog
Every new object that passes the deviation check is saved to the catalog automatically, so the choice grows with every project and later matches get better.
- Saved per entry: the parametric definition (template id or part structure plus parameter values), dimensions, IFC class and type, preview image, the source project and run, the AI backend and model that proposed the structure, deviation and coverage at creation, and the status generated.
- Duplicates are avoided: an entry that matches an existing one within tolerance (same structure, dimensions within the type fusion tolerance) only increases the use counter of the existing entry.
- Entries carry a status: generated (created automatically), reviewed (confirmed or corrected by the user in the viewer), imported (from an IFC file, 9.2). Matching prefers reviewed and imported entries over generated ones when the deviation is equal.
- The catalog lives in library/ (index plus one folder per entry) and is shared across projects. Previews are rendered from the model, never from photos, so the catalog contains no image of a scanned site.
- The user can rename, merge, correct or delete entries in the viewer. Deleting an entry never changes models that already use it; they keep a copy of their definition.
- The catalog is versioned with the run that changed it, so a project run stays reproducible with the catalog state it used.

Choice in the viewer (section 12.6): clicking a furniture element shows the placed object and its other candidates with preview, deviation and coverage. One click on another candidate swaps the object through a patch. A catalog search with filters by type and dimensions is available. Correcting an object marks its catalog entry as reviewed.

Type fusion:
- Identical instances share one type (IfcFurnitureType with many occurrences). Before merging, check that dimensions agree within tolerance. A free-standing instance can fill the gaps of an instance under a table (point fusion in the type frame). Coverage is reported per instance.

## 10. IFC mapping

Goal: the IFC arrives in ArchiCAD like a model that was drawn in ArchiCAD. Walls, slabs, doors, windows and zones must be recognized there as native, editable elements with types, layers, properties and quantities. A collection of proxies is not acceptable.

Schema: IFC4 (IFC4 ADD2 TC1) by default. The consuming software is ArchiCAD (version in Q7). Check the current ArchiCAD IFC import documentation (supported schema versions, model view definitions, which IFC structures it converts into native elements) before finalizing the writer. IFC4.3 only after that check. Use the ifcopenshell API, current version.

Spatial structure: IfcProject, IfcSite, IfcBuilding, IfcBuildingStorey with correct elevations and names. Units: meters, square meters, cubic meters, radians or degrees as declared.

Georeferencing: IfcMapConversion and IfcProjectedCRS using the stored origin offset and the project CRS (default candidate EPSG:2056, height system LN02 or LHN95, confirm in Q4). The model must round-trip: the local offset plus the map conversion reproduce the original coordinates. For outdoor scope the georeference is mandatory. Without a verified georeference the export is marked as unreferenced.

| Scene element | IFC |
|---|---|
| Wall | IfcWall (PredefinedType STANDARD or as fitting) with an IfcWallType, Axis representation (curve 2D) and Body representation (SweptSolid, rectangle profile extruded along the axis), IfcMaterialLayerSetUsage with the layer set, Pset_WallCommon (IsExternal, LoadBearing, Reference) |
| Wall join | IfcRelConnectsPathElements with IfcConnectionTypeEnum (ATSTART, ATEND, ATPATH). Whether ArchiCAD uses the relation for clean corners is tested in M1 and recorded in an ADR. The exported wall bodies are already cut correctly, so the model is right even if the relation is ignored. |
| Floor | IfcSlab (FLOOR or BASESLAB) with an IfcSlabType and IfcMaterialLayerSetUsage, arbitrary closed profile extruded, Pset_SlabCommon |
| Ceiling | IfcCovering (CEILING) or IfcSlab (configurable). Decide the default in an ADR after testing the ArchiCAD import. |
| Opening | IfcOpeningElement with IfcRelVoidsElement to the wall |
| Window, Door | IfcWindow and IfcDoor with IfcWindowType and IfcDoorType (operation type, partitioning type), IfcRelFillsElement to the opening, OverallWidth and OverallHeight, lining and panel properties where the schema provides them, Pset_WindowCommon and Pset_DoorCommon |
| Window sill | Decide in an ADR: part of the window body plus properties, or separate element |
| Stair | IfcStair with IfcStairFlight, Pset_StairCommon (riser count, riser height, tread length), fallback simplified solid flagged |
| Furniture | IfcFurniture with IfcFurnitureType via IfcRelDefinesByType. PredefinedType (CHAIR, TABLE, DESK, SHELF, SOFA, BED and so on as available in the schema) on the type object, and on the occurrence only where the schema version has the attribute (check). USERDEFINED with ObjectType otherwise. Sanitary objects as IfcSanitaryTerminal with its type. |
| Room | IfcSpace (as zones in ArchiCAD) with name, long name, number, Qto_SpaceBaseQuantities, Pset_SpaceCommon, linked to its boundary elements by first level IfcRelSpaceBoundary |
| Terrain | Decide in an ADR: IfcGeographicElement with PredefinedType TERRAIN, or the IfcSite representation. Body as IfcTriangulatedFaceSet. Check the schema for the allowed combinations. |
| Building (outdoor) | IfcBuilding with simplified envelope. Decide in an ADR: IfcWall and IfcRoof elements, or IfcBuildingElementProxy envelope. In indoor_outdoor scope the exterior and the interior belong to the same IfcBuilding. |

Optional classification: IfcClassificationReference per element (system in Q7, for example eBKP-H or the ArchiCAD classification).

Custom property set Raumlot_Quality on every element: provenance, parameter origins, deviation rms/p95/max, coverage, confidence, status, tolerance profile, data source, locked.

### 10.1 Mandatory attributes

Principle: more information is better than less. Every exported element carries all of the following. If mandatory data is missing, the element is still exported but flagged, listed in the QA report, and the export is marked incomplete.

1. Dimensions. Quantities in the standard Qto sets for the element type (check the current IFC4 ADD2 TC1 definitions for the exact names):
   - walls: length, thickness, height, areas, volume
   - slabs and coverings: thickness, areas, perimeter, volume
   - openings, windows and doors: width, height, area, sill height
   - stairs: rise, run, width, step count
   - furniture: width, depth, height, and area or volume where available
   - spaces: height, floor area, volume, perimeter
   - terrain and outdoor buildings: area, height, volume where defined
   Candidate set names to verify in M1: Qto_WallBaseQuantities, Qto_SlabBaseQuantities, Qto_CoveringBaseQuantities, Qto_OpeningElementBaseQuantities, Qto_WindowBaseQuantities, Qto_DoorBaseQuantities, Qto_StairFlightBaseQuantities, Qto_SpaceBaseQuantities; stair counts go into Pset_StairCommon (NumberOfRiser, NumberOfTreads). M1 fixes the mapping table in docs/IFC_MAPPING.md. Values without a standard quantity (for example furniture, terrain) go into Raumlot_Quality.
   Each dimension also has its origin (measured, fitted, snapped, template, assumed, manual) in Raumlot_Quality.
2. Element identity. IFC class and PredefinedType, Name, Description, ObjectType, Tag (the stable uuid), a type object via IfcRelDefinesByType, material or material layers where known, template or catalog id for furniture.
3. Place in the spatial hierarchy: site, building, storey and room.
   - Express it through IFC relations (aggregation, IfcRelContainedInSpatialStructure, first level IfcRelSpaceBoundary with connection geometry for walls, floors and ceilings; openings are linked through their host wall, second level boundaries come later).
   - Repeat it as plain properties in the property set Raumlot_Location: SiteName, BuildingName, StoreyName, StoreyElevation, SpaceNames, SpaceNumbers.
   - Walls, doors and windows list all adjacent spaces. Furniture lists its containing space.
   - Outdoor elements have site and building but no storey or room. Write those properties with the value "not applicable" and never leave them out.
4. Coordinates. A correct ObjectPlacement in the local model frame. In Raumlot_Location also the reference point X, Y, Z and the bounding box minimum and maximum in the project CRS (map coordinates derived with the IfcMapConversion), the CRS name or EPSG code and the height system. A test checks that these values reproduce the source cloud positions.
5. Quality. Raumlot_Quality as defined above, plus the run id and the AI backend and model id used.
6. User properties: the properties added in the viewer (section 5.1) in their standard property set or in Raumlot_User.

IDS gate: generate an IDS (Information Delivery Specification) file from this list, one specification per element type, in specs/raumlot.ids. Check the current IDS standard and IfcTester versions. Every export runs against it.

Room assignment can fail for walls between several spaces, in open-plan areas and near boundaries. Flag these cases and never guess silently.

### 10.2 Validation

After every export: ifcopenshell.validate, IfcTester with the IDS file from 10.1, and a re-import test that compares counts, dimensions and relations.

ArchiCAD acceptance (part of every milestone that changes the IFC writer): the user imports the IFC into ArchiCAD and checks the list in docs/IFC_MAPPING.md:
- walls arrive as native walls with the right thickness, height, layers and clean corners,
- slabs and ceilings arrive as native slabs or ceilings,
- doors and windows sit in their walls, cut them, and carry width, height, sill and operation type,
- zones arrive with name, number, area and volume,
- storeys have the right names and elevations,
- property sets and quantities are visible,
- the georeference is correct.
Bonsai (Blender) or BIMvision serve as an extra check without an ArchiCAD license. An export that fails the IDS check is marked incomplete and lists the missing attributes per element.

## 11. Floor plans

- Indoor scope only. Generated from the scene model with shapely sections, not from the IFC.
- Section height above storey floor is configurable (default 1.0 m).
- Output: DXF (ezdxf, layers per element class), SVG, PDF (check the current options, for example rendering the SVG with a maintained library).
- Content: wall poche, openings with window symbols and door swings, stairs, furniture outlines (if enabled), space labels with name and area, optional dimension chains, north arrow and scale.
- One plan per storey. Optional reflected ceiling plan.
- Plans update when the model changes in the review UI.
- Outdoor scope: a site plan with building footprints as DXF and SVG. Contour lines from the terrain are optional and come later.

## 12. User interface

Desktop app (PySide6, renderer decided in M8). The UI contains no pipeline logic. It calls the service layer. The viewer (M8) comes before the wizard (M11), because the review of real results is needed first. Until the wizard exists, projects are created with `raumlot init`.

### 12.1 Project wizard
Step 1: data source. tls_stationary, slam or photogrammetry. The next steps adapt to it.
Step 2: scope and detail. indoor_outdoor, indoor_only or outdoor_only. For indoor scope: structure_only or structure_and_furniture. For outdoor scope: terrain and building options. Image mode with_images or no_images.
Step 3: inputs.
- Load an E57 file (points and images, no classification needed) or a LAS or LAZ file (shows header, point count, classes found, CRS). With an E57 the images come from the same file. The panel shows the output of `raumlot inspect`: scans, images, camera types, resolutions and the derived visibility mode per image group.
- Images and cameras (needed when the points come from LAS or LAZ): E57 for images only, or a photogrammetry export (COLMAP, Metashape, Pix4D, generic), or a SLAM photo set. The panel previews the camera positions in 3D together with the cloud.
- Optional: SLAM trajectory and calibration, ground control points, reference IFC, furniture catalog.
Step 3b: intake settings (6.1). Anonymization on or off (default on), anonymization classes (default people, license plates, computer screens) with English prompts, method and strength, gray value for anonymized points, SAM version and checkpoint (default 3.1, SAM 3 selectable), confidence and retry thresholds, GPU memory budget (default 20 of 24 GB), cache folder with free disk check. The wizard shows a short warning that no tool guarantees complete anonymization.
Step 4: class mapping table (class ID to class name, with defaults from configs/classes.yaml, user must confirm). Indoor and outdoor classes separately.
Step 5: tolerance profile (tls, slam, photogrammetry) and values, editable.
Step 6: AI settings. Backend choice (openrouter default, claude_subscription, gemini_subscription, codex_subscription, direct APIs), key field for API backends (password style), login status for subscription backends, model picker with capability badges, price or "subscription" and context length, per-task model assignment, qualification test button, send_images toggle (works on anonymized images only, 6.1), privacy options, cost or call cap. The AI is on by default. A script-only switch exists for tests and for runs without a backend. The wizard warns that non-ok elements then go unreviewed to the review queue.
Step 7: summary with the checks that passed or failed, then start.
The wizard validates before it starts. Examples: photogrammetry without camera intrinsics cannot start, a model without image input cannot be assigned to an image task, no_images requires a classified cloud.

### 12.2 Run panel
Stage list with progress, logs, elapsed time, AI token, cost or call counter, GPU memory, RAM and disk counters, anonymization status, AI backend and send_images state, cancel and resume. Runs unattended.

### 12.3 Review mode (the main screen)
- 3D viewport with point cloud, model and camera positions together, with display toggles per class, per instance, per element, per camera group, including terrain and buildings. Color modes: class, instance, RGB, tolerance view (12.4). Navigation, clip box and model tree follow 12.4. Camera mode follows 12.5.
- Large-cloud handling: voxel-reduced display set (target 5 to 10 million points), level of detail, full resolution on demand in a region. Display uses an origin offset in float32, source data stays float64.
- Element list with filters (status, type, storey, provenance, locked, parametric or not) and counts.
- Click on a point or element: selects it and opens the attribute panel (12.6). Double click on a point: opens the best anonymized photo of that location in camera mode. Click in a photo jumps to the 3D position.
- Editing (12.6): attributes, properties and parameters. Later (M12): drag wall ends and opening edges, split or merge instances, reassign class, add or delete elements, lock and unlock. Every edit is a patch. Undo and redo.
- Section tool and clip box (12.4) with measuring.
- Plan tab: live 2D plan from the current model.
- Export panel: IFC, DXF, SVG, PDF, colored LAS or LAZ, QA report.
- Review queue: the list of items the pipeline could not settle, sorted by severity, with next and previous navigation.

Do not build a full CAD system. Parameter fields and drag handles are enough. Detailed design work continues in ArchiCAD.

### 12.4 Viewer requirements

Navigation
- Smooth orbit, pan, zoom and walk mode with point cloud, model and camera markers together. The default target is at least 30 frames per second during interaction on the target hardware (Q11), recorded in docs/PERFORMANCE.md.
- Out-of-core display: an octree or tile hierarchy with level of detail, loaded asynchronously. Interaction never waits for loading. Lower detail while moving, full detail when still. The display budget in points is configurable.
- The renderer is decided by measurement in an ADR in M8. Candidates: PySide6 with pyvistaqt, the PySide6 GUI of Nomivox as a starting point, Qt with a web view and an octree viewer, a custom OpenGL or wgpu renderer. The benchmark runs on a real cloud of 50 million points. VTK-based viewers need level of detail for clouds of this size, so do not choose by assumption. Camera mode (12.5) with photo blending is a hard requirement for the choice.
- Picking: click a point, an element or a camera marker. Distance measurement between two points. Snap to element edges.
- Saved views (bookmarks), standard views (top, front, side), perspective and orthographic.

Clip box
- One clip box (limit box) for the whole scene. It cuts the point cloud and the models at the same time.
- Controls: drag handles on the faces, sliders per axis, rotation about the vertical axis, numeric input, reset.
- Presets: from the selected storey (floor to ceiling with margin), from the selected room, from the selected element, from the current view.
- Section slab mode: a thin slice with configurable thickness in an orthographic top, front or side view, for plan and section inspection. Hide-above mode for plan views.
- The clip box state is saved with the bookmarks.

Model tree
- Tree: Project, Site, Building, Storey, then spaces and element groups (walls, floors, ceilings, openings, stairs, furniture), then the elements. Outdoor branch: terrain and buildings. Point cloud branch: classes. Camera branch: camera groups and cameras.
- Every node has a visibility checkbox, counts and status badges (ok, warning, fail, unsure, locked).
- Click a storey: show this storey only and set the clip box to it. A button restores the full view.
- Click a room or an element: zoom, isolate and open its attribute panel.
- Search and filters by name, type and status.

Tolerance view (point cloud colored by deviation)
- Green: points within the tolerance. Red: points in front of the model surface beyond the tolerance. Blue: points behind the model surface beyond the tolerance. Colors are configurable.
- Only points that matter by class are colored. These are the points assigned to a modeled element (walls, floors, ceilings, windows, doors, stairs, furniture, terrain, buildings). All other points stay neutral gray or are hidden by a toggle.
- The tolerance per element type comes from tolerances.yaml. A tolerance slider recolors live. The signed distance per point is computed once and cached together with the element id. Recoloring changes only a threshold in the shader and costs no recomputation.
- A legend with a histogram of the signed deviations per element, per class or for the whole project, with the tolerance marks.
- Click a colored point to see element, signed distance and tolerance.
- The tolerance view works together with the clip box and can show colored points only inside the box.

Export
- Colored point cloud as LAS or LAZ: RGB set to the tolerance colors, extra dimensions for the signed deviation in meters, the element id and the element type. Options: whole project, only the clip box region, only relevant classes. This export exists from M4 on as a CLI command, so results can be checked in Cyclone 3DR before the viewer exists.
- Screenshots and saved views as PNG.
- IFC, DXF, SVG, PDF and the QA report from the export panel.

### 12.5 Camera mode
- Camera positions are shown as markers: a small frustum for pinhole and fisheye cameras, a sphere for spherical cameras, colored by camera group. They can be shown and hidden per group.
- Click on a camera marker (or a camera in the model tree, or next and previous buttons): the view moves exactly into that camera, with its pose and its camera model. Spherical images can be looked around freely from the camera position. Pinhole images keep their field of view.
- Layers in camera mode, from back to front: the anonymized photo, the point cloud, the model. Each layer has its own opacity slider from 0 to 100 percent, so any blend is possible. Presets: photo only, photo with model wireframe, photo with model surfaces, point cloud with model, model only.
- The model can be drawn as surfaces, as wireframe or as edges. The tolerance view colors also work in camera mode.
- Elements can be clicked in camera mode and open the attribute panel (12.6).
- Leaving camera mode returns to the free navigation at the same position.
- The photo is always the anonymized image of the ImageSet. Original images are never shown.

### 12.6 Attribute panel and editing
Clicking an element (in 3D, in camera mode, in the model tree or in the element list) opens the attribute panel. It shows everything the pipeline stored for the element:
- identity: IFC class, predefined type, type object, name, description, tag, material or layers,
- location: site, building, storey, spaces,
- parameters (section 5.1) with value, unit and origin tag,
- quantities (derived, read only), property sets, user properties,
- quality: deviation metrics, coverage, confidence, status, notes, AI comments, provenance, locked state,
- for furniture: the candidate list (section 9.3).

Editing in the panel:
- attributes and properties: change name, description, type, material, property set values, add and remove user properties,
- geometry: change any parameter in its field with unit, range check and live preview. Dependent elements follow through the dependency graph (an opening moves with its wall, the room area updates),
- lock and unlock,
- every change is a patch with undo and redo. Changed parameters get origin manual.
Non-parametric elements (terrain, mesh fallbacks) allow placement and properties only.

## 13. Repository layout and documentation

```
D:\Raumlot\
  pyproject.toml
  noxfile.py
  README.md
  CLAUDE.md
  .gitignore            (models/, test_PW/, .env, .codex-tools/, graphify-out/, project caches)
  .env.example
  models/               (local SAM weights and assets, never committed)
  test_PW/              (local real test data, never committed)
  native/               (Rust crate with PyO3 bindings, benches, tests; minimal until a kernel is needed)
  configs/              (classes.yaml, tolerances.yaml, pipeline.yaml, ai_models.yaml)
  presets/              (default.json adopted from Nomivox)
  docs/
    MASTERPROMPT.md
    MASTERPROMPT_CHANGES.md
    DECISIONS.md
    CHANGELOG.md
    adr/
    (created when a milestone first touches them:)
    ARCHITECTURE.md, PIPELINE.md, DATA_MODEL.md, MODES.md, TOLERANCES.md,
    PERFORMANCE.md, INTAKE.md, AI_TOOLS.md, AI_MODELS.md, IFC_MAPPING.md,
    UI.md, VIEWER.md, TESTING.md
  library/              (furniture catalog index, imported entries, previews, terms of use)
  specs/                (raumlot.ids)
  src/raumlot/
    io/                 (e57, las, cameras, importers for photogrammetry and slam)
    alignment/
    visibility/
    intake/             (seg, anonymize, vote, mirror, presets, vram planner, report)
    segmentation/       (instance refinement)
    structure/          (interior, exterior)
    furniture/          (templates, catalog, matching)
    model/              (schema, parameters, geometry, dependency graph, patches)
    ai/                 (provider interface, backends, model discovery, context builder, tools, schemas, prompts, anonymized-images-only gate)
    ifc/
    plans/
    qa/
    service/
    cli/
    ui/
  tests/
    synthetic/          (generators)
    unit/
    integration/
    adopted/            (tests taken over from Nomivox)
    realdata/           (marked realdata, read RAUMLOT_TESTDATA)
    benchmarks/
```

Documentation rule: every milestone updates the affected docs. A feature without docs is not done. A doc file is created when a milestone first needs it, not as an empty skeleton in M0. Prompts for the AI live as versioned files in src/raumlot/ai/prompts/ and are documented in AI_TOOLS.md.

## 14. Testing and evaluation

### 14.1 Synthetic ground truth (build this first)
- A generator builds a parametric room set (walls, floor, ceiling with configurable sag, windows with sills, doors, a stair, furniture from the templates) and writes it as a reference scene JSON and a reference IFC.
- A second generator builds an outdoor scene: sloped terrain and several buildings with different roof shapes, with a reference IFC.
- A simulator samples points from the reference surfaces with Gaussian noise (configurable, for example 0.5 to 2 cm for TLS and larger for SLAM and photogrammetry), simulates occlusion by ray casting from virtual scanner positions, assigns class labels with a configurable error rate, and writes E57, LAS and LAZ.
- Synthetic cameras with known poses and intrinsics (pinhole with distortion, fisheye, spherical) write ImageSets in the formats of the importers, including E57 Image2D elements. The images are label renders of the reference scene, so that the fake segmentation provider (14.6) can produce exact masks. This tests the pose conversion, the projection, the visibility, the lifting and the voting without real photos and without a GPU.
- Fixtures avoid exact ties: points are not placed on voxel or cell borders, noise is added to lines and grids, parameters match production values.
- The pipeline runs on these files. Output is compared with the reference.

### 14.2 Metrics
- Element detection: precision and recall per type
- Position error and dimension error per element (mean, p95, max)
- Terrain deviation and building footprint, roof and height errors
- Class accuracy for furniture type
- Shape accuracy (round, oval, rectangular, L-shaped)
- Anonymization recall per class and per data source (people, license plates, screens)
- Class accuracy and instance split quality from the intake
- Share of instances accepted without AI
- AI rounds, tokens or calls and cost per room, per backend
- IFC validity (zero validation errors), IDS pass rate, round-trip counts, ArchiCAD checklist result
- Runtime and peak memory per million points

### 14.3 QA report
HTML and JSON per run: project setup, visibility mode, counts by status, element table with metrics, noise estimate, tolerance warnings, alignment score, anonymization state, AI usage, backend and model, review queue, thumbnails of the worst elements. A minimal version exists from M4 on.

### 14.4 Real data and model comparison
- At least 4 different scans, 15 to 20 objects. Split by scan into development and hold-out. Tune only on development. Report on hold-out. Include at least one photogrammetry dataset and one outdoor dataset.
- Model comparison harness: run the same fixed inputs through a configurable list of backends and models, compare deviation after fitting, rounds, valid JSON share, qualification pass rate and cost or call count. Write the result to docs/AI_MODELS.md.
- Anonymization test: scans with people, license plates and computer screens, with hand-labeled regions. Measure recall per class, reported separately for each data source. The user sets the target recall.
- External check: the user verifies results independently in Cyclone 3DR. The exports must open there: the colored LAS or LAZ (12.4), the camera marker export (3.2) and a model format that Cyclone 3DR reads (Q15). Document in docs/VIEWER.md how to repeat the check. Cyclone 3DR is a commercial tool, so it is never a dependency and the pipeline never calls it.
- ArchiCAD check: see 10.2.

### 14.5 Performance benchmarks
- Benchmarks for ingest, index build, intake per image view, visibility, structure extraction and the full pipeline on synthetic data of several sizes and on the real datasets. Viewer benchmarks measure the frame rate during navigation, clip box interaction and camera mode on a cloud of 50 million points. Intake benchmarks measure peak VRAM, peak RAM and time per unit on the RTX 4090 and run the large synthetic project with many scan positions. Record time and peak memory. Compare against the budgets in docs/PERFORMANCE.md.

### 14.6 Quality gates and test tiers
- Fake providers make every default test run without GPU and network:
  - FakeSegmentationProvider: produces masks from the label renders of the synthetic scene (exact ground truth).
  - FakeAIProvider: scripted or recorded answers, including invalid JSON and wrong tool calls for the error paths.
- pytest markers: gpu (needs CUDA and SAM weights), realdata (needs RAUMLOT_TESTDATA), network (needs an AI backend), slow.
- nox sessions:
  - `nox -s check`: ruff, mypy, pytest without the markers gpu, realdata, network and slow. Must be green after every WP.
  - `nox -s gpu`, `nox -s realdata`, `nox -s network`: the marked tests, run at the end of each milestone where they apply.
  - `nox -s bench`: benchmarks against the budgets.
  - `nox -s native`: cargo test and the maturin build, once native code exists.
- Every milestone needs: `nox -s check` green, the applicable marked sessions green, IFC validation and IDS check clean, benchmarks within budget, docs updated, the demo command runs.

### 14.7 Real test data
- Test data lives outside git in D:\Raumlot\test_PW. Tests find it through the environment variable RAUMLOT_TESTDATA. Test data never leaves the machine and is never sent to an AI backend unless it went through the intake and the user allowed it.
- eingang_buero.e57 (182 MB): a SLAM scan of an entrance area with a room, a corridor, windows and interior furnishings. It holds 1 scan with about 1.05 million points (XYZ, intensity, RGB, normals, no timestamps, no station index) and 29 spherical images of 8192 by 4096 pixels, each with its own pose, all associated with that scan. Visibility mode free_camera. It is the reference dataset for the milestone demos M2 to M5 and M8 to M10 and the fast real-data smoke test.
- pointcloud.e57 (1.38 GB): second, larger dataset. Inspect it in M0 with `raumlot inspect` (or the adopted Nomivox inspector) and record its content in docs/DECISIONS.md. Used for load and memory tests.
- `raumlot e57 crop` writes small real fixtures (a box region, a few images) for fast realdata tests.
- More datasets (TLS stationary, outdoor, scans with people, license plates and screens) are listed in Q17.

## 15. Milestones

Order: a command line path from E57 to IFC comes first and is tested on real data (v0.1 = M0 to M5). Viewer, AI, furniture and the desktop app follow. Each milestone ends with a demo command and acceptance criteria. Stop and wait for the user after each. The WP lists are the starting point. Claude Code refines them at the start of each milestone and keeps every WP small enough for one worker brief.

### M0 Scaffold and decisions
Goal: a working, checked repository and all decisions needed for M1 to M3.
WPs:
1. git init, .gitignore (models/, test_PW/, .env, .codex-tools/, graphify-out/), pyproject.toml with uv, Python 3.12, ruff, mypy, pytest, nox sessions (14.6), empty package raumlot with the CLI entry point `raumlot --version`.
2. Graphify set up project-locally, entries in .git/info/exclude.
3. Minimal Rust extension with PyO3 and maturin, built and imported on Windows (`nox -s native`).
4. Environment check: one environment with torch CUDA, the pinned sam3 commit, ifcopenshell, open3d, laspy with lazrs, pye57, PySide6. Settle the numpy version (Q18) in an ADR.
5. SAM smoke test (marker gpu): load models/sam3.1_multiplex.pt with the image predictor and segment one image from eingang_buero.e57. Fallback SAM 3 by path.
6. Inspect both real datasets and record their content.
7. Ask the questions of section 16 marked M0 in one batch, record the answers in docs/DECISIONS.md.
8. ADRs: 0001 language and performance (4.1), 0002 Nomivox adoption (4.2) with the source commit, 0003 environment and numpy. Performance budgets after Q11 in docs/PERFORMANCE.md. CLAUDE.md derived from this file.
Demo: `nox -s check`, `nox -s native`, `nox -s gpu -- -k sam_smoke`, `raumlot --version`.
Accepted when: questions answered and recorded, the checks run locally and are green, the Rust extension builds and imports on Windows, the SAM checkpoint decision is recorded.
Not in M0: any pipeline code.

### M1 Scene model, parameters, patches, IFC export, synthetic generator
Goal: a synthetic room becomes a valid, ArchiCAD-ready IFC from parameters.
WPs:
1. Pydantic scene model with project settings, element base and the parameter schemas of 5.1 (walls, wall joins, slabs, ceilings, openings, windows, doors, spaces).
2. Geometry module: geometry from parameters, wall joins, openings cut into walls, space boundaries and quantities.
3. Dependency graph and recomputation.
4. Patch log with forward and inverse operations, undo and redo, lock rule, schema check.
5. IFC writer (section 10) for walls with types and layers, wall joins, slabs, ceilings, openings, windows, doors, spaces, storeys, georeferencing, Raumlot_Quality, Raumlot_Location, Qto sets.
6. IDS file generation and the validation chain of 10.2.
7. Synthetic room generator with reference scene JSON and reference IFC.
Demo: `raumlot synth room --out demo_room && raumlot export demo_room --format ifc`.
Accepted when: the synthetic room exports to a valid IFC that passes the IDS check and the re-import test, a parameter patch (for example wall thickness) updates the dependent opening and room area, undo restores the state exactly, and the user confirms the ArchiCAD checklist of 10.2 on the demo IFC.
Not in M1: point clouds, stairs, furniture, outdoor.

### M2 Nomivox port and ingest
Goal: E57 and LAS/LAZ projects are ingested on the command line with correct cameras.
WPs:
1. Port the Nomivox modules of 4.2 (io, cameras, visibility, store, las output) with their tests into raumlot. Adopted tests green.
2. Typed settings replace the Nomivox config dict for the ported modules.
3. ImageSet model, visibility mode derivation, conversion layer for poses and camera models with synthetic camera tests.
4. LAS and LAZ chunked reading and the on-disk index (ADR for the index format), input hashing and the stage cache.
5. `raumlot init`, `raumlot inspect`, `raumlot ingest`, `raumlot export --format cameras`.
6. Synthetic E57 writer for tests (points plus Image2D with spherical and pinhole cameras).
Demo: `raumlot inspect test_PW/eingang_buero.e57`, `raumlot init proj --source test_PW/eingang_buero.e57 --data-source slam --scope indoor_only`, `raumlot ingest proj`, `raumlot export proj --format cameras`.
Accepted when: the adopted tests and the new tests are green, the 29 cameras of eingang_buero.e57 are listed as spherical with free_camera mode and sit at the right place in Cyclone 3DR together with the cloud, a 50 million point synthetic LAZ is ingested within the budget and with flat memory.
Not in M2: SAM, viewer, photogrammetry importers other than E57.

### M3 Intake: anonymization and segmentation
Goal: stages 1 to 3 as one block (6.1).
WPs:
1. Port seg (SAM3Backend, MaskCache, tiling), vote (VoteStore and post-processing), mirror and presets with their tests.
2. Segmentation provider interface with the SAM provider and the FakeSegmentationProvider. Label renders in the synthetic camera generator.
3. Alignment test (stage 1) with score and stop rule.
4. Visibility providers for station and free_camera with compressed depth maps.
5. Anonymization: prompts and thresholds from 4.2, retry pass, pixelation, gray points, anon_flags, anonymized ImageSet with run id, the image gate and its test.
6. Instance ids from masks and cross-view merge.
7. VRAM planner, per-unit processing, scan level checkpoints, free disk check.
8. Labeled LAS or LAZ export, intake report with sample gallery.
9. Large synthetic memory test (165 scan positions, fake provider) and ADR SAM 3 against SAM 3.1.
Demo: `raumlot intake proj` on eingang_buero.e57, `raumlot export proj --format las --labeled`, open the intake report.
Accepted when: eingang_buero.e57 runs through on the RTX 4090 and gives a labeled cloud and an anonymized ImageSet, the sample gallery shows pixelated people, license plates and screens on test images that contain them (Q17), a test proves that no original image reaches the AI layer or the viewer, the alignment score is reported, occluded points are excluded, the synthetic project with 165 scan positions runs with flat peak memory, and peak VRAM and RAM stay within the budgets.
Not in M3: second SAM pass, instance refinement.

### M4 Interior structure and tolerances
Goal: the first real IFC from eingang_buero.e57.
WPs:
1. Noise estimate and the tolerance profiles (slam profile proposed from the measured noise).
2. Storeys, floors and ceilings with rule B.
3. Walls with rule A, thickness, wall joins, assumed thickness for one-sided walls.
4. Spaces and room assignment with flags.
5. Signed deviation per point, metrics and status, colored LAS or LAZ export (12.4).
6. Re-run policy (5) with tests.
7. Minimal QA report (HTML and JSON) and `raumlot run` for ingest to IFC.
Demo: `raumlot run proj --ai off`, open the IFC in ArchiCAD, open the colored LAZ in Cyclone 3DR.
Accepted when: the synthetic evaluation reaches the target errors set in docs/TOLERANCES.md, eingang_buero.e57 gives plausible walls, floors, ceilings and rooms in the tolerance colors, the IFC passes validation and IDS and the user confirms the ArchiCAD checklist.
Not in M4: openings, stairs, furniture, AI.

### M5 Openings and stairs
Goal: doors, windows and stairs complete v0.1.
WPs:
1. Opening detection and measurement (width, height, sill, reveal, sill projection, side) with assumed values where not visible.
2. Windows and doors with types and operation type, IFC relations (void and fill).
3. Stairs (if present in the data, otherwise synthetic only).
4. Synthetic evaluation of opening dimensions, QA report update.
Demo: `raumlot run proj --ai off` on eingang_buero.e57.
Accepted when: opening dimensions on synthetic data are within the opening target, IFC relations validate, the windows and doors of eingang_buero.e57 are found and sit in their walls in ArchiCAD.

### M6 Floor plans
DXF, SVG and PDF per storey from the scene model (section 11). Demo: `raumlot export proj --format dxf,svg,pdf`. Accepted when: plans match the model sections and open cleanly in a CAD viewer and in ArchiCAD.

### M7 Outdoor mode
Terrain model, building models, IFC export with georeference, indoor_outdoor constraint handling, site plan. Accepted when: the synthetic outdoor scene reaches the tolerances confirmed in Q13, a real outdoor dataset gives a plausible terrain and buildings in the colored cloud, the IFC validates.

### M8 Viewer
Goal: review the result visually and edit attributes and parameters.
WPs:
1. Renderer ADR by benchmark on 50 million points (candidates in 12.4, including the Nomivox GUI), PDAL and COPC evaluation for the tile format.
2. Out-of-core display with level of detail, navigation, picking, measuring, bookmarks.
3. Model display from the scene model, model tree, clip box with presets and slab mode.
4. Tolerance view with live threshold and histogram.
5. Camera markers and camera mode with photo, point cloud and model opacity sliders (12.5).
6. Attribute panel with parameter and property editing through patches, undo and redo (12.6).
Demo: `raumlot view proj` on eingang_buero.e57.
Accepted when: a 50 million point cloud navigates smoothly within the frame budget, the 29 cameras appear at their places, clicking a camera shows the anonymized photo with the cloud and the model blended by the sliders and the model lines match the photo, clicking a wall shows all its attributes, changing its thickness updates the openings and the room area and the exported IFC, the clip box cuts cloud and model without stutter, the model tree selects a storey.

### M9 AI layer
Goal: the review loop with any backend.
WPs:
1. AIProvider interface, FakeAIProvider, cache, cost and call caps, image gate.
2. openrouter backend with model discovery and capability badges.
3. Subscription backends (claude_subscription, gemini_subscription, codex_subscription) after checking each CLI and its terms (8.1), optional direct API backends.
4. Context builder, prompts, tools, schemas, JSON loop mode.
5. Loop per room and building, AI tasks of 8.9.
6. Qualification test, comparison harness, privacy settings, key and login handling.
Demo: `raumlot review proj --ai-backend openrouter --model <id>` and the same with a subscription backend.
Accepted when: at least three models (from at least two backends) pass the qualification test or fail it with a clear report, the loop reduces the number of non-ok elements on the evaluation set compared with the script-only result, or the report states honestly that it did not. The loop is evaluated for indoor and outdoor scope and for each data source, with separate numbers per combination. A test confirms that every backend adapter refuses every image without the intake run id.

### M10 Furniture
Goal: the furnishings of eingang_buero.e57 as editable objects.
WPs:
1. Stage 4 clustering check and suspect cluster rules (report and review queue).
2. Parametric templates (9.1) with fitting.
3. Catalog import from IFC (`raumlot library import`) with previews, and matching (9.2, 9.3).
4. Mesh and box fallbacks, type fusion.
5. Candidate choice in the viewer and catalog promotion.
Demo: `raumlot library import <archicad_export.ifc>`, `raumlot extract proj --stage furniture`, `raumlot view proj`.
Accepted when: the share of auto-accepted instances and the shape accuracy are reported, the user can swap a furniture element for another candidate in the viewer and the IFC follows, structure_only projects skip this stage without error.

### M11 Wizard and run panel
Project wizard (12.1) and run panel (12.2) on top of the service layer. Accepted when: a project for eingang_buero.e57 can be set up and run completely from the desktop app.

### M12 Review editing
Drag handles for wall ends and opening edges, split and merge of instances, reassign class, add and delete elements, review queue navigation (catalog promotion is delivered in M10). Accepted when: a user can fix every flagged element type without leaving the app, and exports update.

### M13 More importers
LAS or LAZ plus COLMAP, Metashape, Pix4D and generic camera files, native SLAM sets with trajectory and time offset, image folder fallback, each with its pose convention tests (3.2, 3.3). Accepted when: a synthetic project in each format reproduces the known projected points, and the real formats of Q6 and Q12 load with cameras at the right place.

### M14 Instance refinement
Second SAM 3.1 pass for suspect clusters and disagreements (stage 4), measured gain on the evaluation set. Accepted when: the share of correctly split clusters improves, otherwise the second pass stays off.

### M15 Hardening
Performance, error handling, Windows installer including the native extension and the CUDA dependencies, user manual.

## 16. Open questions (record answers in docs/DECISIONS.md)

Status per question: open, partly answered or answered. "Ask in" names the milestone where the question is asked at the latest. Where a sensible default exists it is given and applies until the user answers. Questions without a default block only the milestone named in "ask in".

Q1 (partly answered, ask in M0). The default class map is presets/default.json from Nomivox: 36 classes and 268 prompts, ASPRS-like codes outdoors (ground 2, low vegetation 3, tree 5, building 6, water 9, road 11, power line 14, vehicle 91 and others) and codes from 100 indoors (wall 100, ceiling 101, floor 102, door 103, window 104, stairs 105, railing 107, column 108, beam 109, pipe 111, furniture 117, appliances 118 and others), sanitary fixtures 63, reflection 68, unclassified 1. Anonymization is stored as flag bits (anon_flags), not as class ids. Open: are these ids right for Raumlot and the same across projects? Default: use the preset as is.
Q2 (open, ask in M4). The 4 cm ceiling tolerance: measured against the fitted (possibly tilted or sagging) surface, or against the horizontal? Default: fitted surface.
Q3 (partly answered, ask in M2). E57 files carry per-scan membership. For eingang_buero.e57 (one merged SLAM scan) visibility is free_camera. Open: do LAS deliveries carry per-station information (point_source_id, scan position)? Default: free_camera unless membership is found.
Q4 (open, ask in M1). Are LAS and E57 in the same coordinate frame and CRS? Which CRS and height system (LN02 or LHN95), and which origin offset do you use? Default: EPSG:2056 with LN02, offset at the rounded minimum of the cloud.
Q5 (partly answered, ask in M2). eingang_buero.e57 has 29 spherical images of 8192 by 4096 with own poses. Open: which camera types do your TLS E57 files use, how many images per scan, and is the camera offset to the scanner center stored?
Q6 (partly answered, ask in M13). SLAM delivered as E57 with posed spherical images needs no trajectory. Open: native SLAM formats you also use (trajectory file format, timestamp format, calibration file format, camera model, known time offset)?
Q7 (partly answered, ask in M1). The consuming software is ArchiCAD. Open: which ArchiCAD version? Layered walls with real layer build-ups or single layer? Which classification system (eBKP-H, ArchiCAD classification, none)? Ceiling as covering or as slab? Default: IFC4 ADD2 TC1, single layer, no classification, ceiling as covering.
Q8 (answered). This is a personal project. Record the license or terms of use of every third-party asset (SAM weights, catalog objects), because a later sale or company use would change what is allowed. Nomivox and NeuralCensor are the user's own code and need no notices.
Q9 (partly answered, ask in M9). Data sharing with external providers is a concern, so the switches (send_images off, AI off per project) stay and are easy to reach. OpenRouter is the default backend. Open: which models are on the shortlist, the cost cap per room or project, which providers must be excluded, whether regional endpoints matter, which subscriptions are used (Claude, Gemini, Codex), which backend per task, and whether subscription backends may receive images.
Q10 (open, ask in M4). Is there a manually modeled reference IFC (for example from ArchiCAD) of at least one scanned room for evaluation, ideally of eingang_buero?
Q11 (partly answered, ask in M0). The GPU is an NVIDIA RTX 4090 with 24 GB VRAM. Open: RAM, CPU cores, free disk space for the cache and the anonymized images, size of the largest project (165 scan positions mentioned, number of points), acceptable processing times for 50 million points, is a Rust toolchain acceptable in the build and installer?
Q12 (partly answered, ask in M13). Photogrammetry results come as E57 with 360 degree images, processed like SLAM. Open: which software produces them, are LAS plus COLMAP, Metashape or Pix4D exports also needed, which camera and distortion models, are scale and georeference reliable (ground control points, GNSS), and are control points available?
Q13 (open, ask in M7). Outdoor scope: which class ids mean ground, building, roof, vegetation and others (default: the preset)? Which output is wanted (terrain resolution, building level of detail, roof shapes, facade openings)? Which accuracy targets apply?
Q14 (open, ask in M7). indoor_outdoor scope: should interior and exterior share one IfcBuilding (default yes), and which source is authoritative for the outer wall faces when they disagree?
Q15 (open, ask in M2). External check in Cyclone 3DR: which formats must the tool provide (colored LAS or LAZ, and which model format: IFC, OBJ, PLY, E57, other), and which Cyclone 3DR version?
Q16 (answered). Nomivox is adopted as the foundation by copying its modules and tests into Raumlot and improving them there (4.2). NeuralCensor's SAM logic is reimplemented. Ollama and Falcon are not used.
Q16b (open, ask in M0). From which Nomivox commit is the code taken? The working tree has uncommitted changes (among them the geometric mirror detector). Default: the user commits them first, then the port uses that commit.
Q17 (partly answered, ask in M0). Test data: eingang_buero.e57 and pointcloud.e57 are known (14.7). Open: which further datasets exist (TLS stationary indoors, outdoor, photogrammetry), and which images contain people, license plates and computer screens for the anonymization test? Who labels the regions by hand?
Q18 (open, ask in M0). Nomivox pins numpy 1.26.4. May Raumlot move to numpy 2 if all dependencies allow it, or should the intake keep its own environment? Default: one environment with the newest numpy that all pinned packages support.
Q19 (open, ask in M10). Furniture catalog: which ArchiCAD library objects (or manufacturer objects) should be exported first, and in which ArchiCAD version?

## 17. Known risks (keep updated in docs/DECISIONS.md)

- Classification errors become model errors. Add an outlier filter before extraction and show conflicts in the review.
- Tolerance below sensor noise gives meaningless deviation values. The noise estimate and warnings are mandatory. The first real dataset is a SLAM scan, where this is expected.
- Misalignment between photos and points shifts all masks and overlays. The alignment test in stage 1 is a gate.
- Photogrammetry scale and georeference errors make every tolerance meaningless. The check in stage 1 is a gate and unverified scale is flagged everywhere.
- Pose and distortion conventions differ between software. Wrong conversion silently shifts everything. The conversion layer needs tests with known projected points.
- Mirrors and glass produce ghost points and false instances. The intake follows the Nomivox rule: reflection points get class 68 and a mirror state, and structure fits exclude them.
- Hidden parts of furniture and walls seen from one side are assumptions. They are tagged and never counted as measured.
- Curved walls, slopes and niches break the straight segment logic of version 1. They are flagged, not silently approximated.
- Designer furniture can be described by templates that look right and fit badly. The deviation check overrides appearance.
- An IFC that validates can still import badly into ArchiCAD (walls as generic objects, broken joins, missing zones). The ArchiCAD checklist (10.2) is part of every IFC milestone.
- Parametric regeneration can change geometry the user did not touch (for example recut joins). The dependency graph recomputes only derived values, and the re-run policy protects manual and locked elements.
- Models and backends differ strongly in image understanding, tool calling and schema discipline. The capability handling, the context pack and the qualification test reduce the risk. Choose defaults by the evaluation harness, not by price.
- Subscription backends depend on locally installed CLIs whose flags, limits and terms change. Check them at build time, isolate every call in a temporary folder, and never let a limited backend block a run.
- OpenRouter routes to third-party providers with different data policies. A data decision (Q9) is needed before any image is sent.
- The AI runs in every standard project, so cost and data exposure scale with every run. Cache, caps and the send_images setting are mandatory. An unreachable backend must never block a run. Non-ok elements then go to the review queue.
- Anonymization depends on the detection recall of SAM alone. There is no second detector and no verification model. A missed person or screen stays visible. A low confidence threshold, the retry pass, prompt variants and the sample gallery lower the risk and do not remove it. Mosaic and blur do not prove irreversibility. The send_images switch stays separate.
- SAM 3.1 may not improve still image segmentation over SAM 3, and the multiplex checkpoint may not load in the image predictor, because its published changes concern video tracking. Smoke test in M0, decide by benchmark in M3.
- A global voting structure can grow with the project and exhaust memory. The adopted VoteStore is on disk and per unit. Verify with the large synthetic project.
- VRAM is shared between SAM and the desktop viewer. The VRAM planner and the out-of-memory fallback are mandatory.
- The adopted Nomivox code is coupled to a config dict and partly to large modules. The port keeps its tests green first and refactors second.
- numpy and library version conflicts between the Nomivox pins and the IFC and geometry stack. Settled in M0 (Q18), with a separate intake environment as fallback.
- Rust and Python mixed builds add complexity, especially on Windows. Keep the Python reference implementation as fallback and test the build early (M0).
- Viewer performance with very large clouds and camera mode blending is a risk. Decide the renderer by measurement in M8.
- Room assignment for the mandatory IFC attributes can fail for walls between spaces and in open-plan areas. Flag these cases and never guess silently.
- Interior scans and exterior photogrammetry have different accuracy. Merging them in indoor_outdoor scope can produce conflicts at the outer walls. Flag them, do not average them silently.
- Catalog and segmentation model licenses can block commercial use. Record the terms per asset.

