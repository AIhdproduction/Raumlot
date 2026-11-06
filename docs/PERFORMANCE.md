# Performance

Hardware measured 2026-11-06: Intel Core i9-13900K (24 cores, 32 threads), 127.7 GB RAM, NVIDIA RTX 4090 with 24 GB VRAM, and free disk space of 183 GB on C:, 562 GB on D:, and 2621 GB on E:.

The following budgets are initial, to be measured:

- Ingest plus index of 50 million points: at most 5 minutes and 8 GB peak RAM.
- Intake per 8192×4096 spherical image view: at most 60 seconds on the RTX 4090 and 20 GB peak VRAM.
- Intake measured on RTX 4090: 1.1 s per 1024x1024 tile, 4.1 GB peak VRAM, single prompt batch of 6 prompts.
- Z-buffer visibility per image: at most 5 seconds.
- Interior structure extraction per room: at most 60 seconds.
- Viewer interaction with 50 million points: at least 30 fps.
- Intake peak RAM: flat across 165 scan positions.

M2 and M3 replace these initial budgets with measured numbers.
