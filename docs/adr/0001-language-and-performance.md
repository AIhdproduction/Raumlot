# ADR 0001: Language and performance

## Context

Raumlot needs an IFC-capable pipeline, GPU segmentation, and high-throughput point-cloud processing on Windows.

## Decision

Python implements the orchestration, pipeline, IFC layer, AI layer, and UI. Heavy math uses vectorized NumPy or SciPy, and Torch when the GPU is already active. Rust with PyO3 and maturin is introduced only for benchmark-proven hot paths; the M0 maturin build is deliberately minimal. Candidate alternatives are C++ with pybind11, Numba, and Cython.

## Consequences

The existing Python ecosystem and Nomivox code can be used directly, while optimized kernels retain a Python reference implementation and require measured benefit before adoption. A full Rust or C++ rewrite is rejected because it would lose the IFC ecosystem without a demonstrated gain.

## M0 result

The minimal extension builds with maturin and imports on Windows.

Build verified: 2026-11-06 on Windows 11 (rustc 1.99.1, PyO3 0.30.1, maturin 1.16.0, abi3-py312). `nox -s native` runs cargo test, `maturin develop` and 4 Python smoke tests, all green.
