from __future__ import annotations

import json

import pytest

import raumlot.cli.main as cli_main
from raumlot.cli.main import main
from raumlot.doctor import DoctorReport


def test_version_outputs_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as result:
        main(["--version"])

    assert result.value.code == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_doctor_json_has_report_sections(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_main, "run_doctor", lambda settings, include_sam: _report(ok=True))

    assert main(["doctor", "--json"]) == 0

    report = json.loads(capsys.readouterr().out)
    assert {
        "system",
        "packages",
        "torch",
        "numpy",
        "checkpoints",
        "test_data",
        "ok",
    } <= report.keys()


def test_doctor_returns_zero_for_healthy_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_main, "run_doctor", lambda settings, include_sam: _report(ok=True))

    assert main(["doctor"]) == 0


def test_doctor_returns_one_for_unhealthy_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_main, "run_doctor", lambda settings, include_sam: _report(ok=False))

    assert main(["doctor"]) == 1


def _report(*, ok: bool) -> DoctorReport:
    return DoctorReport(
        ok=ok,
        system={},
        packages=[],
        torch={},
        numpy={},
        checkpoints={},
        test_data={"path": "", "disk": {}, "e57_files": []},
        sam_smoke=None,
    )
