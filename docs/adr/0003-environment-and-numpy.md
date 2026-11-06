# ADR 0003: Environment and NumPy

Status: accepted

## Context

Nomivox pins NumPy 1.26.4. Raumlot needs one environment that can also support IFC, geometry, UI, E57, and CUDA intake dependencies. The preferred approach is the newest NumPy version supported by every resolved package; the fallback is a separate intake environment.

## Decision

Raumlot uses one environment with NumPy 1.26.4. sam3 requires `numpy>=1.26,<2`, so there is no separate intake environment.

## Consequences

New dependencies must support NumPy 1.26. Revisit this decision when sam3 supports NumPy 2.

## Result of the M0 environment check

`uv lock` resolved all packages with NumPy 1.26.4. A trial resolve with the constraint `numpy>=2` failed because sam3 0.1.0 (pinned commit 0570b3a5) requires `numpy>=1.26,<2`. Everything else (torch 2.11.0+cu128, open3d 0.20.0, ifcopenshell 0.9.0.post1, ifctester 0.9.0, pye57 0.4.19, laspy 2.7.0, PySide6 6.12.0, shapely 2.2.0, opencv-python 4.11.0.86) imports and works with NumPy 1.26.4 in one environment (`raumlot doctor`, 2026-11-06).

Decision: one environment, with NumPy pinned by sam3 to `<2`; revisit when sam3 supports NumPy 2. No separate intake environment is needed.

Consequence: new dependencies must support NumPy 1.26.
