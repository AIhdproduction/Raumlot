from __future__ import annotations

import pytest

from raumlot.intake.sam_smoke import run_sam_smoke
from raumlot.settings import Settings


@pytest.mark.gpu
@pytest.mark.realdata
def test_sam_smoke_loads_checkpoint_and_returns_wall_mask() -> None:
    result = run_sam_smoke(Settings.load())

    assert result.worked
    successful_attempt = next(attempt for attempt in result.attempts if attempt.worked)
    wall = next(prompt for prompt in successful_attempt.prompts if prompt.prompt == "wall")
    assert wall.masks_at_threshold >= 1
