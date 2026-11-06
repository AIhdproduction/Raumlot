"""Runtime settings loaded from the environment and an optional .env file."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict


def default_repo_root() -> Path:
    """Return the repository root for an editable install."""
    return Path(__file__).resolve().parents[2]


def _value(values: Mapping[str, str | None], name: str, default: str) -> str:
    value = values.get(name)
    return value if value else default


class Settings(BaseModel):
    """Paths required by M0 commands."""

    model_config = ConfigDict(frozen=True)

    home: Path
    sam_checkpoint: Path
    sam3_fallback_checkpoint: Path
    testdata: Path

    @classmethod
    def load(cls, environ: Mapping[str, str] | None = None, *, use_dotenv: bool = True) -> Settings:
        """Load settings, giving non-empty environment values precedence over .env."""
        source = os.environ if environ is None else environ
        environment = {name: value for name, value in source.items() if value}
        initial_root = default_repo_root()
        explicit_home = environ is not None and "RAUMLOT_HOME" in environment
        initial_dotenv = (
            dotenv_values(initial_root / ".env") if use_dotenv and not explicit_home else {}
        )
        initial_values: dict[str, str | None] = {**initial_dotenv, **environment}
        home = Path(_value(initial_values, "RAUMLOT_HOME", str(initial_root))).expanduser()

        home_dotenv = dotenv_values(home / ".env") if use_dotenv and home != initial_root else {}
        values: dict[str, str | None] = {**initial_dotenv, **home_dotenv, **environment}
        return cls(
            home=home,
            sam_checkpoint=Path(
                _value(
                    values, "RAUMLOT_SAM_CHECKPOINT", str(home / "models" / "sam3.1_multiplex.pt")
                )
            ).expanduser(),
            sam3_fallback_checkpoint=Path(
                _value(values, "RAUMLOT_SAM3_FALLBACK_CHECKPOINT", r"D:\Nomivox\models\sam3.pt")
            ).expanduser(),
            testdata=Path(_value(values, "RAUMLOT_TESTDATA", str(home / "test_PW"))).expanduser(),
        )
