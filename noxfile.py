from __future__ import annotations

import os
from pathlib import Path

import nox

nox.options.default_venv_backend = "none"


def _run(session: nox.Session, *arguments: str) -> None:
    session.run("uv", "run", *arguments, external=True)


@nox.session
def check(session: nox.Session) -> None:
    _run(session, "ruff", "check")
    _run(session, "ruff", "format", "--check")
    _run(session, "mypy", "src")
    _run(
        session,
        "pytest",
        "-m",
        "not gpu and not realdata and not network and not native and not slow",
        *session.posargs,
    )


@nox.session
def native(session: nox.Session) -> None:
    cargo_bin = Path.home() / ".cargo" / "bin"
    environment = {"PATH": os.pathsep.join((str(cargo_bin), os.environ["PATH"]))}

    session.run(
        "cargo",
        "test",
        "--manifest-path",
        "native/Cargo.toml",
        external=True,
        env=environment,
    )
    session.run(
        "uv",
        "run",
        "maturin",
        "develop",
        "--manifest-path",
        "native/Cargo.toml",
        external=True,
        env=environment,
    )
    session.run("uv", "run", "pytest", "tests/native", external=True, env=environment)


@nox.session
def gpu(session: nox.Session) -> None:
    _run(session, "pytest", "-m", "gpu", *session.posargs)


@nox.session
def realdata(session: nox.Session) -> None:
    _run(session, "pytest", "-m", "realdata", *session.posargs)


@nox.session
def network(session: nox.Session) -> None:
    _run(session, "pytest", "-m", "network", *session.posargs)
