"""The command line for everything that is not the server.

    uv run inferapi data-convert
    uv run inferapi train --max-depth 12 --output out/models/deep.joblib

A CLI instead of an `if __name__ == "__main__"` block at the bottom of train.py:
the entrypoint is then something you can name, document, `--help`, and call from a
bash script without knowing which module happens to hold the code today. Lab 2's
hyperparameter sweep is a loop over this command.

Flags beat every configuration source, including the environment, because whoever
typed the flag is standing right there.

The parser and the flag layering are provided. What is missing is the wiring, and
each piece ships as a stub followed by its solution.
"""

import argparse
import logging
from pathlib import Path
from typing import Any

from inferapi.config import TrainingSettings
from inferapi.data import csv_to_parquet, load_raw
from inferapi.logging_setup import setup_logging
from inferapi.train import training_procedure

logger = logging.getLogger(__name__)

# Flags accepted before the subcommand, and the settings field each one overrides.
# Subcommands declare their own map in set_defaults(config_flags=...) below.
GLOBAL_FLAGS = {"log_level": "logging.level"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inferapi", description=__doc__.splitlines()[0])
    parser.add_argument("--log-level", help="override logging.level for this run")
    commands = parser.add_subparsers(dest="command", required=True)

    convert = commands.add_parser("data-convert", help="convert the downloaded CSV into parquet")
    convert.add_argument("--csv", type=Path, help="override data.csv_path")
    convert.add_argument("--parquet", type=Path, help="override data.parquet_path")
    convert.set_defaults(
        run=run_data_convert,
        config_flags={"csv": "data.csv_path", "parquet": "data.parquet_path"},
    )

    train = commands.add_parser("train", help="train the model and write the artifact")
    # One argument is provided as the example to follow: --output is required, because
    # a training run that does not say where the artifact goes has nothing to say.
    train.add_argument("--output", type=Path, required=True, help="where to write the artifact")
    train.add_argument("--data", type=Path, help="override data.parquet_path")
    train.add_argument("--n-estimators", type=int, help="override training.n_estimators")
    train.add_argument("--max-depth", type=int, help="override training.max_depth")
    train.add_argument("--seed", type=int, help="override training.seed")
    train.add_argument("--decision-threshold", type=float, help="override training.decision_threshold")
    train.add_argument(
        "--overwrite",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="replace the artifact if it already exists (default: refuse)",
    )
    train.set_defaults(
        run=run_train,
        # --output and --overwrite are absent on purpose: they say what this run does
        # with its result, not what the project is configured to be.
        config_flags={
            "data": "data.parquet_path",
            "n_estimators": "training.n_estimators",
            "max_depth": "training.max_depth",
            "seed": "training.seed",
            "decision_threshold": "training.decision_threshold",
        },
    )

    return parser


def settings_from_args(args: argparse.Namespace) -> TrainingSettings:
    """Build the settings, with the flags the user actually typed layered on top.

    An absent flag is `None`, and `None` is not an opinion: it must leave whatever
    the YAML or the environment said alone. Only the flags carrying a value become a
    layer, and that layer is handed to pydantic-settings as init values - its
    highest-priority source, deep-merged over the others. Precedence therefore reads
    flags, environment, .env, YAML, field defaults, and it is stated once, in
    config.py, instead of being re-implemented by every subcommand.

    Two things follow from building the settings here rather than patching them
    later: the values are validated on the way in, and the `cli_invoked` log line
    below describes the run that is about to happen rather than the one the YAML
    would have produced.
    """
    overrides: dict[str, dict[str, Any]] = {}
    for flag, path in (GLOBAL_FLAGS | args.config_flags).items():
        value = getattr(args, flag)
        if value is None:
            continue
        section, field = path.split(".")
        overrides.setdefault(section, {})[field] = value

    return TrainingSettings(**overrides)


def run_data_convert(args: argparse.Namespace, settings: TrainingSettings) -> int:
    csv_to_parquet(settings.data.csv_path, settings.data.parquet_path)
    return 0


def run_train(args: argparse.Namespace, settings: TrainingSettings) -> int:
    training_procedure(
        settings.training,
        dataframe=load_raw(settings.data.parquet_path),
        output_model_path=args.output,
        overwrite_model=args.overwrite,
    )
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    settings = settings_from_args(args)
    # Once, here, at the entrypoint: no imported module ever configures logging.
    setup_logging(settings.logging)

    logger.debug("cli_invoked command=%s settings=%s", args.command, settings.model_dump(mode="json"))
    return args.run(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())
