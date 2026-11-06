from __future__ import annotations

from pathlib import Path

import pytest

import raumlot.settings as settings_module
from raumlot.settings import Settings, default_repo_root


def test_defaults_use_repository_paths() -> None:
    settings = Settings.load(environ={}, use_dotenv=False)

    assert settings.home == default_repo_root()
    assert settings.sam_checkpoint == default_repo_root() / "models" / "sam3.1_multiplex.pt"
    assert settings.testdata == default_repo_root() / "test_PW"


def test_environment_overrides_paths(tmp_path: Path) -> None:
    settings = Settings.load(
        environ={
            "RAUMLOT_HOME": str(tmp_path),
            "RAUMLOT_TESTDATA": str(tmp_path / "data"),
            "RAUMLOT_SAM_CHECKPOINT": str(tmp_path / "sam.pt"),
            "RAUMLOT_SAM3_FALLBACK_CHECKPOINT": str(tmp_path / "fallback.pt"),
        },
        use_dotenv=False,
    )

    assert settings.home == tmp_path
    assert settings.testdata == tmp_path / "data"
    assert settings.sam_checkpoint == tmp_path / "sam.pt"
    assert settings.sam3_fallback_checkpoint == tmp_path / "fallback.pt"


def test_dotenv_is_loaded_from_overridden_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("RAUMLOT_TESTDATA=fixture_data\n", encoding="utf-8")
    original_dotenv_values = settings_module.dotenv_values

    def dotenv_values_from_home(path: Path) -> dict[str, str | None]:
        if path == default_repo_root() / ".env":
            raise AssertionError("The repository .env must not be read.")
        return original_dotenv_values(path)

    monkeypatch.setattr(settings_module, "dotenv_values", dotenv_values_from_home)

    settings = Settings.load(environ={"RAUMLOT_HOME": str(tmp_path)})

    assert settings.testdata == Path("fixture_data")


def test_empty_environment_values_do_not_override_dotenv(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("RAUMLOT_TESTDATA=fixture_data\n", encoding="utf-8")

    settings = Settings.load(environ={"RAUMLOT_HOME": str(tmp_path), "RAUMLOT_TESTDATA": ""})

    assert settings.testdata == Path("fixture_data")
