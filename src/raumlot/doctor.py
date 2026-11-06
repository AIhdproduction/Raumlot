"""Environment diagnostics for Raumlot."""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psutil

from raumlot.settings import Settings

REQUIRED_PACKAGES: tuple[tuple[str, str, str], ...] = (
    ("numpy", "numpy", "numpy"),
    ("scipy", "scipy", "scipy"),
    ("pydantic", "pydantic", "pydantic"),
    ("PyYAML", "yaml", "PyYAML"),
    ("xxhash", "xxhash", "xxhash"),
    ("psutil", "psutil", "psutil"),
    ("Pillow", "PIL", "Pillow"),
    ("laspy", "laspy", "laspy"),
    ("lazrs", "lazrs", "lazrs"),
    ("pye57", "pye57", "pye57"),
    ("shapely", "shapely", "shapely"),
    ("ifcopenshell", "ifcopenshell", "ifcopenshell"),
    ("ifctester", "ifctester", "ifctester"),
    ("ezdxf", "ezdxf", "ezdxf"),
    ("httpx", "httpx", "httpx"),
    ("python-dotenv", "dotenv", "python-dotenv"),
    ("keyring", "keyring", "keyring"),
    ("opencv-python", "cv2", "opencv-python"),
)

OPTIONAL_PACKAGES: tuple[tuple[str, str, str], ...] = (
    ("torch", "torch", "intake"),
    ("torchvision", "torchvision", "intake"),
    ("triton-windows", "triton", "intake"),
    ("sam3", "sam3", "intake"),
    ("einops", "einops", "intake"),
    ("pycocotools", "pycocotools", "intake"),
    ("timm", "timm", "intake"),
    ("iopath", "iopath", "intake"),
    ("ftfy", "ftfy", "intake"),
    ("regex", "regex", "intake"),
    ("huggingface_hub", "huggingface_hub", "intake"),
    ("decord", "decord", "intake"),
    ("safetensors", "safetensors", "intake"),
    ("tqdm", "tqdm", "intake"),
    ("open3d", "open3d", "geometry"),
    ("PySide6", "PySide6", "ui"),
)


@dataclass(frozen=True)
class PackageStatus:
    name: str
    module: str
    required: bool
    group: str
    version: str | None
    error: str | None


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    system: dict[str, Any]
    packages: list[PackageStatus]
    torch: dict[str, Any]
    numpy: dict[str, Any]
    checkpoints: dict[str, dict[str, Any]]
    test_data: dict[str, Any]
    sam_smoke: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _package_status(name: str, module: str, required: bool, group: str) -> PackageStatus:
    try:
        importlib.import_module(module)
        try:
            package_version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            package_version = None
        return PackageStatus(name, module, required, group, package_version, None)
    except Exception as error:
        return PackageStatus(
            name, module, required, group, None, f"{type(error).__name__}: {error}"
        )


def _disk_usage(path: Path) -> dict[str, Any]:
    anchor = path.drive + "\\" if path.drive else path.anchor
    try:
        usage = shutil.disk_usage(anchor)
        return {"drive": anchor, "total_bytes": usage.total, "free_bytes": usage.free}
    except OSError as error:
        return {"drive": anchor, "error": f"{type(error).__name__}: {error}"}


def _checkpoint(path: Path) -> dict[str, Any]:
    exists = path.is_file()
    return {
        "path": str(path),
        "exists": exists,
        "size_gb": round(path.stat().st_size / 1_000_000_000, 3) if exists else None,
    }


def _test_data(path: Path) -> dict[str, Any]:
    files = []
    if path.is_dir():
        files = [
            {"path": str(item), "size_gb": round(item.stat().st_size / 1_000_000_000, 3)}
            for item in sorted(path.glob("*.e57"))
        ]
    return {
        "path": str(path),
        "exists": path.is_dir(),
        "disk": _disk_usage(path),
        "e57_files": files,
    }


def _torch_report() -> dict[str, Any]:
    try:
        torch = importlib.import_module("torch")
    except Exception as error:
        return {"available": False, "error": f"{type(error).__name__}: {error}"}

    cuda_available = bool(torch.cuda.is_available())
    result: dict[str, Any] = {
        "available": True,
        "version": getattr(torch, "__version__", None),
        "cuda_available": cuda_available,
        "cuda_version": getattr(torch.version, "cuda", None),
        "gpu_name": None,
        "total_vram_bytes": None,
        "free_vram_bytes": None,
    }
    if cuda_available:
        try:
            device = torch.device("cuda:0")
            free_vram_bytes, total_vram_bytes = torch.cuda.mem_get_info()
            result.update(
                gpu_name=torch.cuda.get_device_name(device),
                total_vram_bytes=total_vram_bytes,
                free_vram_bytes=free_vram_bytes,
            )
        except Exception as error:
            result["gpu_error"] = f"{type(error).__name__}: {error}"
    return result


def _system_report(settings: Settings) -> dict[str, Any]:
    virtual_memory = psutil.virtual_memory()
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_name": platform.processor() or platform.machine(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "total_ram_bytes": virtual_memory.total,
        "repo_disk": _disk_usage(settings.home),
    }


def run_doctor(settings: Settings, include_sam: bool = False) -> DoctorReport:
    """Collect a complete environment report without changing local data."""
    packages = [
        _package_status(name, module, True, group) for name, module, group in REQUIRED_PACKAGES
    ]
    packages.extend(
        _package_status(name, module, False, group) for name, module, group in OPTIONAL_PACKAGES
    )
    required_ok = all(status.error is None for status in packages if status.required)

    sam_smoke: dict[str, Any] | None = None
    if include_sam:
        from raumlot.intake.sam_smoke import run_sam_smoke

        sam_smoke = run_sam_smoke(settings).to_dict()

    package_versions = {
        status.name: status.version for status in packages if status.version is not None
    }
    return DoctorReport(
        ok=required_ok,
        system=_system_report(settings),
        packages=packages,
        torch=_torch_report(),
        numpy={
            "version": package_versions.get("numpy"),
            "reported_package_versions": package_versions,
            "note": (
                "Package versions are reported only; binary build compatibility is not inferred."
            ),
        },
        checkpoints={
            "sam": _checkpoint(settings.sam_checkpoint),
            "sam3_fallback": _checkpoint(settings.sam3_fallback_checkpoint),
        },
        test_data=_test_data(settings.testdata),
        sam_smoke=sam_smoke,
    )


def render_text(report: DoctorReport) -> str:
    """Render a human-readable version of a doctor report."""
    lines = [
        "Raumlot environment report",
        f"Status: {'ok' if report.ok else 'failed'}",
        "",
        "System",
    ]
    lines.extend(f"  {key}: {value}" for key, value in report.system.items())
    lines.extend(["", "Packages"])
    for package in report.packages:
        state = "ok" if package.error is None else ("failed" if package.required else "warning")
        detail = package.version if package.error is None else package.error
        lines.append(f"  {package.name} ({package.group}, {state}): {detail}")
    lines.extend(["", "Torch"])
    lines.extend(f"  {key}: {value}" for key, value in report.torch.items())
    lines.extend(["", "Checkpoints"])
    for name, checkpoint in report.checkpoints.items():
        lines.append(f"  {name}: {checkpoint}")
    lines.extend(
        [
            "",
            "Test data",
            f"  path: {report.test_data['path']}",
            f"  disk: {report.test_data['disk']}",
        ]
    )
    for item in report.test_data["e57_files"]:
        lines.append(f"  E57: {item['path']} ({item['size_gb']} GB)")
    if report.sam_smoke is not None:
        lines.extend(["", "SAM smoke test", f"  {json.dumps(report.sam_smoke, sort_keys=True)}"])
    return "\n".join(lines)
