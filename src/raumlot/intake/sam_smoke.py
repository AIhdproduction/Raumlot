"""GPU smoke test for loading SAM from an E57 panorama."""

from __future__ import annotations

import gc
import io
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from raumlot.settings import Settings

PROMPTS: tuple[str, ...] = ("wall", "floor", "ceiling", "door", "window", "person")
E57_REPRESENTATIONS: tuple[str, ...] = (
    "sphericalRepresentation",
    "pinholeRepresentation",
    "cylindricalRepresentation",
)


@dataclass(frozen=True)
class PromptResult:
    prompt: str
    masks_at_threshold: int


@dataclass(frozen=True)
class CheckpointAttempt:
    checkpoint: str
    worked: bool
    load_seconds: float | None
    inference_seconds: float | None
    peak_vram_bytes: int | None
    prompts: list[PromptResult]
    error: str | None


@dataclass(frozen=True)
class SamSmokeResult:
    worked: bool
    attempts: list[CheckpointAttempt]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _image_blob(path: Path) -> bytes:
    """Read the first E57 Image2D image blob directly into memory."""
    import numpy as np
    from pye57 import libe57 as lib

    image_file = lib.ImageFile(str(path), "r")
    try:
        root = image_file.root()
        images = root["images2D"]
        if images.childCount() < 1:
            raise ValueError(f"No Image2D records found in {path}")
        image = images[0]
        for representation_name in E57_REPRESENTATIONS:
            if not image.isDefined(representation_name):
                continue
            representation = image[representation_name]
            for blob_name in ("jpegImage", "pngImage"):
                if not representation.isDefined(blob_name):
                    continue
                blob = representation[blob_name]
                data = np.empty(blob.byteCount(), dtype=np.uint8)
                blob.read(data, 0, blob.byteCount())
                return data.tobytes()
        raise ValueError("The first Image2D record has no JPEG or PNG image blob")
    finally:
        image_file.close()


def load_test_image(testdata: Path) -> Image.Image:
    """Decode, resize, and centrally crop the smoke-test panorama in memory."""
    source = testdata / "eingang_buero.e57"
    if not source.is_file():
        raise FileNotFoundError(f"Smoke-test E57 file missing: {source}")
    with Image.open(io.BytesIO(_image_blob(source))) as image:
        resized = image.convert("RGB").resize((2048, 1024), Image.Resampling.LANCZOS)
    return resized.crop((512, 0, 1536, 1024))


def _run_checkpoint(checkpoint: Path, image: Any) -> CheckpointAttempt:
    """Load one checkpoint and count high-confidence masks for the configured prompts."""
    import torch
    from sam3.model.data_misc import FindStage
    from sam3.model.sam3_image_processor import Sam3Processor
    from sam3.model_builder import build_sam3_image_model

    if not checkpoint.is_file():
        raise FileNotFoundError(f"SAM checkpoint missing: {checkpoint}")
    if not torch.cuda.is_available():
        raise RuntimeError("SAM smoke test requires a CUDA GPU")

    device = torch.device("cuda:0")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(device)
    load_started = time.perf_counter()
    model = (
        build_sam3_image_model(
            checkpoint_path=str(checkpoint),
            device="cpu",
            load_from_HF=False,
            enable_segmentation=True,
            enable_inst_interactivity=False,
            compile=False,
        )
        .to(device)
        .eval()
    )
    processor = Sam3Processor(model, resolution=1008, device=str(device))
    load_seconds = time.perf_counter() - load_started

    results: list[PromptResult] = []
    inference_started = time.perf_counter()
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    with torch.inference_mode(), torch.autocast(device_type="cuda", dtype=dtype):
        state = processor.set_image(image)
        for prompt in PROMPTS:
            text_features = model.backbone.forward_text([prompt], device=str(device))
            state["backbone_out"].update(text_features)
            find = FindStage(
                img_ids=torch.zeros(1, dtype=torch.long, device=device),
                text_ids=torch.zeros(1, dtype=torch.long, device=device),
                input_boxes=None,
                input_boxes_mask=None,
                input_boxes_label=None,
                input_points=None,
                input_points_mask=None,
            )
            output = model.forward_grounding(
                backbone_out=state["backbone_out"],
                find_input=find,
                geometric_prompt=model._get_dummy_prompt(num_prompts=1),
                find_target=None,
            )
            scores = output["pred_logits"][0, :, 0].sigmoid()
            results.append(PromptResult(prompt, int((scores >= 0.15).sum().item())))
    torch.cuda.synchronize(device)
    inference_seconds = time.perf_counter() - inference_started
    peak_vram_bytes = int(torch.cuda.max_memory_allocated(device))

    del processor, model
    gc.collect()
    torch.cuda.empty_cache()
    return CheckpointAttempt(
        checkpoint=str(checkpoint),
        worked=True,
        load_seconds=load_seconds,
        inference_seconds=inference_seconds,
        peak_vram_bytes=peak_vram_bytes,
        prompts=results,
        error=None,
    )


def run_sam_smoke(settings: Settings) -> SamSmokeResult:
    """Try the SAM 3.1 checkpoint, then the configured SAM 3 fallback checkpoint."""
    attempts: list[CheckpointAttempt] = []
    try:
        image = load_test_image(settings.testdata)
    except Exception as error:
        return SamSmokeResult(
            worked=False,
            attempts=[
                CheckpointAttempt(
                    checkpoint=str(settings.testdata / "eingang_buero.e57"),
                    worked=False,
                    load_seconds=None,
                    inference_seconds=None,
                    peak_vram_bytes=None,
                    prompts=[],
                    error=f"{type(error).__name__}: {error}",
                )
            ],
        )

    for checkpoint in (settings.sam_checkpoint, settings.sam3_fallback_checkpoint):
        try:
            attempt = _run_checkpoint(checkpoint, image)
        except Exception as error:
            attempt = CheckpointAttempt(
                checkpoint=str(checkpoint),
                worked=False,
                load_seconds=None,
                inference_seconds=None,
                peak_vram_bytes=None,
                prompts=[],
                error=f"{type(error).__name__}: {error}",
            )
        attempts.append(attempt)
        if attempt.worked:
            return SamSmokeResult(worked=True, attempts=attempts)
    return SamSmokeResult(worked=False, attempts=attempts)
