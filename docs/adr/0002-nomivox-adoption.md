# ADR 0002: Nomivox adoption

Status: accepted, source commit pending

Source commit: pending (to be filled in M2)

## Context

Nomivox contains the E57, camera, visibility, segmentation, voting, mirror, preset, and LAS foundations needed by Raumlot. Its working tree had open changes on 2026-11-06.

## Decision

The user first commits the open Nomivox changes. M2 then ports the needed modules and tests from that fixed commit into Raumlot, where they are maintained as Raumlot code. NeuralCensor is not copied; only its SAM logic and parameters are reimplemented where required.

## Consequences

The M2 port has a reproducible source point and an adopted regression suite. No change is made in the Nomivox repository, and new Raumlot work is independent after the port.
