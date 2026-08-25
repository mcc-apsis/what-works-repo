from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from deet.ui.terminal.wizards import UI, run_model_wizard
from pydantic import Field, create_model

from what_works_repo.batch import Batch
from what_works_repo.configurations import DeetAnnotationConfig
from what_works_repo.constants import DEET_RUN_SKIP


def get_available_deet_runs(deet_dir: Path) -> type:

    runs = {}
    runs["NO_RUN"] = DEET_RUN_SKIP
    for exp_dir in deet_dir.iterdir():
        runs[exp_dir.name] = exp_dir.name

    return Enum("DeetRun", runs)


def create_deet_annotation_config(deet_dir: Path) -> type[DeetAnnotationConfig]:
    DeetRunEnum = get_available_deet_runs(deet_dir)
    return create_model(
        "DeetAnnotationConfigWizard",
        deet_run=(
            Annotated[
                DeetRunEnum,  # ty: ignore[invalid-type-form]
                UI(
                    help=(
                        "Choose a deet experiment, or select skip to proceed"
                        " without deet annotations"
                    )
                ),
            ],
            Field(..., description="deet run"),
        ),
        __base__=DeetAnnotationConfig,
    )


def main(batch_n: int):
    batch = Batch(batch_n)
    config_class = create_deet_annotation_config(
        batch.deet_dir / "data-extraction-experiments"
    )
    config = run_model_wizard(config_class)
    batch.deet_annotation_config.write_text(config.model_dump_json(indent=2))


if __name__ == "__main__":
    typer.run(main)
