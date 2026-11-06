from __future__ import annotations

import importlib

from raumlot import doctor
from raumlot.settings import Settings


def test_missing_required_package_fails(monkeypatch) -> None:
    original_import = importlib.import_module

    def missing_numpy(name: str, package: str | None = None):
        if name == "numpy":
            raise ImportError("simulated missing package")
        return original_import(name, package)

    monkeypatch.setattr(doctor.importlib, "import_module", missing_numpy)
    report = doctor.run_doctor(Settings.load(environ={}))

    numpy_status = next(item for item in report.packages if item.name == "numpy")
    assert report.ok is False
    assert "simulated missing package" in (numpy_status.error or "")


def test_missing_optional_package_warns_without_failure(monkeypatch) -> None:
    original_import = importlib.import_module

    def missing_open3d(name: str, package: str | None = None):
        if name == "open3d":
            raise ImportError("simulated optional package absence")
        return original_import(name, package)

    monkeypatch.setattr(doctor.importlib, "import_module", missing_open3d)
    report = doctor.run_doctor(Settings.load(environ={}))

    open3d_status = next(item for item in report.packages if item.name == "open3d")
    assert report.ok is True
    assert "simulated optional package absence" in (open3d_status.error or "")
