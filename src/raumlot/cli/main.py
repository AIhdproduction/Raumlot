"""Argument parser and command registration for Raumlot."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from raumlot import __version__
from raumlot.doctor import render_text, run_doctor
from raumlot.settings import Settings

Command = Callable[[argparse.Namespace], int]


def doctor_command(arguments: argparse.Namespace) -> int:
    """Run environment diagnostics."""
    report = run_doctor(Settings.load(), include_sam=arguments.sam)
    if arguments.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report.ok else 1


COMMANDS: dict[str, Command] = {"doctor": doctor_command}


def build_parser() -> argparse.ArgumentParser:
    """Build the extensible Raumlot command-line parser."""
    parser = argparse.ArgumentParser(prog="raumlot", description="Raumlot command-line tools")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subcommands.add_parser("doctor", help="report the local environment")
    doctor_parser.add_argument("--sam", action="store_true", help="run the GPU SAM smoke test")
    doctor_parser.add_argument("--json", action="store_true", help="write the report as JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the requested command and return a process exit code."""
    arguments = build_parser().parse_args(argv)
    return COMMANDS[arguments.command](arguments)
